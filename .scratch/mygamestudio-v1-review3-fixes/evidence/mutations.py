import ast, hashlib, json, os, pathlib, re, subprocess
W = pathlib.Path(__file__).parent
C = W / 'copy'
REPO = pathlib.Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
ENV = {**os.environ, 'TMPDIR': '/tmp', 'PYTHONDONTWRITEBYTECODE': '1'}

def old(path, rev='9376dec'):
    return subprocess.check_output(['git', 'show', f'{rev}:{path}'], cwd=REPO, text=True)

def func(text, name):
    node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == name)
    return ''.join(text.splitlines(keepends=True)[node.lineno-1:node.end_lineno])

def test(module, function, runtime=False):
    code = f"import sys,json,tempfile;from pathlib import Path;sys.path.insert(0,{str(C/'tests')!r});import {module} as t;"
    if runtime:
        code += f"\nwith tempfile.TemporaryDirectory(dir='/tmp') as d:t.{function}(Path(d))\n"
    else:
        code += f't.{function}();'
    code += "print(json.dumps(t.FAILURES,ensure_ascii=False,indent=2));sys.exit(bool(t.FAILURES))"
    p = subprocess.run(['python3','-B','-c',code], cwd=C, env=ENV, capture_output=True, text=True)
    return {'exit': p.returncode, 'output': p.stdout+p.stderr}

results=[]
def mutation(name, path, change, module, function, runtime=False):
    p=C/path; source=p.read_text(); changed=change(source); assert source!=changed
    before=test(module,function,runtime)
    try:
        p.write_text(changed)
        red=test(module,function,runtime)
    finally:
        p.write_text(source)
    after=test(module,function,runtime)
    row={'id':name,'path':path,'test':module+'.'+function,'before':before,'mutation':red,'restored':after,
         'byte_restored':p.read_bytes()==source.encode(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    results.append(row)
    (W/'mutation-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(name, before['exit'], red['exit'], after['exit'], flush=True)

runtime='plugin/runtime/mgs_runtime.py'
block='''            if denial is None:
                config, resource, note, config_denial = (
                    self._remote_config_state(policy, config_rel, action,
                                              payload))
                if config_denial is not None:
                    denial = (config_denial[0], config_denial[1], None)
'''
def remove_config(s):
    assert s.count(block)==1
    return s.replace(block,'')
mutation('01-SP1-lock-config',runtime,remove_config,'test_runtime_gate','review2_sp1_section',True)
github='plugin/records/mgs_github.py'
mutation('02-SP2-partial-and-adoption',github,lambda s:s.replace(func(s,'append_result'),func(old(github),'append_result')),'test_github_backend','test_append_result_partial_success_and_retry_completion')
mutation('02-SP3-repo-identity',github,lambda s:s.replace(func(s,'_save_draft'),func(old(github),'_save_draft')),'test_github_backend','test_draft_identity_includes_repo_cross_repo')
mutation('02-partial-draft-retention',github,lambda s:s.replace('and not outcome.get("partial")',''),'test_github_backend','test_append_result_draft_replay_partial_keeps_draft')
scanner='acceptance/16-producer-complete-loop/secret_scan.py'
mutation('03-SP4-per-root-scan',scanner,lambda s:s.replace(func(s,'iter_files'),func(old(scanner),'iter_files').replace('roots: list[str]','roots: list[str], errors: list[str]')),'test_plugin_package','test_accept16_secret_scan_gate')
run='acceptance/18-complete-package-acceptance/run.sh'
def shellfunc(s,name):return re.search(r'^'+name+r'\(\) \{.*?^\}',s,re.M|re.S).group(0)
mutation('03-SP5-sanitize',run,lambda s:s.replace(shellfunc(s,'sanitize'),shellfunc(old(run),'sanitize')),'test_plugin_package','test_accept18_leak_checks_mechanized')
def leak(s):return re.search(r'^LEAK=0\n.*?^check "原始令牌与替身凭据未泄漏到证据与项目[^\n]*$',s,re.M|re.S).group(0)
mutation('03-SP5-scan-wiring',run,lambda s:s.replace(leak(s),leak(old(run))),'test_plugin_package','test_accept18_leak_checks_mechanized')
def legacy_r1(s):
    current=re.search(r'^check "R1 记录 path 拒绝.*?\n  test .*? = "OK"$',s,re.M|re.S).group(0)
    legacy=re.search(r'^if grep -Eq.*?^fi$',old(run),re.M|re.S).group(0)
    return s.replace(current,legacy)
mutation('04-SP6-r1-legacy-check',run,legacy_r1,'test_plugin_package','test_accept18_probe_checks_anchored_to_events')
assert all(r['before']['exit']==0 and r['mutation']['exit']!=0 and r['restored']['exit']==0 and r['byte_restored'] for r in results)
