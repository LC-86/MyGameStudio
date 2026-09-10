import json, os, pathlib, re, shlex, socket, subprocess
W=pathlib.Path(__file__).parent
F=W/'curl-extra-fixtures';F.mkdir(exist_ok=True)
text=(W/'copy/acceptance/18-complete-package-acceptance/run.sh').read_text()
fn=re.search(r'^curl_direct_denied\(\) \{.*?^\}',text,re.M|re.S).group()
sock=socket.socket();sock.bind(('0.0.0.0',0));port=sock.getsockname()[1]
url=f'http://127.0.0.1:{port}/_test/ping'
q=shlex.quote
base="/usr/bin/curl -q --noproxy '*' --connect-timeout 1 "
cases=[
('true-direct',base+q(url),'OK'),
('userinfo-wrong-host',base+q(f'http://127.0.0.1:{port}@127.0.0.2:{port}/_test/ping'),'MISSING'),
('shell-userinfo-wrong-host','/bin/zsh -lc '+q(base+q(f'http://127.0.0.1:{port}@127.0.0.2:{port}/_test/ping')),'MISSING'),
('true-url-flag',base+'--url '+q(url),'OK'),
('unsupported-env',f'env MGS_R5_URL={q(url)} '+base+q(url),'MISSING'),
('unsupported-xargs',"printf '%s\\n' "+q(url)+" | xargs /usr/bin/curl -q --noproxy '*' --connect-timeout 1",'MISSING'),
('ipv6-other-host',base+q(f'http://[::1]:{port}/_test/ping'),'MISSING'),
]
out=[]
try:
 for name,cmd,expect in cases:
  p=subprocess.run(['/bin/sh','-c',cmd],cwd=F,capture_output=True,text=True,timeout=10)
  item={'type':'commandExecution','command':cmd,'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
  fixture=F/(name+'.jsonl');fixture.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
  a=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+q(str(fixture))],capture_output=True,text=True)
  out.append({'id':name,'command':cmd,'exit':p.returncode,'actual_output':p.stdout+p.stderr,'expected':expect,'anchor':a.stdout.strip(),'observed_bug':a.stdout.strip()!=expect,'fixture':str(fixture)})
finally:sock.close()
(W/'curl-extra-probes-5.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
