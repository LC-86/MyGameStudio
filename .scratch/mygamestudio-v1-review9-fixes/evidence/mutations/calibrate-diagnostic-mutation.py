from pathlib import Path
import subprocess,json,os,difflib
W=Path('/tmp/mgs-review9-3hpb5uhl');R=W/'mutation';p=R/'acceptance/18-complete-package-acceptance/run.sh';original=p.read_bytes();s=original.decode()
v=s.replace('r"^curl: \\((?:7|28)\\) (?:Failed to connect to|Couldn\'t connect to) "','r"(?:Failed to connect to|Couldn\'t connect to) "').replace('r"(?P<host>\\S+?)(?: |:)"','r"(?P<host>\\S+?)(?: |:|$)"')
assert v!=s
(W/'diagnostic-initial-mutation.diff').write_bytes((W/'diagnostic-mutation.diff').read_bytes())
(W/'diagnostic-mutation.diff').write_text(''.join(difflib.unified_diff(s.splitlines(True),v.splitlines(True),fromfile='current',tofile='diagnostic-form-relaxed-retain-host-equality')))
j=json.loads((W/'mutation-results-9.json').read_text());(W/'mutation-initial-results-9.json').write_text(json.dumps(j,ensure_ascii=False,indent=2))
cmd=['python3','-B','-c',"import sys,json;sys.path.insert(0,'tests');import test_plugin_package as t;t.test_accept18_probe_checks_anchored_to_events();print(json.dumps({'failures':t.FAILURES},ensure_ascii=False));sys.exit(bool(t.FAILURES))"]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'))
try:
    for label,body,expected in [('diagnostic-red',v.encode(),1),('diagnostic-restored-green',original,0)]:
        p.write_bytes(body);q=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True)
        (W/'logs'/f'mutation-{label}-calibrated.log').write_text(q.stdout+q.stderr)
        data=json.loads(q.stdout.splitlines()[-1]);row={'id':label,'exit':q.returncode,'failure_count':len(data['failures']),'expected_count':expected,'matches_expected':len(data['failures'])==expected,'failures':data['failures']}
        j['runs']=[row if r['id']==label else r for r in j['runs']];print(json.dumps(row,ensure_ascii=False))
finally:p.write_bytes(original)
j['initial_diagnostic_calibration']={'failure_count':0,'only_error_prefix_removed':True,'reason':'Original SP25 body ends immediately after hostname. The regex also requires space/colon after host. Calibrated diagnostic-form relaxation removes error prefix AND allows end-of-line after host; host equality remains unchanged.','evidence':'mutation-initial-results-9.json'}
j['byte_restored']=p.read_bytes()==original==(W/'repo/acceptance/18-complete-package-acceptance/run.sh').read_bytes()
(W/'mutation-results-9.json').write_text(json.dumps(j,ensure_ascii=False,indent=2))
