"""Provision the pinned official ARM64 SDK and PicoGK; no system install."""
import hashlib,json,os,platform,shutil,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VERSION='9.0.318'
SDK_URL=f'https://builds.dotnet.microsoft.com/dotnet/Sdk/{VERSION}/dotnet-sdk-{VERSION}-osx-arm64.tar.gz'
SDK_SHA512='4305c929005f47a933f33c253b6f47f8b21fd6096c7e359e78495e0de7c8ed1c6700aec2785a983d76ac7c99a66b1422abedb4056259b00e748ffbe36f243532'
def provision():
    if platform.system()!='Darwin' or platform.machine()!='arm64':raise SystemExit('Native PicoGK setup requires Apple Silicon macOS')
    local=ROOT/'.local';local.mkdir(exist_ok=True)
    archive=local/'dotnet-sdk.tar.gz'
    if not archive.exists() or hashlib.sha512(archive.read_bytes()).hexdigest()!=SDK_SHA512:
        archive.unlink(missing_ok=True)
        subprocess.run(['curl','--fail','--location','--retry','3','--retry-all-errors','--output',str(archive),SDK_URL],check=True)
    if hashlib.sha512(archive.read_bytes()).hexdigest()!=SDK_SHA512:raise SystemExit('Official SDK checksum mismatch')
    sdk=local/'dotnet';sdk.mkdir(exist_ok=True)
    if not (sdk/'dotnet').is_file():
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if not (sdk/member.name).resolve().is_relative_to(sdk.resolve()):raise SystemExit('Unsafe archive entry')
            tar.extractall(sdk)
    environment={**os.environ,'DOTNET_ROOT':str(sdk),'DOTNET_CLI_HOME':str(local/'dotnet-home'),'DOTNET_CLI_TELEMETRY_OPTOUT':'1','DOTNET_SKIP_FIRST_TIME_EXPERIENCE':'1','DOTNET_GENERATE_ASPNET_CERTIFICATE':'false','NUGET_PACKAGES':str(local/'nuget')}
    actual=subprocess.check_output([str(sdk/'dotnet'),'--version'],env=environment,text=True).strip()
    if actual!=VERSION:raise SystemExit('Installed SDK version differs from pinned '+VERSION)
    project=ROOT/'host/macos/picogk/Kcee.Geometry.csproj'
    subprocess.run([str(sdk/'dotnet'),'restore',str(project),'-r','osx-arm64','--locked-mode'],env=environment,check=True)
    subprocess.run([str(sdk/'dotnet'),'publish',str(project),'-c','Release','-r','osx-arm64','--self-contained','false','--no-restore','-o',str(local/'picogk')],env=environment,check=True)
    data={'schema_version':1,'architecture':'arm64','dotnet_sdk':{'version':VERSION,'url':SDK_URL,'archive_sha512':SDK_SHA512},'PicoGK':{'package_version':'2.3.0','lock_sha256':hashlib.sha256((project.parent/'packages.lock.json').read_bytes()).hexdigest(),'status':'provisioned'}}
    (local/'runtime-manifest.json').write_text(json.dumps(data,indent=2)+'\n')
    print('PicoGK provisioned under',local)
if __name__=='__main__':provision()
