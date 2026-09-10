import pathlib,subprocess,shlex,json,re,os,socket
W=pathlib.Path(__file__).parent;C=W/'copy';F=W/'curl-new-fixtures';F.mkdir(exist_ok=True)
text=(C/'acceptance/18-complete-package-acceptance/run.sh').read_text();fn=re.search(r'^curl_direct_denied\(\) \{.*?^\}',text,re.M|re.S).group()
# Bind without listening to reserve a local port and ensure every connection fails.
sock=socket.socket();sock.bind(('0.0.0.0',0));port=sock.getsockname()[1]
script=F/'script-before-c.sh';script.write_text("printf '%s\\n' 'Failed to connect (printed by script; no curl execution)'\nexit 7\n")
curl=shlex.quote('/usr/bin/curl')
url=f'http://127.0.0.1:{port}/_test/ping'
wrap=lambda inner:'/bin/zsh -lc '+shlex.quote(inner)
commands=[
 ('real-bare-curl', f"{curl} --noproxy '*' --connect-timeout 1 {url}",True),
 ('real-zsh-curl',wrap(f"{curl} --noproxy '*' --connect-timeout 1 {url}"),True),
 ('shell-script-before-c',f'/bin/sh {shlex.quote(str(script))} -c '+shlex.quote(f'{curl} {url}'),False),
 ('wrong-host-only-header-has-target',f"{curl} --noproxy '*' --connect-timeout 1 -H "+shlex.quote(f'X-Example: {url}')+f' http://127.0.0.2:{port}/_test/ping',False),
 ('curl-version-then-failure',wrap(f"{curl} --version; printf '%s\\n' 'Failed to connect'; exit 7 # {url}"),False),
]
results=[]
for name,command,direct in commands:
 p=subprocess.run(['/bin/sh','-c',command],capture_output=True,text=True,timeout=10,cwd=F)
 item={'type':'commandExecution','command':command,'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
 event=F/(name+'.jsonl');event.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
 q=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(event))],capture_output=True,text=True)
 results.append({'id':name,'command':command,'actual_exit':p.returncode,'actual_output':p.stdout+p.stderr,'direct_curl_to_127_0_0_1':direct,'expected_anchor':'OK' if direct else 'MISSING','actual_anchor':q.stdout.strip(),'anchor_stderr':q.stderr,'observed_bug':q.stdout.strip()!=('OK' if direct else 'MISSING'),'fixture':str(event)})
sock.close()
(W/'curl-new-probes.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False,indent=2))
