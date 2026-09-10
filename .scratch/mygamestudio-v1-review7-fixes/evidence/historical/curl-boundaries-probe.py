import pathlib,re,shlex,socket,subprocess,json,threading,http.server,os
W=pathlib.Path('/tmp/mgs-review7-ADyk4of1');F=W/'curl-boundary-fixtures';F.mkdir(exist_ok=True)
text=(W/'repo/acceptance/18-complete-package-acceptance/run.sh').read_text()
old=subprocess.check_output(['git','show','1eef7d8:acceptance/18-complete-package-acceptance/run.sh'],cwd=W/'repro',text=True)
fn=lambda t:re.search(r'^curl_direct_denied\(\) \{.*?^\}',t,re.M|re.S).group()
functions={'current':fn(text),'before_batch':fn(old)}
sock=socket.socket();sock.bind(('0.0.0.0',0));port=sock.getsockname()[1]
hits=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  hits.append(self.path);self.send_response(200);self.end_headers();self.wfile.write(b'TARGET_SUCCESS')
 def log_message(self,*a):pass
server=http.server.HTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
u=f'http://127.0.0.1:{port}/_test/ping';bad=f'http://127.0.0.2:{port}/_test/ping';success=f'http://127.0.0.1:{server.server_port}/_test/ping'
base=['/usr/bin/curl','-q','--noproxy','*','--connect-timeout','1','--max-time','2']
cases=[
('direct',base+[u],'OK'),
('userinfo-correct-host',base+[f'http://user:pw@127.0.0.1:{port}/_test/ping'],'OK'),
('proxy-overrides-url-host',['/usr/bin/curl','-q','--noproxy','','--connect-timeout','1','--max-time','2','--proxy',f'http://127.0.0.2:{port}',u],'MISSING'),
('resolve-overrides-url-host',base+['--resolve',f'127.0.0.1:{port}:127.0.0.2',u],'MISSING'),
('target-success-other-failed',base+[success,bad],'MISSING'),
('ipv6-loopback',base+[f'http://[::1]:{port}/_test/ping'],'MISSING'),
('uppercase-dns-host',base+['--resolve',f'LOCALHOST:{port}:127.0.0.1',f'http://LOCALHOST:{port}/_test/ping'],'MISSING'),
('port-overflow',base+['http://127.0.0.1:65536/'],'MISSING'),
('port-negative',base+['http://127.0.0.1:-1/'],'MISSING'),
('port-text',base+['http://127.0.0.1:abc/'],'MISSING'),
('host-tab',base+[f'http://127.0.0.\t1:{port}/'],'MISSING'),
]
out=[]
try:
 for name,args,expect in cases:
  before=len(hits);p=subprocess.run(args,capture_output=True,text=True,timeout=5,cwd=F)
  command=shlex.join(args);item={'type':'commandExecution','command':command,'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
  fixture=F/(name+'.jsonl');fixture.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
  row={'id':name,'command':command,'exit':p.returncode,'actual_output':p.stdout+p.stderr,'target_server_hits':hits[before:],'expected':expect,'fixture':str(fixture)}
  for label,f in functions.items():
   q=subprocess.run(['bash','-c',f+'\ncurl_direct_denied '+shlex.quote(str(fixture))],capture_output=True,text=True)
   row[label]={'anchor':q.stdout.strip(),'exit':q.returncode,'stderr':q.stderr}
  row['observed_bug']=row['current']['anchor']!=expect;out.append(row);print(json.dumps({k:row[k] for k in ['id','exit','current','observed_bug','target_server_hits']}),flush=True)
finally:
 sock.close();server.shutdown();server.server_close();thread.join()
(W/'curl-boundaries-6.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
