import os,sys,subprocess,json,pathlib,shutil,time
W=pathlib.Path('/tmp/mgs-review9-3hpb5uhl'); R=W/'repo'; L=W/'logs'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'))
for p in (R/'plugin').rglob('__pycache__'):
    if p.is_dir(): shutil.rmtree(p.resolve())
results=[]
def run(name,cmd,cwd=R):
    start=time.monotonic()
    with (L/(name+'.log')).open('w') as out:
        p=subprocess.run(cmd,cwd=cwd,env=env,stdout=out,stderr=subprocess.STDOUT)
    results.append({'name':name,'command':cmd,'cwd':str(cwd),'exit':p.returncode,'seconds':round(time.monotonic()-start,2),'log':str(L/(name+'.log'))})
    (W/'suite-results.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results[-1]),flush=True)
for name in ['plugin_package','runtime_gate','runtime_boundaries','records_backend','github_backend']:
    run(name,['python3','-B',f'tests/test_{name}.py'])
