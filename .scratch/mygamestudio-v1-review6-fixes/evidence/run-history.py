import pathlib,re,os,subprocess,json,difflib
W=pathlib.Path('/tmp/mgs-review6-zonhimd1'); R=W/'repo'
(W/'copy').symlink_to(R,target_is_directory=True)
e=R/'.scratch/mygamestudio-v1-review5-fixes/evidence'
files={n:e/n for n in ['spec-extra-pending.py','curl-extra-probes-5.py','path-extra-probes-5.py']}
files.update({'spec-custom-probes.py':R/'.scratch/mygamestudio-v1-review3-fixes/evidence/spec-custom-probes.py','spec-independent-probes.py':R/'.scratch/mygamestudio-v1-review4-fixes/evidence/spec-independent-probes.py','curl-new-probes.py':R/'.scratch/mygamestudio-v1-review4-fixes/evidence/curl-new-probes.py'})
diffs=[]
for n,p in files.items():
    old=p.read_text(); s=old
    s=re.sub(r"ROOT = Path\('[^']+'\)",f"ROOT = Path('{W}')",s)
    if n=='spec-custom-probes.py':
        s=s.replace('[str(ev), tool, stage, wanted]',"[str(ev), tool, stage, wanted, 'write' if tool == 'mgs_write' else 'update']")
    if n in ['spec-extra-pending.py','spec-independent-probes.py']:
        s=s.replace(".glob('*.json')",".rglob('*.json')")
    if n=='spec-extra-pending.py':
        s=s.replace('    assert same_file',"    assert not same_file and backend._pending_index_file('01-task', A).parent == backend._pending_index_file('01-task', B).parent")
    (W/n).write_text(s)
    diffs.extend(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile=str(p.relative_to(R)),tofile=str(W/n)))
(W/'probe-adaptation.diff').write_text(''.join(diffs))
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'))
res=[]
for n in files:
    cmd=['python3','-B',str(W/n)]
    if n=='spec-extra-pending.py': cmd += ['--repo',str(R),'--out',str(W)]
    with (W/'logs'/n.replace('.py','.log')).open('w') as f:
        p=subprocess.run(cmd,env=env,cwd=W,stdout=f,stderr=subprocess.STDOUT)
    row={'name':n,'source':str(files[n].relative_to(R)),'exit':p.returncode,'command':cmd};res.append(row);print(json.dumps(row),flush=True)
(W/'history-execution.json').write_text(json.dumps(res,indent=2))
