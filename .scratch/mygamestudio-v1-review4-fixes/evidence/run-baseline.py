import pathlib,os,subprocess,json,shutil,time
W=pathlib.Path(__file__).parent; C=W/'copy'; E=C/'.scratch/mygamestudio-v1-review3-fixes/evidence'
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(W)}
results=[]
def run(name,args):
 start=time.monotonic();p=subprocess.run(args,cwd=C,env=env,capture_output=True,text=True)
 (W/'logs'/f'{name}.log').write_text(p.stdout+p.stderr)
 r={'id':name,'command':args,'cwd':str(C),'exit':p.returncode,'seconds':round(time.monotonic()-start,2),'log':str(W/'logs'/f'{name}.log')};results.append(r)
 (W/'suite-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)); print(r,flush=True)
for p in (C/'plugin').rglob('__pycache__'):shutil.rmtree(p.resolve())
for name in ['plugin_package','runtime_gate','runtime_boundaries','records_backend','github_backend']:run(name,['python3','-B',f'tests/test_{name}.py'])
run('bash-syntax',['bash','-n','acceptance/18-complete-package-acceptance/run.sh'])
run('reproducible',['bash','dist/verify-reproducible.sh'])
run('driver-probes',['bash','acceptance/18-complete-package-acceptance/driver-probes.sh',str(W/'driver-env')])
