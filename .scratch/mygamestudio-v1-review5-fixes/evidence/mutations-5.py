import json, os, pathlib, re, subprocess, time
W=pathlib.Path(__file__).parent
C=W/'mutation'
ENV={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(W/'tmp')}
GH='plugin/records/mgs_github.py'
RUN='acceptance/18-complete-package-acceptance/run.sh'
original={p:(C/p).read_bytes() for p in [GH,RUN]}
old={p:subprocess.check_output(['git','show','8dfd706:'+p],cwd=C) for p in [GH,RUN]}
results=[]
def execute(name,cmd):
    p=subprocess.run(cmd,cwd=C,env=ENV,text=True,capture_output=True)
    log=W/'logs'/(name+'.log');log.write_text(p.stdout+p.stderr)
    r={'name':name,'cmd':cmd,'exit':p.returncode,'log':str(log),'output':p.stdout+p.stderr}
    results.append(r)
    print(json.dumps({'name':name,'exit':p.returncode,'output':r['output']},ensure_ascii=False),flush=True)
    return p.returncode
anchor=['python3','-B','-c',"import sys;sys.path.insert(0,'tests');import test_plugin_package as t;t.test_accept18_probe_checks_anchored_to_events();print('FAILURES',len(t.FAILURES));print('\\n'.join(t.FAILURES));sys.exit(bool(t.FAILURES))"]
github=['python3','-B','tests/test_github_backend.py']
gate=['python3','-B','tests/test_runtime_gate.py']
try:
    assert execute('mutation-baseline-github',github)==0
    assert execute('mutation-baseline-gate',gate)==0
    assert execute('mutation-baseline-anchor',anchor)==0
    (C/GH).write_bytes(old[GH])
    assert execute('mutation-ticket01-revert-github',github)!=0
    assert execute('mutation-ticket01-revert-gate',gate)!=0
    (C/GH).write_bytes(original[GH])
    assert execute('mutation-ticket01-restored-github',github)==0
    assert execute('mutation-ticket01-restored-gate',gate)==0
    for fn in ['mcp_deny_anchor','curl_direct_denied']:
        pattern=r'^'+fn+r'\(\) \{.*?^\}'
        previous=re.search(pattern,old[RUN].decode(),re.M|re.S).group()
        changed=re.sub(pattern,lambda _:previous,original[RUN].decode(),flags=re.M|re.S)
        (C/RUN).write_text(changed)
        assert execute('mutation-ticket02-revert-'+fn,anchor)!=0
        (C/RUN).write_bytes(original[RUN])
        assert execute('mutation-ticket02-restored-'+fn,anchor)==0
finally:
    for path,data in original.items(): (C/path).write_bytes(data)
    (W/'mutation-results-5.json').write_text(json.dumps({'results':results,'restored_bytes':{p:(C/p).read_bytes()==data for p,data in original.items()}},ensure_ascii=False,indent=2))
