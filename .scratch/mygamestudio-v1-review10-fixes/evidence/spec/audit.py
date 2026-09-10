from pathlib import Path
import ast,re,json,os,subprocess
W=Path('/tmp/mgs-review10-j5225ubn/spec'); R=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
env={'PATH':os.environ['PATH'],'LANG':'C','HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
s=(R/'acceptance/18-complete-package-acceptance/run.sh').read_text()
p=subprocess.run(['/usr/bin/curl','-q','--help','all'],env=env,capture_output=True,text=True);helptext=p.stdout;(W/'curl-help-all.txt').write_text(helptext)
p=subprocess.run(['/usr/bin/curl','-q','--manual'],env=env,capture_output=True,text=True);(W/'curl-manual.txt').write_text(p.stdout)
(W/'curl-version.txt').write_text(subprocess.run(['/usr/bin/curl','-q','--version'],env=env,capture_output=True,text=True).stdout)
rows=[]
for group in ['CURL_VALUE_SHORT','CURL_PLAIN_SHORT','CURL_VALUE_LONG','CURL_PLAIN_LONG']:
 pattern=group+r' = set\(("[^"]*"|\(.*?\))\)'
 vals=ast.literal_eval(re.search(pattern,s,re.S).group(1))
 for val in vals:
  flag='-'+val if group.endswith('SHORT') else val
  line=next((l for l in helptext.splitlines() if (re.match(r'^\s+'+re.escape(flag)+r',',l) if group.endswith('SHORT') else re.search(r'(?<!\S)'+re.escape(flag)+r'(?=\s|$)',l))),None)
  p=subprocess.run(['/usr/bin/curl','-q',flag],env=env,cwd=W,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=3)
  observed='value' if 'requires parameter' in p.stderr else ('plain' if 'no URL specified' in p.stderr or (flag=='--version' and p.returncode==0) else 'other')
  expected='value' if '_VALUE_' in group else 'plain'
  rows.append({'table':group,'flag':flag,'help_line':line,'expected_arity':expected,'observed_noarg_arity':observed,'exit':p.returncode,'stderr':p.stderr,'matches':expected==observed})
(W/'arity-audit.json').write_text(json.dumps({'rows':rows,'total':len(rows),'mismatches':[r for r in rows if not r['matches']],'network_calls':0},indent=2))
print(json.dumps({'count':len(rows),'mismatches':[r for r in rows if not r['matches']]}))
