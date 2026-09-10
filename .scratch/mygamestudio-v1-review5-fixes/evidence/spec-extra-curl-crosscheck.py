import json, re, shlex, socket, subprocess
from pathlib import Path
W=Path('/tmp/mygamestudio-review-5-niculnow')
fn=re.search(r'^curl_direct_denied\(\) \{.*?^\}',(W/'spec/acceptance/18-complete-package-acceptance/run.sh').read_text(),re.M|re.S).group()
sock=socket.socket(); sock.bind(('0.0.0.0',0)); port=sock.getsockname()[1]
url=f'http://127.0.0.1:{port}@127.0.0.2:{port}/_test/ping'
cmd='/usr/bin/curl -q --noproxy '+shlex.quote('*')+' --connect-timeout 1 '+shlex.quote(url)
try:
 p=subprocess.run(['/bin/sh','-c',cmd],text=True,capture_output=True,timeout=5)
 item={'type':'commandExecution','command':cmd,'status':'failed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
 fixture=W/'spec-extra-curl-crosscheck.jsonl';fixture.write_text(json.dumps({'params':{'item':item}})+'\n')
 check=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(fixture))],capture_output=True,text=True)
 out={'command':cmd,'exit':p.returncode,'actual_output':item['aggregatedOutput'],'anchor':check.stdout.strip(),'observed_bug':check.stdout.strip()=='OK' and 'Failed to connect to 127.0.0.2' in item['aggregatedOutput']}
 (W/'spec-extra-curl-crosscheck.json').write_text(json.dumps(out,indent=2))
 print(json.dumps(out,indent=2))
finally:sock.close()
