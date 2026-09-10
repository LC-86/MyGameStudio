from pathlib import Path
import re,subprocess,os,shutil,json,hashlib,difflib
W=Path('/tmp/mgs-review9-3hpb5uhl');R=W/'mutation';shutil.copytree(W/'repo',R,ignore=shutil.ignore_patterns('__pycache__','.tmp'))
RUN=Path('acceptance/18-complete-package-acceptance/run.sh');p=R/RUN;s=p.read_text();original=p.read_bytes()
old=subprocess.check_output(['git','show',f'3f3031a:{RUN}'],cwd=W/'repro',text=True)
pat=r'^curl_direct_denied\(\) \{.*?^\}';oldfn=re.search(pat,old,re.M|re.S).group()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'))
cmd=['python3','-B','-c',"import sys,json;sys.path.insert(0,'tests');import test_plugin_package as t;t.test_accept18_probe_checks_anchored_to_events();print(json.dumps({'failures':t.FAILURES},ensure_ascii=False));sys.exit(bool(t.FAILURES))"]
results=[]
def run(label,expected):
    q=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True)
    (W/'logs'/f'mutation-{label}.log').write_text(q.stdout+q.stderr)
    data=json.loads(q.stdout.splitlines()[-1]);row={'id':label,'exit':q.returncode,'failure_count':len(data['failures']),'expected_count':expected,'matches_expected':len(data['failures'])==expected,'failures':data['failures']};results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    (W/'mutation-results-9.json').write_text(json.dumps({'runs':results},ensure_ascii=False,indent=2))
prefix=s.replace('                if not all(ch in CURL_PLAIN_SHORT for ch in body[:value_at]):\n                    return None\n','')
diagnostic=s.replace('r"^curl: \\((?:7|28)\\) (?:Failed to connect to|Couldn\'t connect to) "','r"(?:Failed to connect to|Couldn\'t connect to) "')
host=s.replace('m.group("host") == STANDBY_HOST','STANDBY_HOST in m.group("host")')
combined=s.replace('    def diagnostic_binds_standby(line):\n        m = connect_diag.search(line)\n        return m is not None and m.group("host") == STANDBY_HOST','    def diagnostic_binds_standby(line):\n        return re.search("failed to connect|couldn\'t connect|connection refused", line, re.I) and STANDBY_HOST in line')
variants={'prefix':(prefix,4),'diagnostic':(diagnostic,1),'host':(host,1),'combined_old':(combined,2)}
try:
    run('initial-green',0)
    p.write_text(re.sub(pat,lambda m:oldfn,s,flags=re.M|re.S));run('baseline-red',6)
    p.write_bytes(original);run('baseline-restored-green',0)
    for label,(v,expected) in variants.items():
        assert v!=s,label
        (W/f'{label}-mutation.diff').write_text(''.join(difflib.unified_diff(s.splitlines(True),v.splitlines(True),fromfile='current',tofile=label)))
        p.write_text(v);run(label+'-red',expected)
        p.write_bytes(original);run(label+'-restored-green',0)
finally:p.write_bytes(original)
restored=p.read_bytes()==original==(W/'repo'/RUN).read_bytes()
(W/'mutation-results-9.json').write_text(json.dumps({'runs':results,'byte_restored':restored,'run_sha256':hashlib.sha256(original).hexdigest()},ensure_ascii=False,indent=2))
