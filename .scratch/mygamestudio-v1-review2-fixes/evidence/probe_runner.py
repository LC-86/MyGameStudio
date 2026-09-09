import sys, json, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
root=Path(__file__).parent/'copy'
sys.path.insert(0,str(root/'tests'))
import test_github_backend as gh
import test_runtime_gate as rt
name=sys.argv[1]
module=rt if name.endswith('_section') else gh
try:
 if name.endswith('_section'):
  with tempfile.TemporaryDirectory(dir='/tmp') as temp:
   getattr(module,name)(Path(temp))
 else: getattr(module,name)()
except BaseException as exc:
 module.FAILURES.append(type(exc).__name__+': '+str(exc))
print(json.dumps({'name':name,'failures':module.FAILURES},ensure_ascii=False,indent=2))
sys.exit(bool(module.FAILURES))
