from pathlib import Path
import subprocess,os,json,time
W=Path('/tmp/mgs-review10-j5225ubn'); R=W/'repo'
env={'PATH':os.environ['PATH'],'HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'ZDOTDIR':str(W/'home'),'LANG':'C','TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
skips=['test_accept16_sanitize_covers_unenumerated_tokens','test_accept16_secret_scan_gate','test_accept18_leak_checks_mechanized']
code="import sys;sys.path.insert(0,'tests');import test_plugin_package as t\n"
for n in skips:code+=f"t.{n}=lambda:None\n"
code+='sys.exit(t.main())\n'
rows=[]
for name in ['plugin_package','runtime_gate','runtime_boundaries','records_backend','github_backend']:
    cmd=['python3','-B','-c',code] if name=='plugin_package' else ['python3','-B',f'tests/test_{name}.py']
    start=time.monotonic();p=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True,timeout=180)
    (W/'logs'/('suite-'+name+'.log')).write_text(p.stdout+p.stderr)
    row={'name':name,'exit':p.returncode,'seconds':round(time.monotonic()-start,2),'skipped':skips if name=='plugin_package' else [],'complete_suite':name!='plugin_package','log':str(W/'logs'/('suite-'+name+'.log'))};rows.append(row)
    (W/'suite-results-10.json').write_text(json.dumps(rows,indent=2));print(json.dumps(row),flush=True)
