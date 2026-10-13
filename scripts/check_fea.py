from pathlib import Path
from kcee.fea import benchmark
result,archive=benchmark('/tmp/kcee-fea-check')
print(__import__('json').dumps(result,indent=2))
Path('/tmp/kcee-fea-check.zip').write_bytes(archive)
