#!/usr/bin/env python3
import sys,json,importlib.util,threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
sys.dont_write_bytecode=True
ROOT=Path('/tmp/mgs-review6-zonhimd1/spec-agent/repo-tracked');OUT=Path('/tmp/mgs-review6-zonhimd1/spec-agent/pending-boundary-run')
OUT.mkdir();sys.path.insert(0,str(ROOT/'tests'))
import test_github_backend as gh
sp=importlib.util.spec_from_file_location('mgs_github_old',OUT.parent/'mgs_github_old.py');old=importlib.util.module_from_spec(sp);sp.loader.exec_module(old);old.TransportError=gh.mgs_github.TransportError
A,B='collision-result-79891','collision-result-80657'
rows=[]
def setup(name):
    base=OUT/name;project=gh.make_github_project(base/'project');fake=gh._OnceReadFailTransport();fake.seed_issue('01-task','Existing');backend=gh.backend_for(project,fake,base/'cache');return base,fake,backend
# Two independent full hashes sharing one short-digest directory: genuinely overlap
# mkdir/write execution, 20 fresh cache directories; no same-request promise implied.
for i in range(20):
    base,fake,backend=setup(f'concurrent-{i}');barrier=threading.Barrier(2)
    def worker(body):
        barrier.wait()
        return backend._record_pending_index('01-task',body,{'id':1 if body==A else 2},'fake://receipt','timeout')
    with ThreadPoolExecutor(max_workers=2) as pool:
        errs=list(pool.map(worker,[A,B]))
    loaded=[backend._load_pending_index('01-task',body) for body in [A,B]]
    rows.append({'id':f'concurrent-distinct-full-hashes-{i}','pass':errs==[None,None] and [p['args']['result_markdown'] for p in loaded]==[A,B] and len(list((base/'cache'/'pending-index').rglob('*.json')))==2})
# Interrupt migration at a precise stage using OSError; all receipt creation is
# performed by the actual old implementation, not constructed data.
for mode in ['before-write','after-partial-write','before-unlink']:
    base,fake,backend=setup('migration-'+mode);legacy=old.GithubBackend(backend.config,fake,base/'cache');fake.fail('PATCH','/issues/1','timeout');first=legacy.append_result('01-task',A)
    current=backend._pending_index_file('01-task',A);oldfile=legacy._pending_index_file('01-task',A)
    orig_write=Path.write_text;orig_unlink=Path.unlink
    def write(self,text,*args,**kwargs):
        if self==current:
            if mode=='after-partial-write': orig_write(self,'{',encoding='utf-8')
            raise OSError('injected migration write failure')
        return orig_write(self,text,*args,**kwargs)
    def unlink(self,*args,**kwargs):
        if self==oldfile: raise OSError('injected migration unlink failure')
        return orig_unlink(self,*args,**kwargs)
    target='write_text' if mode!='before-unlink' else 'unlink';func=write if target=='write_text' else unlink
    with patch.object(Path,target,func): loaded=backend._load_pending_index('01-task',A)
    again=backend._load_pending_index('01-task',A)
    fake._fail=[];fake.read_fail=True;retry=backend.append_result('01-task',A)
    backend._clear_pending_index('01-task',A)
    paths=[str(p.relative_to(base)) for p in (base/'cache'/'pending-index').rglob('*.json')]
    rows.append({'id':'migration-'+mode,'first_comment':first.get('comment_id'),'first_load_comment':loaded.get('comment_id'),'second_load_comment':again.get('comment_id'),'second_load_corrupt':bool(again.get('corrupt')),'retry':retry,'posts':sum(m=='POST' and '/comments' in p for m,p,_ in fake.calls),'remaining_after_clear':paths,'observation':('Truncated current shadows healthy legacy; conservative corrupt disclosure, no re-POST; automatic migration is not retried.' if mode=='after-partial-write' else 'Retry remains safe, matching receipts clear from both layouts.')})
# Exact identity normalization: distinct Unicode forms and control characters
# remain distinct hashes and exact payloads. Long result body does not enter path.
base,fake,backend=setup('unicode')
ids=[('任务-é','NFC'),('任务-e\u0301','NFD'),('任务-\t','TAB'),('任务-\n','NEWLINE'),('任务-long','长'*100000)]
paths=[]
for index,(identity,body) in enumerate(ids):
    err=backend._record_pending_index(identity,body,{'id':index+1},'fake://receipt','timeout');p=backend._pending_index_file(identity,body);paths.append(p);loaded=backend._load_pending_index(identity,body)
    rows.append({'id':'identity-'+str(index),'identity_repr':repr(identity),'body_length':len(body),'pass':err is None and loaded['args']=={'identity':identity,'result_markdown':body}})
rows.append({'id':'unicode-control-path-distinctness','pass':len(set(paths))==len(paths)})
(OUT/'result.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print(json.dumps({'passed_assertions':sum(r.get('pass') is True for r in rows),'failed_assertions':sum(r.get('pass') is False for r in rows),'migration_observations':[r for r in rows if r['id'].startswith('migration-')]},ensure_ascii=False,indent=2))
