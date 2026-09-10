from pathlib import Path
import subprocess,shutil,os,json,re,hashlib
W=Path('/tmp/mgs-review7-ADyk4of1'); R=W/'mutation'
shutil.copytree(W/'repro',R,ignore=shutil.ignore_patterns('.git','__pycache__'))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'))
GH=Path('plugin/records/mgs_github.py'); RUN=Path('acceptance/18-complete-package-acceptance/run.sh')
original={p:(R/p).read_bytes() for p in [GH,RUN]}
oldgh=subprocess.check_output(['git','show',f'a3c43ce:{GH}'],cwd=W/'repro').decode()
results=[]
def run(label,kind):
 cmd=['python3','-B','tests/test_github_backend.py'] if kind=='github' else ['python3','-B','-c',"import sys;sys.path.insert(0,'tests');import test_plugin_package as t;t.test_accept18_probe_checks_anchored_to_events();print('FAILURES:',len(t.FAILURES));print('\\n'.join(t.FAILURES));sys.exit(bool(t.FAILURES))"]
 p=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True)
 log=W/'logs'/f'mutation-{label}.log';log.write_text(p.stdout+p.stderr)
 m=re.search(r'FAIL \((\d+) 项\)|FAILURES: (\d+)',p.stdout)
 count=int(next(g for g in m.groups() if g is not None)) if m else 0
 row={'label':label,'exit':p.returncode,'failure_count':count,'log':str(log),'command':cmd};results.append(row);print(json.dumps(row),flush=True)
try:
 run('sp17-green','github')
 pattern=r'^    def _clear_pending_index\(.*?(?=^    def |\Z)'
 oldfn=re.search(pattern,oldgh,re.M|re.S).group()
 new=re.sub(pattern,lambda m:oldfn,original[GH].decode(),flags=re.M|re.S)
 (R/GH).write_text(new);(W/'sp17-mutation.diff').write_text(__import__('difflib').unified_diff if False else '')
 run('sp17-revert-red','github')
finally: (R/GH).write_bytes(original[GH])
run('sp17-restored-green','github')
variants={}
s=original[RUN].decode()
variants['sp18']=s.replace('"--retry", "--form", "--upload-file", "--cert", "--key", "--cacert",','"--retry", "--form", "--upload-file", "--cert", "--key", "--cacert",\n    "--proxy", "--resolve", "--host", "--interface",')
variants['sp19']=s.replace('    if len(urls) != 1:\n        continue\n','').replace('if not host_is_standby(urls[0]):','if not any(host_is_standby(u) for u in urls):')
for name,mutation in variants.items():
 try:
  run(f'{name}-green','anchor');(R/RUN).write_text(mutation);run(f'{name}-revert-red','anchor')
 finally:(R/RUN).write_bytes(original[RUN])
 run(f'{name}-restored-green','anchor')
restored={str(p):(R/p).read_bytes()==data for p,data in original.items()}
(W/'mutation-results-7.json').write_text(json.dumps({'runs':results,'byte_restored':restored},indent=2));print(restored)
