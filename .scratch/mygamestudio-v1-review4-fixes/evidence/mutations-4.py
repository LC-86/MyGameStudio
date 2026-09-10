import pathlib,subprocess,json,re,os,shutil,hashlib
W=pathlib.Path(__file__).parent; C=W/'mutation';repo=pathlib.Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
if not C.exists():
 C.mkdir(); archive=subprocess.check_output(['git','-C',str(repo),'archive','05a2776']); subprocess.run(['tar','-x','-C',str(C)],input=archive,check=True)
env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(W)}
module=C/'plugin/records/mgs_github.py';runsh=C/'acceptance/18-complete-package-acceptance/run.sh'
orig_module=module.read_bytes();orig_run=runsh.read_bytes()
old_module=subprocess.check_output(['git','-C',str(repo),'show','521c465:plugin/records/mgs_github.py'])
old_run=subprocess.check_output(['git','-C',str(repo),'show','521c465:acceptance/18-complete-package-acceptance/run.sh']).decode()
fn=lambda s,n:re.search(r'^'+n+r'\(\) \{.*?^\}',s,re.M|re.S).group()
results=[]
def check(name,suite):
 if suite=='anchor':
  cmd=['python3','-B','-c',"import sys,json;sys.path.insert(0,'tests');import test_plugin_package as t;t.test_accept18_probe_checks_anchored_to_events();print(json.dumps({'failures':t.FAILURES},ensure_ascii=False,indent=2));sys.exit(bool(t.FAILURES))"]
 else:cmd=['python3','-B',f'tests/test_{suite}.py']
 p=subprocess.run(cmd,cwd=C,env=env,text=True,capture_output=True)
 (W/'logs'/f'mutation-{name}-{suite}.log').write_text(p.stdout+p.stderr)
 r={'phase':name,'suite':suite,'exit':p.returncode,'log':str(W/'logs'/f'mutation-{name}-{suite}.log')};results.append(r);print(r,flush=True)
 (W/'mutation-results-4.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
try:
 for suite in ['github_backend','runtime_gate','anchor']:check('baseline',suite)
 module.write_bytes(old_module)
 for suite in ['github_backend','runtime_gate']:check('A-remove-SP7-fix',suite)
 module.write_bytes(orig_module)
 for suite in ['github_backend','runtime_gate']:check('A-restored',suite)
 # Mutant C intentionally overblocks every read-first failure. Use a sentinel
 # dictionary so failures reflect semantic regression, not a None crash.
 text=orig_module.decode();old='''            if pending is not None:
                return self._pending_recovery_result(
                    number, pending, read_first_failed, attempts)'''
 new='''            if True:
                return self._pending_recovery_result(
                    number, pending or {}, read_first_failed, attempts)'''
 assert old in text;module.write_text(text.replace(old,new))
 check('C-always-pending', 'github_backend')
 module.write_bytes(orig_module);check('C-restored','github_backend')
 for n,label in [('mcp_deny_anchor','B-restore-old-mcp-anchor'),('curl_direct_denied','D-restore-old-curl-anchor')]:
  current=orig_run.decode();runsh.write_text(current.replace(fn(current,n),fn(old_run,n)))
  check(label,'anchor');runsh.write_bytes(orig_run);check(label+'-restored','anchor')
finally:
 module.write_bytes(orig_module);runsh.write_bytes(orig_run)
 restored={'module_restored_byte_exact':module.read_bytes()==orig_module,'runsh_restored_byte_exact':runsh.read_bytes()==orig_run,'module_sha256':hashlib.sha256(orig_module).hexdigest(),'runsh_sha256':hashlib.sha256(orig_run).hexdigest()}
 (W/'mutation-restoration-4.json').write_text(json.dumps(restored,indent=2));print(restored)
