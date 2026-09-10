import posixpath, json, pathlib, re, shlex, subprocess, sys, tempfile
W=pathlib.Path(__file__).parent;C=W/'spec';F=W/'spec-extra-path-fixtures';F.mkdir(exist_ok=True)
sys.dont_write_bytecode=True;sys.path.insert(0,str(C/'tests'))
import test_github_backend as gh
import test_runtime_gate as rt
fn=re.search(r'^mcp_deny_anchor\(\) \{.*?^\}',(C/'acceptance/18-complete-package-acceptance/run.sh').read_text(),re.M|re.S).group()
out=[]
with tempfile.TemporaryDirectory(prefix='path-extra-state-',dir=W) as t:
 b=pathlib.Path(t);p=gh.make_github_project(b/'project');svc=rt.GateService(b/'runtime')
 svc.init_policy(p,{'producer':['src/**']},{'production':None})
 inst=svc.create_instance('producer','path-extra','production',['src/**'])
 target='/tmp/mgs18-evil-link.md'
 cases=[('exact',target,'OK'),('trailing-slash',target+'/','OK'),('dot-component','/tmp/./mgs18-evil-link.md','OK'),('duplicate-slash','/tmp//mgs18-evil-link.md','OK'),('repeat-path','/tmp/tmp/mgs18-evil-link.md','MISSING'),('case-variant','/tmp/MGS18-evil-link.md','MISSING'),('space-suffix',target+' ','MISSING'),('space-prefix',' '+target,'MISSING')]
 for name,path,expected in cases:
  ret=svc.write(inst.token,path,'X',expected_sha256='absent')
  assert ret['decision']=='deny',ret
  fixture=F/(name+'.jsonl');fixture.write_text(json.dumps({'method':'item/completed','params':{'item':{'type':'mcpToolCall','tool':'mgs_write','status':'completed','arguments':{'path':path},'result':{'content':[{'type':'text','text':json.dumps(ret)}]}}}})+'\n')
  a=subprocess.run(['bash','-c',fn+'\nmcp_deny_anchor '+' '.join(map(shlex.quote,[str(fixture),'mgs_write','path',target,'write']))],capture_output=True,text=True)
  out.append({'id':name,'path':path,'ret':ret,'expected':expected,'anchor':a.stdout.strip(),'observed_bug':a.stdout.strip()!=expected,'normpath_equal':posixpath.normpath(path)==posixpath.normpath(target),'fixture':str(fixture)})
(W/'spec-extra-path-crosscheck.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
