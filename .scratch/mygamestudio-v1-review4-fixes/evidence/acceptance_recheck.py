import hashlib,json,os,pathlib,re,shlex,subprocess,shutil
W=pathlib.Path(__file__).parent
C=W/'copy'
R=pathlib.Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
F=W/'acceptance-fixtures';F.mkdir(exist_ok=True)
ENV={**os.environ,'TMPDIR':'/tmp','PYTHONDONTWRITEBYTECODE':'1'}
script=(C/'acceptance/18-complete-package-acceptance/run.sh').read_text()
scanner=C/'acceptance/16-producer-complete-loop/secret_scan.py'
def fn(name):return re.search(r'^'+name+r'\(\) \{.*?^\}',script,re.M|re.S).group(0)
defs=fn('mcp_deny_anchor')+'\n'+fn('curl_direct_denied')
def bash(body):
 p=subprocess.run(['bash','-c',body],env=ENV,capture_output=True,text=True)
 return {'exit':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
def anchor(path,tool,stage,target,action):return bash(defs+'\nmcp_deny_anchor '+' '.join(map(shlex.quote,map(str,[path,tool,stage,target,action]))))
def curl(path):return bash(defs+'\ncurl_direct_denied '+shlex.quote(str(path)))
def event(path,item):path.write_text(json.dumps({'method':'item/completed','params':{'item':item}},ensure_ascii=False)+'\n');return path
out={}
synthetic=event(F/'agent-allow.jsonl',{'type':'agentMessage','text':'Example only: '+json.dumps({'decision':'allow','rule_stage':'path'})})
out['SP6_original_fixture']=anchor(synthetic,'mgs_write','path','/tmp/mgs18-evil-link.md','write')
real=C/'acceptance/18-complete-package-acceptance/evidence'
anchors=[]
for name,tool,stage,target in [
 ('r1','mgs_write','role_scope','docs/mygamestudio/PROJECT.md'),
 ('r1','mgs_write','occupancy','src/lock-probe.txt'),
 ('r1','mgs_write','task_grant','src/other.txt'),
 ('r1','mgs_write','path','/tmp/mgs18-evil-link.md'),
 ('g1','mgs_remote','task_grant','01-harbor-timer'),
 ('g1','mgs_remote','task_grant','02-crane-sprite'),
 ('p1','mgs_write','role_scope|task_grant','docs/mygamestudio/GAME_DESIGN.md'),
 ('p2','mgs_write','role_scope|task_grant','docs/mygamestudio/GAME_DESIGN.md'),
 ('r1b','mgs_write','identity','src/stale.txt')]:
 anchors.append({'event':name,'tool':tool,'stage':stage,'target':target,**anchor(real/f'{name}-events.jsonl',tool,stage,target,'write' if tool=='mgs_write' else ('update' if target=='01-harbor-timer' else 'append-result'))})
anchors.append({'event':'g1','tool':'curl',**curl(real/'g1-events.jsonl')})
out['retained_anchors']=anchors
command="printf '%s\\n' 'curl http://127.0.0.1:1/_test/ping (example only)' 'Failed to connect (example only)'; exit 7"
executed=subprocess.run(['/bin/zsh','-lc',command],capture_output=True,text=True,env=ENV)
item={'type':'commandExecution','command':"/bin/zsh -lc "+shlex.quote(command),'status':'failed','exitCode':executed.returncode,'aggregatedOutput':executed.stdout+executed.stderr}
curl_example=event(F/'curl-command-example.jsonl',item)
out['curl_example_false_positive']={'actual_command':command,'actual_exit':executed.returncode,'actual_output':executed.stdout+executed.stderr,'curl_was_executed':False,'anchor':curl(curl_example)}

(W/'acceptance-probes-4.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
