import pathlib,re,subprocess,shlex,json,hashlib,sys,tempfile,posixpath
W=pathlib.Path('/tmp/mgs-review10-j5225ubn');R=W/'repo';F=W/'path-boundary-fixtures';F.mkdir(exist_ok=True)
sys.dont_write_bytecode=True;sys.path.insert(0,str(R/'tests'))
import test_github_backend as gh
import test_runtime_gate as rt
text=(R/'acceptance/18-complete-package-acceptance/run.sh').read_text()
fns={name:re.search(rf'^{name}\(\) \{{.*?^\}}',text,re.M|re.S).group() for name in ['mcp_deny_anchor','curl_direct_denied']}
def anchor(f,args):
 p=subprocess.run(['bash','-c',fns[f]+'\n'+f+' '+shlex.join([str(x) for x in args])],capture_output=True,text=True)
 return {'anchor':p.stdout.strip(),'exit':p.returncode,'stderr':p.stderr}
ev=R/'acceptance/18-complete-package-acceptance/evidence'
retained=[]
cases=[('r1','mgs_write',stage,target,'write') for stage,target in [('role_scope','docs/mygamestudio/PROJECT.md'),('occupancy','src/lock-probe.txt'),('task_grant','src/other.txt'),('path','/tmp/mgs18-evil-link.md')]]
cases += [('g1','mgs_remote','task_grant','01-harbor-timer','update'),('g1','mgs_remote','task_grant','02-crane-sprite','append-result')]
cases += [(n,'mgs_write','role_scope|task_grant','docs/mygamestudio/GAME_DESIGN.md','write') for n in ['p1','p2']]
cases += [('r1b','mgs_write','identity','src/stale.txt','write')]
for n,*args in cases:
 p=ev/f'{n}-events.jsonl'; result=anchor('mcp_deny_anchor',[p,*args]); retained.append({'flow':n,'args':args,**result})
retained.append({'flow':'g1','kind':'curl',**anchor('curl_direct_denied',[ev/'g1-events.jsonl'])})
blobs=[]
for n in ['r1','g1','p1','p2','r1b']:
 p=ev/f'{n}-events.jsonl';data=p.read_bytes(); rows=[json.loads(l) for l in data.splitlines()]
 prior=subprocess.check_output(['git','show',f'a3c43ce:acceptance/18-complete-package-acceptance/evidence/{n}-events.jsonl'],cwd='/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
 blobs.append({'flow':n,'lines':len(rows),'sha256':hashlib.sha256(data).hexdigest(),'unchanged_from_batch_base':(pathlib.Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')/'acceptance/18-complete-package-acceptance/evidence'/f'{n}-events.jsonl').read_bytes()==prior, 'task_copy_sanitized':data!=prior})
(W/'acceptance-probes-6.json').write_text(json.dumps({'results':retained,'passed':sum(r['anchor']=='OK' for r in retained),'total':len(retained),'streams':blobs},ensure_ascii=False,indent=2))
out=[]
with tempfile.TemporaryDirectory(prefix='path-boundary-state-',dir=W) as t:
 b=pathlib.Path(t);project=gh.make_github_project(b/'project');svc=rt.GateService(b/'runtime')
 svc.init_policy(project,{'producer':['src/**']},{'production':None});inst=svc.create_instance('producer','path-boundary','production',['src/**'])
 target='/tmp/mgs6-café.md'; candidates=[('nfc-exact',target),('nfd-other','/tmp/mgs6-cafe\u0301.md'),('tab-suffix',target+'\t'),('newline-suffix',target+'\n'),('carriage-suffix',target+'\r'),('nbsp-suffix',target+'\u00a0'),('zero-width-suffix',target+'\u200b'),('leading-space',' '+target)]
 for name,path in candidates:
  ret=svc.write(inst.token,path,'X',expected_sha256='absent');assert ret['decision']=='deny',ret
  event={'method':'item/completed','params':{'item':{'type':'mcpToolCall','tool':'mgs_write','status':'completed','arguments':{'path':path},'result':{'content':[{'type':'text','text':json.dumps(ret)}]}}}}
  fixture=F/(name+'.jsonl');fixture.write_text(json.dumps(event)+'\n')
  want='OK' if posixpath.normpath(path)==posixpath.normpath(target) else 'MISSING'
  out.append({'id':name,'path':path,'expected':want,'real_gate_result':ret,'matches_target':anchor('mcp_deny_anchor',[fixture,'mgs_write','path',target,'write']),'matches_self':anchor('mcp_deny_anchor',[fixture,'mgs_write',ret['rule_stage'],path,'write'])})
(W/'path-boundaries-6.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({'retained':retained,'new_path_cases':[{'id':r['id'],'stage':r['real_gate_result']['rule_stage'],'anchor':r['matches_target']['anchor'],'self':r['matches_self']['anchor'],'expected':r['expected']} for r in out]},ensure_ascii=False,indent=2))
