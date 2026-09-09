from pathlib import Path
import subprocess,json,os,sys
r=Path(__file__).parent;c=r/'copy'
env=dict(os.environ,TMPDIR='/tmp',PYTHONDONTWRITEBYTECODE='1')
for key in ['GH_TOKEN','GITHUB_TOKEN','GH_ENTERPRISE_TOKEN','GITHUB_ENTERPRISE_TOKEN']:
 env.pop(key,None)
cases=[
 ('A-S1','plugin/records/mgs_github.py','if draft_repo != current_repo:', 'if False:', 'test_publish_drafts_refuses_cross_repo_draft'),
 ('A-R2','plugin/runtime/mgs_runtime.py','entry = policy.get("purposes", {}).get(purpose)','entry = policy.get("purposes", {}).get(purpose, {"restrict": None})','review_fix_section'),
 ('B-handover','plugin/records/mgs_records.py','payload = mgs_github.handover_baseline_check(', 'payload = mgs_github.handover_baselinecheck_item(', 'test_cli_github_handover_end_to_end')
]
results=[]
for cid,rel,old,new,test in cases:
 p=c/rel; original=p.read_text(); assert original.count(old)==1
 record={'id':cid,'mutation':{'file':rel,'before':old,'after':new},'runs':[]}
 for phase in ['green-before','red-mutated','green-restored']:
  p.write_text(original.replace(old,new) if phase=='red-mutated' else original)
  proc=subprocess.run([sys.executable,str(r/'probe_runner.py'),test],cwd=c,env=env,text=True,capture_output=True)
  log=r/f'{cid}-{phase}.log';log.write_text(proc.stdout+proc.stderr)
  record['runs'].append({'phase':phase,'returncode':proc.returncode,'output':proc.stdout,'stderr':proc.stderr,'log':str(log)})
 p.write_text(original);results.append(record)
(r/'mutations.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps([{ 'id':x['id'],'runs':[{k:y[k] for k in ['phase','returncode','log']} for y in x['runs']]} for x in results],indent=2))
