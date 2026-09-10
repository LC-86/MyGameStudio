import json, sys, re, shlex, subprocess, hashlib, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path('/tmp/mgs-review6-zonhimd1')
COPY = ROOT / 'copy'
sys.path.insert(0, str(COPY/'tests'))
import test_github_backend as gh
import test_runtime_gate as rt
out = []
class OnceFail(gh.FakeTransport):
    read_fail = False
    def request(self, method, path, body=None, *, auth=None):
        if self.read_fail and method == 'GET' and '/comments?' in path:
            self.read_fail = False
            self.calls.append((method, path, body))
            raise gh.mgs_github.TransportError('timeout', 'one read-first timeout')
        return super().request(method, path, body, auth=auth)
def post_count(f):
    return sum(m=='POST' and '/comments' in p for m,p,_ in f.calls)
def setup(base, cache=True):
    proj=gh.make_github_project(base/'project')
    svc=rt.GateService(base/'runtime')
    resources=['github://github.com/mygamestudio/issue-accept/issues/**', 'src/**']
    svc.init_policy(proj, {'producer':resources}, {'production':None})
    inst=svc.create_instance('producer','independent-spec','production',resources)
    channel={'api_base':'http://unused.invalid','token_env':'MGS_TEST_UNUSED'}
    if cache: channel['cache_dir']=str(base/'cache')
    svc._write_json('remote.json', {'github':channel})
    fake=OnceFail(); fake.seed_issue('01-task','Existing')
    class Facade:
        def remote_record(self, token, action, payload):
            return svc.remote_record(token, action, payload, transport=fake)
    def call(result):
        return json.loads(rt.mcp_gate.handle_tools_call(Facade(),'mgs_remote',
            {'token':inst.token,'action':'append-result','payload':{'identity':'01-task','result_markdown':result}})['content'][0]['text'])
    return proj,svc,inst,fake,call
fn=re.search(r'^mcp_deny_anchor\(\) \{.*?^\}',(COPY/'acceptance/18-complete-package-acceptance/run.sh').read_text(),re.M|re.S).group()
def anchor(name, tool, stage, want, action, args, ret):
    path=ROOT/f'spec-independent-{name}.jsonl'
    path.write_text(json.dumps({'method':'item/completed','params':{'item':{'type':'mcpToolCall','tool':tool,'status':'completed','arguments':args,'result':{'content':[{'type':'text','text':json.dumps(ret)}]}}}})+'\n')
    cmd=fn+'\nmcp_deny_anchor '+' '.join(map(shlex.quote,[str(path),tool,stage,want,action]))
    p=subprocess.run(['bash','-c',cmd],text=True,capture_output=True)
    return {'id':name,'arguments':args,'actual_target':ret.get('target'),'wanted_target':want,'ret':ret,'anchor':p.stdout.strip(),'exit':p.returncode,'stderr':p.stderr,'event':str(path)}
with tempfile.TemporaryDirectory(prefix='spec-independent-',dir=ROOT) as temp:
    root=Path(temp)
    proj,svc,inst,fake,call=setup(root/'no-cache',False)
    fake.fail('PATCH','/issues/1','timeout'); first=call('same result')
    fake._fail=[]; fake.read_fail=True; second=call('same result')
    out.append({'id':'no-cache-partial-retry','first':first,'second':second,'comments':len(fake.comments[1]),'posts':post_count(fake),'first_has_warning':'警告' in first.get('result',{}).get('note','')})
    # Actual GateService denies another absolute file outside project. No write occurs.
    wrong='/tmp/alternate-root/tmp/mgs18-evil-link.md'
    ret=svc.write(inst.token,wrong,'X',expected_sha256='absent')
    out.append(anchor('absolute-prefix','mgs_write','path','/tmp/mgs18-evil-link.md','write',{'path':wrong},ret))
    # Both call and result need be compared to intended project root, not just basename suffix.
    limited=svc.create_instance('producer','limited','production',['github://github.com/mygamestudio/issue-accept/issues/04-fog-layer/**'])
    for ident,name in [('01-harbor-timer/comments','identity-comments-suffix'),('01-harbor-timer/comments/comments','identity-double-comments')]:
        ret=svc.remote_record(limited.token,'append-result',{'identity':ident,'result_markdown':'wrong resource'},transport=fake)
        out.append(anchor(name,'mgs_remote','task_grant','01-harbor-timer','append-result',{'action':'append-result','payload':{'identity':ident}},ret))
    # Find deterministic collision in exact 32-bit pending-index key, same repo+identity.
    seen={}; collision=None
    for i in range(300000):
        result=f'collision-result-{i}'
        digest=hashlib.sha256(json.dumps({'op':'append_result','args':{'identity':'01-task','result_markdown':result},'repo':'github.com/mygamestudio/issue-accept'},ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:8]
        if digest in seen:
            collision=(seen[digest],result,digest,i+1);break
        seen[digest]=result
    assert collision
    a,b,digest,count=collision
    proj,svc,inst,fake,call=setup(root/'collision')
    fake.fail('PATCH','/issues/1','timeout'); first=call(a)
    pending_files=list((root/'collision/cache/pending-index').rglob('*.json'))
    fake._fail=[]; fake.read_fail=True; second=call(b)
    out.append({'id':'pending-hash-collision','result_a':a,'result_b':b,'digest':digest,'candidates':count,'first':first,'second':second,'pending_file':str(pending_files[0]),'pending_basename':pending_files[0].name,'pending_data':json.loads(pending_files[0].read_text()),'comments':fake.comments[1],'posts':post_count(fake),'second_body_exists':any(c['body']==f'任务:01-task\n\n{b}' for c in fake.comments[1])})
    # Corrupt JSON: sentinelled pending state should stop duplicate and disclose corrupt.
    proj,svc,inst,fake,call=setup(root/'corrupt-json')
    fake.fail('PATCH','/issues/1','timeout'); first=call('same result')
    pending_file=next((root/'corrupt-json/cache/pending-index').rglob('*.json'))
    pending_file.write_text('{')
    fake._fail=[]; fake.read_fail=True; second=call('same result')
    out.append({'id':'corrupt-json','second':second,'posts':post_count(fake),'comments':len(fake.comments[1])})
    # Valid JSON with mismatched operation content is not validated.
    pending_file.write_text('{}')
    fake.read_fail=True; third=call('same result')
    out.append({'id':'corrupt-shape-object','second':third,'posts':post_count(fake),'comments':len(fake.comments[1])})
(ROOT/'spec-independent-probes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
