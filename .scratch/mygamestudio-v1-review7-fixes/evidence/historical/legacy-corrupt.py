from pathlib import Path
import sys,tempfile,json,hashlib
W=Path('/tmp/mgs-review7-ADyk4of1');sys.dont_write_bytecode=True;sys.path.insert(0,str(W/'repo/tests'))
import test_github_backend as gh
rows=[]
with tempfile.TemporaryDirectory(prefix='legacy-corrupt-',dir=W) as tmp:
 for mode in ['json','shape','receipt']:
  base=Path(tmp)/mode;project=gh.make_github_project(base/'project');fake=gh._OnceReadFailTransport();fake.seed_issue('01-task','Existing');backend=gh.backend_for(project,fake,base/'cache')
  fake.fail('PATCH','/issues/1','timeout');first=backend.append_result('01-task','body')
  current=backend._pending_index_file('01-task','body');legacy=backend._legacy_pending_index_file('01-task','body');pending=json.loads(current.read_text());pending.pop('comment_id')
  legacy.write_text('{' if mode=='json' else '{}' if mode=='shape' else json.dumps(pending));current.unlink();before=legacy.read_bytes()
  fake._fail=[];fake.read_fail=True;second=backend.append_result('01-task','body');backend._clear_pending_index('01-task','body')
  rows.append({'id':mode,'corrupt_disclosed':'不可读' in second.get('note',''),'posts':sum(m=='POST' and '/comments' in p for m,p,_ in fake.calls),'legacy_bytes_unchanged':legacy.exists() and legacy.read_bytes()==before,'current_created':current.exists(),'second':second})
(W/'legacy-corrupt-6.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print(json.dumps([{k:v for k,v in r.items() if k!='second'} for r in rows],ensure_ascii=False,indent=2))
