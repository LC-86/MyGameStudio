import json, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path('/tmp/mgs-review8-60iu1bo4/repo/tests')))
import test_github_backend as t
with tempfile.TemporaryDirectory(prefix='mixed-layout-',dir=Path(__file__).parent) as tmp:
 base=Path(tmp)
 root=t.make_github_project(base/'project')
 cache=base/'cache'
 fake=t._OnceReadFailTransport()
 fake.seed_issue('01-task','甲任务')
 backend=t.backend_for(root,fake,cache)
 a,b='collision-result-79891','collision-result-80657'
 fake.fail('PATCH','/issues/1','timeout')
 first_b=backend.append_result('01-task',b)
 b_current=backend._pending_index_file('01-task',b)
 b_legacy=backend._legacy_pending_index_file('01-task',b)
 b_current.rename(b_legacy) # simulate existing healthy pre-upgrade ledger
 fake.read_fail=True
 first_a=backend.append_result('01-task',a)
 before=[str(p.relative_to(cache)) for p in (cache/'pending-index').rglob('*.json')]
 fake._fail=[]
 restored_a=backend.append_result('01-task',a)
 after=[str(p.relative_to(cache)) for p in (cache/'pending-index').rglob('*.json')]
 fake.read_fail=True
 restored_b=backend.append_result('01-task',b)
 summary={'first_a_partial':first_a.get('partial'),'first_b_partial':first_b.get('partial'),
 'before_a_recovery':before,'after_a_recovery':after,'b_legacy_deleted':not b_legacy.exists(),
 'a_recovery_id':restored_a.get('comment_id'),'b_initial_id':first_b.get('comment_id'),
 'b_recovery_id':restored_b.get('comment_id'),'post_count':sum(m=='POST' and '/comments' in p for m,p,_ in fake.calls),
 'a_comment_count':sum(c['body']==f'任务:01-task\n\n{a}' for c in fake.comments[1]),
 'b_comment_count':sum(c['body']==f'任务:01-task\n\n{b}' for c in fake.comments[1]),
 'b_recovery':restored_b}
 print(json.dumps(summary,ensure_ascii=False,indent=2))
