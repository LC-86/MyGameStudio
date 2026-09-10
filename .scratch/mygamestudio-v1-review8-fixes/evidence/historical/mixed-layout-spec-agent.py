#!/usr/bin/env python3
import sys, json, importlib.util, hashlib, argparse
from pathlib import Path
sys.dont_write_bytecode=True
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--guard-each-path',action='store_true');opts=p.parse_args()
ROOT=Path('/tmp/mgs-review8-60iu1bo4/repo')
sys.path.insert(0,str(ROOT/'tests'))
import test_github_backend as gh
import test_runtime_gate as rt
old_path=Path('/tmp/mgs-review8-60iu1bo4/repo/.scratch/mygamestudio-v1-review6-fixes/evidence/mixed-layout/mgs_github_1eef7d8.py')
sp=importlib.util.spec_from_file_location('mgs_github_old',old_path);old=importlib.util.module_from_spec(sp);sp.loader.exec_module(old)
# Share transport exception identity, so the unmodified old implementation handles
# the test suite's FakeTransport exactly as its original module did.
old.TransportError=gh.mgs_github.TransportError
A,B='collision-result-79891','collision-result-80657'
base=opts.out;base.mkdir(parents=True)
project=gh.make_github_project(base/'project');fake=gh._OnceReadFailTransport();fake.seed_issue('01-task','Existing')
svc=rt.GateService(base/'runtime');resources=['github://github.com/mygamestudio/issue-accept/issues/**','src/**']
svc.init_policy(project,{'producer':resources},{'production':None});instance=svc.create_instance('producer','review6-spec','production',resources)
svc._write_json('remote.json',{'github':{'api_base':'http://unused.invalid','token_env':'MGS_TEST_UNUSED','cache_dir':str(base/'cache')}})
class Facade:
    def remote_record(self,token,action,payload):
        return svc.remote_record(token,action,payload,transport=fake)
def call(body):
    return json.loads(rt.mcp_gate.handle_tools_call(Facade(),'mgs_remote',{'token':instance.token,'action':'append-result','payload':{'identity':'01-task','result_markdown':body}})['content'][0]['text'])
current=gh.backend_for(project,fake,base/'cache')
legacy=old.GithubBackend(current.config,fake,base/'cache')
if opts.guard_each_path:
    # Mechanism-control mutation, in-memory only: independently guard each path.
    def clear_each(self,identity,body):
        for path in [self._pending_index_file(identity,body),self._legacy_pending_index_file(identity,body)]:
            if path is None: continue
            try:
                receipt=json.loads(path.read_text())
                if not isinstance(receipt,dict): continue
                if {key:receipt.get(key) for key in ['op','args','repo']} != self._pending_identity(identity,body): continue
                if receipt.get('comment_id') is None or not isinstance(receipt.get('ref'),str) or not receipt['ref']: continue
                path.unlink(missing_ok=True)
            except (OSError,ValueError): pass
    gh.mgs_github.GithubBackend._clear_pending_index=clear_each
def snap():
    return {str(p.relative_to(base/'cache')):json.loads(p.read_text()) for p in sorted((base/'cache'/'pending-index').rglob('*.json'))}
# A real old-version call produces B's legacy receipt without manual relocation.
fake.fail('PATCH','/issues/1','timeout')
first=legacy.append_result('01-task',B);before_upgrade=snap()
# Upgrade: A's first attempt cannot read comments. Its legacy address collides
# with B but identity check prevents adoption, so A publishes and records itself.
fake.read_fail=True
second=call(A);after_a_partial=snap()
# A's index is completed. Its clear must preserve B's healthy legacy receipt.
fake._fail=[]
third=call(A);after_a_complete=snap()
# B cannot read comments and should recover its receipt rather than re-POST.
fake.read_fail=True
fourth=call(B);after_b_retry=snap()
posts=sum(m=='POST' and '/comments' in p for m,p,_ in fake.calls)
b_count=sum(c['body']==f'任务:01-task\n\n{B}' for c in fake.comments[1])
result={'id':'mixed-layout-clear-deletes-foreign-legacy','entry':'old GithubBackend -> upgraded MCP -> GateService -> FakeTransport','old_source':'git show 1eef7d8:plugin/records/mgs_github.py','old_source_sha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),'fake_only':True,'manual_receipt_edits':False,'guard_each_path_control':opts.guard_each_path,'first_old_b':first,'second_new_a':second,'third_a_complete':third,'fourth_b_retry':fourth,'pending_before_upgrade':before_upgrade,'pending_after_a_partial':after_a_partial,'pending_after_a_complete':after_a_complete,'pending_after_b_retry':after_b_retry,'posts':posts,'b_comment_count':b_count,'comments':fake.comments[1],'observed_bug':b_count>1,'expected':'B legacy receipt survives A completion; B retry returns B first comment identity without POST.'}
(base/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:result[k] for k in ['id','posts','b_comment_count','observed_bug','manual_receipt_edits']},indent=2))
