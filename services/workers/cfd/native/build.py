"""Build the narrow OpenFOAM 1912 postprocessing hash-stream overlay."""
import hashlib,json,os,subprocess,tarfile
from pathlib import Path
from urllib.request import urlopen
URL='https://deb.debian.org/debian/pool/main/o/openfoam/openfoam_1912.200626.orig.tar.bz2'
DIGEST='c75ca0f04cc4f49708296c1926cbde9d0138b3fef298fed54270dfe29e2df404'
root=Path('/build');archive=root/'source.tar.bz2'
with urlopen(URL,timeout=120) as r:archive.write_bytes(r.read())
if hashlib.sha256(archive.read_bytes()).hexdigest()!=DIGEST:raise ValueError('OpenFOAM source checksum mismatch')
with tarfile.open(archive) as tar:
    members=tar.getmembers()
    if any(m.name.startswith('/') or '..' in m.name.split('/') for m in members):raise ValueError('Unsafe upstream source paths')
    tar.extractall(root/'source')
source=next((root/'source').iterdir());header=source/'src/OpenFOAM/db/IOstreams/hashes/OSHA1stream.H';text=header.read_text()
needle='''            sha1_.append(s, n);
            return n;
        }'''
if text.count(needle)!=1:raise ValueError('Unexpected pinned hash-stream implementation')
text=text.replace(needle,needle+'''

        // C++11 stream character writes must participate in the same SHA1.
        virtual int_type overflow(int_type c = traits_type::eof()) override
        {
            if (traits_type::eq_int_type(c, traits_type::eof()))
                return traits_type::not_eof(c);
            const char value = traits_type::to_char_type(c);
            sha1_.append(&value, 1);
            return c;
        }
''');header.write_text(text)
includes=[]
for component in ('OpenFOAM','OSspecific/POSIX'):
    tree=source/'src'/component;links=tree/'lnInclude';links.mkdir(exist_ok=True)
    for p in tree.rglob('*'):
        if p.is_file() and p.suffix in ('.H','.C') and 'lnInclude' not in p.parts:
            link=links/p.name
            if not link.exists():link.symlink_to(p)
    includes+=['-I'+str(links)]
flags=['g++','-std=c++11','-DWM_DP','-DWM_LABEL_SIZE=32','-DNoRepository','-fPIC','-O2',*includes]
out=Path('/opt/kcee/native');out.mkdir(parents=True,exist_ok=True)
subprocess.run([*flags,'-shared',str(root/'digest.cpp'),'-o',str(out/'libkceeDigest.so'),'-lOpenFOAM','-Wl,--version-script='+str(root/'exports.map')],check=True)
exported=subprocess.check_output(['nm','-D','--defined-only',str(out/'libkceeDigest.so')],text=True).splitlines()
if [line.split()[-1] for line in exported]!=['_ZNK4Foam10dictionary6digestEv']:raise ValueError('Unexpected compatibility exports')
subprocess.run([*flags,str(root/'hash_test.cpp'),'-o',str(out/'hash-self-test'),'-lOpenFOAM'],check=True)
subprocess.run([str(out/'hash-self-test')],env={**os.environ,'FOAM_ETC':'/usr/share/openfoam/etc','WM_PROJECT_DIR':'/usr/share/openfoam','LD_PRELOAD':str(out/'libkceeDigest.so')},check=True)
record={'schema':'kcee.openfoam-hash-overlay.v1','source_url':URL,'source_sha256':DIGEST,'upstream_fix':'https://github.com/OpenFOAM/OpenFOAM-9/commit/b0c15bebd37142f3902901ed5e9a60e33ed456eb','scope':'dictionary::digest only; LD_PRELOAD only for native postprocessing','patched_header_sha256':hashlib.sha256(header.read_bytes()).hexdigest(),'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],'package':subprocess.check_output(['dpkg-query','-W','-f=${Version}','libopenfoam'],text=True),'implementation_sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ('build.py','digest.cpp','hash_test.cpp','exports.map')},'binaries_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}}
(out/'build.json').write_text(json.dumps(record,indent=2))
