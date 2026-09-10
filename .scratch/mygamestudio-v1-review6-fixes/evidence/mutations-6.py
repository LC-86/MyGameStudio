from pathlib import Path
import subprocess,shutil,os,json,re,hashlib
W=Path('/tmp/mgs-review6-zonhimd1'); R=W/'mutation'
shutil.copytree(W/'repro',R,ignore=shutil.ignore_patterns('.git','__pycache__'))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'))
GH=Path('plugin/records/mgs_github.py'); RUN=Path('acceptance/18-complete-package-acceptance/run.sh')
original={p:(R/p).read_bytes() for p in [GH,RUN]}
old={p:subprocess.check_output(['git','show',f'1eef7d8:{p}'],cwd=W/'repro') for p in [GH,RUN]}
results=[]
def run(label,kind):
    cmd=['python3','-B','tests/test_github_backend.py'] if kind=='github' else ['python3','-B','-c',"import sys;sys.path.insert(0,'tests');import test_plugin_package as t;t.test_accept18_probe_checks_anchored_to_events();print('FAILURES:',len(t.FAILURES));print('\\n'.join(t.FAILURES));sys.exit(bool(t.FAILURES))"]
    p=subprocess.run(cmd,cwd=R,env=env,capture_output=True,text=True)
    log=W/'logs'/f'mutation-{label}.log';log.write_text(p.stdout+p.stderr)
    row={'label':label,'exit':p.returncode,'log':str(log),'command':cmd};results.append(row);print(json.dumps(row),flush=True)
try:
    run('ticket01-green','github'); (R/GH).write_bytes(old[GH]); run('ticket01-revert-red','github')
finally: (R/GH).write_bytes(original[GH])
run('ticket01-restored-green','github')
for name,fn in [('sp16','mcp_deny_anchor'),('sp15','curl_direct_denied')]:
    pattern=rf'^{fn}\(\) \{{.*?^\}}'
    try:
        run(f'{name}-green','anchor')
        text=original[RUN].decode(); prev=re.search(pattern,old[RUN].decode(),re.M|re.S).group()
        text=re.sub(pattern,lambda m:prev,text,flags=re.M|re.S)
        (R/RUN).write_text(text)
        run(f'{name}-revert-red','anchor')
    finally: (R/RUN).write_bytes(original[RUN])
    run(f'{name}-restored-green','anchor')
restored={str(p):(R/p).read_bytes()==data for p,data in original.items()}
(W/'mutation-results-6.json').write_text(json.dumps({'runs':results,'byte_restored':restored},indent=2));print(restored)
