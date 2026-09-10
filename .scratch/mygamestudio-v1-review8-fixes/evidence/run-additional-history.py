import pathlib,subprocess,os,json
W=pathlib.Path('/tmp/mgs-review8-60iu1bo4')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'),CURL_HOME=str(W/'home'))
commands=[('curl-boundaries',['curl-boundaries-probe.py']),('path-and-retained',['path-and-retained.py']),('mixed-standards',['mixed-layout-standards.py']),('mixed-spec-plain',['mixed-layout-spec-agent.py','--out',str(W/'mixed-plain')]),('mixed-spec-guard',['mixed-layout-spec-agent.py','--out',str(W/'mixed-guard'),'--guard-each-path'])]
out=[]
for name,args in commands:
    cmd=['python3','-B',str(W/args[0]),*args[1:]]
    with (W/'logs'/f'{name}.log').open('w') as f:p=subprocess.run(cmd,cwd=W,env=env,stdout=f,stderr=subprocess.STDOUT)
    row={'id':name,'command':cmd,'exit':p.returncode};out.append(row);print(json.dumps(row),flush=True)
(W/'additional-history-execution.json').write_text(json.dumps(out,indent=2))
