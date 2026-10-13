"""Run integration checks and surface bounded failure details in CI annotations."""
import subprocess,sys,tempfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryFile(mode='w+') as log:
    result=subprocess.run([sys.executable,str(root/'scripts/check_integration.py'),'--viewer','--fea'],cwd=root,stdout=log,stderr=subprocess.STDOUT)
    log.seek(0);output=log.read();print(output,end='')
    if result.returncode:
        lines=output.splitlines()
        markers=[i for i,line in enumerate(lines) if any(token in line for token in ('ERROR:','FAIL:','failed to solve','dependency failed','Error response','CalledProcessError','AssertionError'))]
        diagnostic='\n'.join(lines[max(0,markers[0]-3):markers[0]+55]) if markers else '\n'.join(lines[-80:])
        diagnostic=diagnostic[-10000:].replace('%','%25').replace('\r','%0D').replace('\n','%0A')
        print('::error title=Integration failure details::'+diagnostic)
    raise SystemExit(result.returncode)
