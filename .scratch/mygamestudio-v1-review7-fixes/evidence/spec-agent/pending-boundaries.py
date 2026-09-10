"""Additional current/legacy identity and corruption checks; local files only."""
import copy,json,sys,unicodedata
from pathlib import Path
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'repo/tests'))
import test_github_backend as gh
base=W/'boundary-cases';base.mkdir();rows=[]
own=('01-task','结果 café \t\n😀'); foreign=('01-task','结果 cafe\u0301 \t\n😀')
def healthy(body=own[1]):return gh._pending_registration_content('01-task',body,5101,'#issuecomment-5101')
variants=[('invalid-json',b'{not json',False),('invalid-utf8',b'\xff',False),('json-null',None,False),('json-list',[],False),('missing-args',{'op':'append_result','repo':gh.REPO,'comment_id':5101,'ref':'#issuecomment-5101'},False),('foreign-unicode',healthy(foreign[1]),False)]
for key,val in [('comment_id',None),('ref',None),('ref',''),('ref',[]),('op','APPEND_RESULT'),('repo',gh.REPO+' '),('args',{'identity':'01-task','result_markdown':own[1],'extra':'unexpected'})]:
 d=healthy();d[key]=val;variants.append((f'field-{key}-{len(variants)}',d,False))
d=healthy();d.update({'future_field':{'nested':[1,'extra',True]},'note':'保留额外字段'});variants.append(('top-level-extra',d,True))
for name,content,clear in variants:
 for side in ['current','legacy']:
  home=base/f'{name}-{side}';root=gh.make_github_project(home/'project');be=gh.backend_for(root,gh.FakeTransport(),home/'cache')
  cur=be._pending_index_file(*own);leg=be._legacy_pending_index_file(*own)
  tested,other=(cur,leg) if side=='current' else (leg,cur)
  for p in [tested,other]:p.parent.mkdir(parents=True,exist_ok=True)
  raw=content if isinstance(content,bytes) else json.dumps(content,ensure_ascii=False).encode()
  tested.write_bytes(raw);other.write_text(json.dumps(healthy(),ensure_ascii=False))
  be._clear_pending_index(*own)
  checks={'tested_side_expected':tested.exists()!=clear,'healthy_other_side_cleared':not other.exists(),'preserved_bytes':clear or tested.read_bytes()==raw}
  rows.append({'id':f'{name}-{side}','checks':checks,'pass':all(checks.values())})
# A result body is an exact string identity: every Unicode/whitespace variant
# independently addresses its own receipt and must not remove the base receipt.
for i,body in enumerate([own[1],foreign[1],own[1]+' ',own[1]+'\u200b',own[1].replace('\t',' '),own[1].replace('\n','\r\n')]):
 home=base/f'identity-{i}';root=gh.make_github_project(home/'project');be=gh.backend_for(root,gh.FakeTransport(),home/'cache')
 be._record_pending_index('01-task',own[1],{'id':5101},'#issuecomment-5101','local test')
 path=be._pending_index_file(*own);be._clear_pending_index('01-task',body)
 rows.append({'id':f'exact-identity-{i}','pass':path.exists()==(body!=own[1])})
result={'rows':rows,'case_count':len(rows),'assertions':sum(len(r.get('checks',{'pass':r['pass']})) for r in rows),'failed':sum(not r['pass'] for r in rows),'real_remote_calls':0}
(W/'pending-boundaries.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'}))
