import sys,json,tempfile,threading,hashlib
from pathlib import Path
sys.dont_write_bytecode=True
r=Path(__file__).parent;c=r/'copy'
sys.path.insert(0,str(c/'tests'))
import test_github_backend as gh
import test_runtime_gate as rt
results=[]
with tempfile.TemporaryDirectory(dir='/tmp',prefix='mgs-s6-crossrepo-') as temp:
 b=Path(temp); root=gh.make_github_project(b/'p'); cfg=gh.mgs_records.load_config(root)
 old={**cfg,'repo':{'host':'github.com','owner':'old-owner','repo':'private-repo'},'external':'github.com/old-owner/private-repo:issues-write(test)'}
 fake=gh.FakeTransport(); fake.offline()
 previous=gh.mgs_github.GithubBackend(old,fake,b/'cache'); current=gh.mgs_github.GithubBackend(cfg,fake,b/'cache')
 real=gh.mgs_github._dt.datetime
 class FixedDatetime(real):
  @classmethod
  def now(cls,tz=None): return cls(2026,9,9,1,2,3,tzinfo=tz)
 gh.mgs_github._dt.datetime=FixedDatetime
 try:
  a=previous.create_task('09-same','same title',{'当前目标':'same goal'})
  z=current.create_task('09-same','same title',{'当前目标':'same goal'})
 finally: gh.mgs_github._dt.datetime=real
 drafts=[json.loads(p.read_text()) for p in (b/'cache/drafts').glob('*.json')]
 online=gh.FakeTransport(); current=gh.mgs_github.GithubBackend(cfg,online,b/'cache'); publish=current.publish_drafts()
 results.append({'id':'S6-cross-repo-idempotence','first':a,'second':z,'draft_count':len(drafts),'draft_repositories':[d['repo'] for d in drafts],'published_count':publish['published_count'],'writes':[x[0:2] for x in online.calls if x[0]=='POST'],'observed_bug':a['draft']==z['draft'] and len(drafts)==1})
with tempfile.TemporaryDirectory(dir='/tmp',prefix='mgs-remote-revoke-') as temp:
 b=Path(temp); project=gh.make_github_project(b/'project'); runtime=b/'runtime'
 svc=rt.GateService(runtime); peer=rt.GateService(runtime)
 resources=['github://github.com/mygamestudio/issue-accept/issues/**','docs/mygamestudio/CONFIG.md']
 svc.init_policy(project,{'producer':resources},{'production':None})
 inst=svc.create_instance('producer','remote','production',resources)
 admin=svc.create_instance('producer','config-update','production',resources)
 svc._write_json('remote.json',{'github':{'api_base':'http://unused.invalid','token_env':'MGS_TEST_UNUSED','cache_dir':str(b/'cache')}})
 transport=gh.FakeTransport(); transport.seed_issue('01-task','Existing')
 real_lock=svc._locked; waiting=threading.Event(); resume=threading.Event(); outcome={}
 def paused_lock():
  if threading.current_thread().name=='remote-writer':
   waiting.set()
   if not resume.wait(10):raise RuntimeError('pause timed out')
  return real_lock()
 svc._locked=paused_lock
 def worker():
  try: outcome['inflight']=svc.remote_record(inst.token,'append-result',{'identity':'01-task','result_markdown':'after revoked'},transport=transport)
  except Exception as e:outcome['error']=repr(e)
 thread=threading.Thread(target=worker,name='remote-writer');thread.start()
 assert waiting.wait(10)
 config=project/'docs/mygamestudio/CONFIG.md'; old_text=config.read_text(); new_text=old_text.replace(gh.AUTH,'无(已撤销)')
 assert old_text!=new_text
 rev=peer.write(admin.token,'docs/mygamestudio/CONFIG.md',new_text,expected_sha256=hashlib.sha256(old_text.encode()).hexdigest())
 outcome['revoke_config']= {'decision':rev['decision'],'rule_stage':rev['rule_stage']}
 resume.set();thread.join(10);assert not thread.is_alive()
 svc._locked=real_lock
 fresh=peer.remote_record(inst.token,'append-result',{'identity':'01-task','result_markdown':'fresh should reject'},transport=transport)
 outcome['fresh']={k:fresh[k] for k in ['decision','rule_stage','reason']}
 outcome['comment_count']=len(transport.comments[1])
 outcome['posts']=[x[0:2] for x in transport.calls if x[0]=='POST']
 outcome['id']='remote-config-revoke-inflight'
 outcome['observed_bug']=rev['decision']=='allow' and outcome.get('inflight',{}).get('decision')=='allow' and fresh['decision']=='deny' and len(transport.comments[1])==1
 results.append(outcome)
(r/'extra-probes.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
