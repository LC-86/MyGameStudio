from pathlib import Path
import subprocess,re,json,os,shlex,hashlib
W=Path('/tmp/mgs-review10-j5225ubn/spec');R=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio');F=W/'archive-fixtures';F.mkdir(exist_ok=True)
env={'PATH':os.environ['PATH'],'LANG':'C','HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
extract=lambda s:re.search(r'^curl_direct_denied\(\) \{.*?^\}',s,re.M|re.S).group()
functions={'current':extract((R/'acceptance/18-complete-package-acceptance/run.sh').read_text()),'e3741c6':extract(subprocess.check_output(['git','show','e3741c6:acceptance/18-complete-package-acceptance/run.sh'],cwd=R,text=True))}
rows=[]
for source in ['new-probes/new-probes-9.json','parallel-supplement/parallel-curl-supplement.json']:
 sourcefile=R/'.scratch/mygamestudio-v1-review9-fixes/evidence'/source
 data=json.loads(sourcefile.read_text());raw=data.get('rows',[]) if isinstance(data,dict) else data
 for row in raw:
  item={'type':'commandExecution','command':row['command'],'status':'failed' if row['exit'] else 'completed','exitCode':row['exit'],'aggregatedOutput':row['stdout']+row['stderr']}
  f=F/(row['id']+'.jsonl');f.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
  expected='MISSING' if row['id']=='retry-closed-control' else row['expected']
  r={'id':row['id'],'source':str(sourcefile),'source_sha256':hashlib.sha256(sourcefile.read_bytes()).hexdigest(),'original_expected':row['expected'],'expected':expected,'classification':'accepted-output-origin-limit' if row['id']=='full-diagnostic-body' else 'disclosed-conservative-flip' if row['id']=='retry-closed-control' else 'required','fixture':str(f)}
  for label,fn in functions.items():
   p=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(f))],env=env,capture_output=True,text=True)
   r[label]={'anchor':p.stdout.strip(),'exit':p.returncode,'stderr':p.stderr}
  r['observed_bug']=r['current']['anchor']!=expected;rows.append(r)
(W/'original-replay.json').write_text(json.dumps({'rows':rows,'total':len(rows),'raw_current_mismatches':[r['id'] for r in rows if r['observed_bug']],'source':'archive command, exit and stdout/stderr replayed only; no historical commands executed and no new network curl process'},indent=2))
print(json.dumps({'count':len(rows),'mismatches':[r['id'] for r in rows if r['observed_bug']]}))
