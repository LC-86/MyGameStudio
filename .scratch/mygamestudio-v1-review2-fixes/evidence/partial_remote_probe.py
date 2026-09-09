import sys,json,tempfile
from pathlib import Path
sys.dont_write_bytecode=True
r=Path(__file__).parent;c=r/'copy';sys.path.insert(0,str(c/'tests'))
import test_github_backend as gh
import test_runtime_gate as rt
with tempfile.TemporaryDirectory(dir='/tmp',prefix='mgs-partial-remote-') as temp:
 b=Path(temp); project=gh.make_github_project(b/'project'); svc=rt.GateService(b/'runtime')
 resources=['github://github.com/mygamestudio/issue-accept/issues/**']
 svc.init_policy(project,{'producer':resources},{'production':None}); inst=svc.create_instance('producer','T','production',resources)
 svc._write_json('remote.json',{'github':{'api_base':'http://unused.invalid','token_env':'MGS_TEST_UNUSED','cache_dir':str(b/'cache')}})
 fake=gh.FakeTransport();fake.seed_issue('01-task','Existing');fake.fail('PATCH','/issues/1','timeout')
 class Facade:
  def remote_record(self,token,action,payload):return svc.remote_record(token,action,payload,transport=fake)
 def call():
  out=rt.mcp_gate.handle_tools_call(Facade(),'mgs_remote',{'token':inst.token,'action':'append-result','payload':{'identity':'01-task','result_markdown':'same result'}})
  return json.loads(out['content'][0]['text'])
 first=call(); count_first=len(fake.comments[1]);fake._fail=[];second=call()
 data={'id':'R4-partial-remote-result-misreported','first':first,'comments_after_first':count_first,'second_decision':second['decision'],'comments_after_retry':len(fake.comments[1]),'audit':rt.audit_lines(b/'runtime'),'observed_bug':first['decision']=='deny' and count_first==1 and len(fake.comments[1])==2}
 (r/'partial-remote-probe.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in data.items() if k!='audit'},ensure_ascii=False,indent=2))
