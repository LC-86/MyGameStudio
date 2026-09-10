from pathlib import Path
import subprocess,os,json,time
W=Path('/tmp/mgs-review10-j5225ubn'); R=W/'repo'
env={'PATH':os.environ['PATH'],'HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'ZDOTDIR':str(W/'home'),'LANG':'C','TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
commands=[(n,[str(W/n)]) for n in ['spec-custom-probes.py','spec-independent-probes.py','curl-new-probes.py','curl-extra-probes-5.py','path-extra-probes-5.py','curl-boundaries-probe.py','path-and-retained.py','mixed-layout-standards.py','curl-adversarial-7.py','new-probes-8.py','new-probes-9.py','parallel-curl-supplement.py']]
commands.insert(2,('spec-extra-pending.py',[str(W/'spec-extra-pending.py'),'--repo',str(R),'--out',str(W)]))
commands.extend([('mixed-spec-'+tag,[str(W/'mixed-layout-spec-agent.py'),'--out',str(W/('mixed-'+tag)),*flags]) for tag,flags in [('plain',[]),('guard',['--guard-each-path'])]])
rows=[]
for name,args in commands:
    start=time.monotonic()
    p=subprocess.run(['python3','-B',*args],cwd=W,env=env,capture_output=True,text=True,timeout=150)
    # Internal command/result pipes never become unfiltered terminal output.
    (W/'logs'/(name+'.log')).write_text(p.stdout+p.stderr)
    row={'name':name,'exit':p.returncode,'seconds':round(time.monotonic()-start,2),'command':['python3','-B',*args]};rows.append(row)
    (W/'history-execution-10.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(row),flush=True)
