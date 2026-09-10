from pathlib import Path
import re,subprocess,os,shutil,json,hashlib,difflib
W=Path('/tmp/mgs-review10-j5225ubn');S=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio');R=W/'mutations/repo'
shutil.copytree(W/'repo/acceptance/18-complete-package-acceptance',R/'acceptance/18-complete-package-acceptance')
(R/'tests').mkdir();shutil.copyfile(W/'repo/tests/test_plugin_package.py',R/'tests/test_plugin_package.py')
RUN=Path('acceptance/18-complete-package-acceptance/run.sh');p=R/RUN;s=p.read_text();original=p.read_bytes()
old=subprocess.check_output(['git','show',f'e3741c6:{RUN}'],cwd=S,text=True)
pat=r'^curl_direct_denied\(\) \{.*?^\}';oldfn=re.search(pat,old,re.M|re.S).group()
env={'PATH':os.environ['PATH'],'HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'LANG':'C','TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
cmd=['python3','-B','-c',"import sys,json;sys.path.insert(0,'tests');import test_plugin_package as t;t.test_accept18_probe_checks_anchored_to_events();print(json.dumps({'failures':t.FAILURES},ensure_ascii=False));sys.exit(bool(t.FAILURES))"]
results=[]
def run(label,expected):
 q=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True)
 (W/'logs'/f'mutation-{label}.log').write_text(q.stdout+q.stderr)
 data=json.loads(q.stdout.splitlines()[-1]);row={'id':label,'exit':q.returncode,'failure_count':len(data['failures']),'expected_count':expected,'matches_expected':len(data['failures'])==expected,'failures':data['failures']};results.append(row)
 print(json.dumps({k:v for k,v in row.items() if k!='failures'}),flush=True)
 (W/'mutation-results-10.json').write_text(json.dumps({'runs':results},ensure_ascii=False,indent=2))
short=s.replace('CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzD")','CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzZDJg")').replace('CURL_PLAIN_SHORT = set("sSkvIifnN46qgJZ")','CURL_PLAIN_SHORT = set("sSkvIifnN46q")')
retry=s.replace('    "--form", "--upload-file",','    "--retry", "--form", "--upload-file",')
glob=s.replace('            if any(any(ch in arg for ch in "{}[]") for arg in args[i + 1:]):\n                return None\n','').replace('        if any(ch in tok for ch in "{}[]"):\n            return None\n','')
try:
 run('initial-green',0)
 p.write_text(re.sub(pat,lambda m:oldfn,s,flags=re.M|re.S));run('baseline-current-all-assertions',9)
 p.write_bytes(original);run('baseline-restored-green',0)
 for label,v,count in [('short',short,5),('retry',retry,2),('glob',glob,2)]:
  assert v!=s
  (W/'mutations'/f'{label}.diff').write_text(''.join(difflib.unified_diff(s.splitlines(True),v.splitlines(True),fromfile='current',tofile=label)))
  p.write_text(v);run(label+'-red',count)
  p.write_bytes(original);run(label+'-restored-green',0)
finally:p.write_bytes(original)
(W/'mutation-results-10.json').write_text(json.dumps({'runs':results,'byte_restored':p.read_bytes()==original==(S/RUN).read_bytes(),'run_sha256':hashlib.sha256(original).hexdigest()},ensure_ascii=False,indent=2))
