from pathlib import Path
import re,subprocess,os,shutil,json,hashlib,difflib
W=Path('/tmp/mgs-review8-60iu1bo4'); R=W/'mutation'
shutil.copytree(W/'repo',R,ignore=shutil.ignore_patterns('__pycache__','.tmp'))
RUN=Path('acceptance/18-complete-package-acceptance/run.sh'); p=R/RUN
s=p.read_text(); original=p.read_bytes()
old=subprocess.check_output(['git','show',f'3e6ae30:{RUN}'],cwd=W/'repro',text=True)
pat=r'^curl_direct_denied\(\) \{.*?^\}'
oldfn=re.search(pat,old,re.M|re.S).group()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'))
cmd=['python3','-B','-c',"import sys,json;sys.path.insert(0,'tests');import test_plugin_package as t;t.test_accept18_probe_checks_anchored_to_events();print(json.dumps({'failures':t.FAILURES},ensure_ascii=False));sys.exit(bool(t.FAILURES))"]
results=[]
def run(label,expected):
    q=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True)
    (W/'logs'/f'mutation-{label}.log').write_text(q.stdout+q.stderr)
    data=json.loads(q.stdout.splitlines()[-1]); row={'id':label,'exit':q.returncode,'failure_count':len(data['failures']),'expected_count':expected,'matches_expected':len(data['failures'])==expected,'failures':data['failures']};results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    (W/'mutation-results-8.json').write_text(json.dumps({'runs':results},ensure_ascii=False,indent=2))
short=s.replace('CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzZDJg")','CURL_VALUE_SHORT = set("HmXdoAuwbceEKrTQyYzZDxUJg")')
redirect=s.replace('CURL_PLAIN_SHORT = set("sSkvIifnN46q")','CURL_PLAIN_SHORT = set("sSLkvIifnN46q")').replace('"--silent", "--show-error",','"--location", "--silent", "--show-error",')
consume=re.sub(r'            value_at = next\(\(j for j, ch in enumerate\(body\)\n                             if ch in CURL_VALUE_SHORT\), None\)\n            if value_at is not None:\n                i \+= 2 if value_at == len\(body\) - 1 else 1\n                continue', '            if any(ch in CURL_VALUE_SHORT for ch in body):\n                i += 2\n                continue',s)
oldwords=re.search(r'^fail_words = .*?(?=^SHELLS)',oldfn,re.M|re.S).group().replace('fail_words','connect_fail_words')
fail=re.sub(r'^connect_fail_words = .*?(?=^SHELLS)',lambda m:oldwords,s,flags=re.M|re.S)
fail=fail.replace('any(connect_fail_words.search(line) and STANDBY_HOST in line\n                      for line in output.splitlines())','connect_fail_words.search(output)')
variants={'A-short':(short,1),'B-redirect':(redirect,1),'C-consumption':(consume,1),'D-failure':(fail,3)}
try:
    run('initial-green',0)
    p.write_text(re.sub(pat,lambda m:oldfn,s,flags=re.M|re.S));run('baseline-red',10)
    p.write_bytes(original);run('baseline-restored-green',0)
    for label,(v,expected) in variants.items():
        assert v!=s,label
        (W/f'{label}-mutation.diff').write_text(''.join(difflib.unified_diff(s.splitlines(True),v.splitlines(True),fromfile='current',tofile=label)))
        p.write_text(v);run(label+'-red',expected)
        p.write_bytes(original);run(label+'-restored-green',0)
finally:p.write_bytes(original)
restored=p.read_bytes()==original==(W/'repo'/RUN).read_bytes()
(W/'mutation-results-8.json').write_text(json.dumps({'runs':results,'byte_restored':restored,'run_sha256':hashlib.sha256(original).hexdigest()},ensure_ascii=False,indent=2))
