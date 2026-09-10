from pathlib import Path
import re,subprocess,shlex,socket,threading,http.server,json,os,time,hashlib
W=Path('/tmp/mgs-review9-3hpb5uhl');F=W/'curl-adversarial-fixtures';F.mkdir(exist_ok=True)
text=(W/'repo/acceptance/18-complete-package-acceptance/run.sh').read_text()
fn=lambda s:re.search(r'^curl_direct_denied\(\) \{.*?^\}',s,re.M|re.S).group()
cur=fn(text)
old=fn(subprocess.check_output(['git','show','a3c43ce:acceptance/18-complete-package-acceptance/run.sh'],cwd=W/'repro',text=True))
# All transport addresses, listeners and proxy endpoints stay on loopback.
reservation=socket.socket();reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
hits=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  hit={'path':self.path,'host':self.headers.get('Host'),'status':302 if self.path=='/redirect' else 200};hits.append(hit)
  self.send_response(hit['status'])
  if self.path=='/redirect':self.send_header('Location',f'http://127.0.0.2:{port}/unreachable');self.end_headers();return
  body=b'TARGET_SUCCESS\n'
  if self.path=='/slow':
   self.send_header('Content-Length',str(len(body)+10));self.end_headers();self.wfile.write(body);self.wfile.flush();time.sleep(1.3);return
  self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
u=f'http://127.0.0.1:{port}/unreachable';bad=f'http://127.0.0.2:{port}/unreachable';success=f'http://127.0.0.1:{server.server_port}'
proxycfg=F/'proxy.curlrc';proxycfg.write_text(f'proxy = "http://127.0.0.2:{port}"\nnoproxy = ""\n')
# An isolated curl home tests defaults without reading the user's own configuration.
ch=F/'curl-home';ch.mkdir(exist_ok=True);(ch/'.curlrc').write_bytes(proxycfg.read_bytes())
env={k:v for k,v in os.environ.items() if not k.lower().endswith('_proxy') and k not in ('CURL_HOME','XDG_CONFIG_HOME')}
env.update(CURL_HOME=str(ch),PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(W/'tmp'))
base=['/usr/bin/curl','-q','--noproxy','*','--connect-timeout','1','--max-time','2']
cases=[
 ('direct',base+[u],'OK','control',{}),
 ('correct-userinfo',base+[u.replace('http://','http://user:pw@')],'OK','control',{}),
 ('long-proxy',base+['--noproxy','','--proxy',f'http://127.0.0.2:{port}',u],'MISSING','target-options',{}),
 ('short-proxy',base+['--noproxy','','-x',f'http://127.0.0.2:{port}',u],'MISSING','target-options',{}),
 ('short-config',base+['-K',str(proxycfg),u],'MISSING','target-options',{}),
 ('connect-to',base+['--connect-to',f'127.0.0.1:{port}:127.0.0.2:{port}',u],'MISSING','target-options',{}),
 ('default-config',['/usr/bin/curl','--connect-timeout','1','--max-time','2',u],'MISSING','ambient-config',{}),
 ('environment-proxy',['/usr/bin/curl','-q','--connect-timeout','1','--max-time','2',u],'MISSING','ambient-config',{'http_proxy':f'http://127.0.0.2:{port}','no_proxy':''}),
 ('redirect-short',base+['-L',success+'/redirect'],'MISSING','redirect',{}),
 ('redirect-long',base+['--location',success+'/redirect'],'MISSING','redirect',{}),
 ('redirect-not-followed',base+[success+'/redirect'],'MISSING','control',{}),
 ('attached-short-value-hides-first-url',base+['-m2',success+'/ok',u],'MISSING','url-consumption',{}),
 ('separate-short-value-two-urls',base+['-m','2',success+'/ok',u],'MISSING','control',{}),
 ('successful-target',base+[success+'/ok'],'MISSING','control',{}),
 ('target-200-body-then-timeout',base+['--max-time','0.3',success+'/slow'],'MISSING','failure-stage',{}),
 ('two-shell-layers',['/bin/sh','-c',shlex.join(['/bin/sh','-c',shlex.join(base+[u])])],'OK','control',{}),
 ('three-shell-layers',['/bin/sh','-c',shlex.join(['/bin/sh','-c',shlex.join(['/bin/sh','-c',shlex.join(base+[u])])])],'MISSING','documented-shell-limit',{})
]
guards={
 'reject-short-xK':cur.replace('CURL_VALUE_SHORT = set("HmXdoAuwbceEKrTQyYzZDxUJg")','CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzZDUJg")'),
 'reject-location':cur.replace('CURL_PLAIN_SHORT = set("sSLkvIifnN46q")','CURL_PLAIN_SHORT = set("sSkvIifnN46q")').replace('"--location", ',''),
 'correct-short-consumption':cur.replace('''            if any(ch in CURL_VALUE_SHORT for ch in body):
                i += 2
                continue
''','''            value_at = next((j for j, ch in enumerate(body) if ch in CURL_VALUE_SHORT), None)
            if value_at is not None:
                i += 1 if value_at < len(body) - 1 else 2
                continue
''')
}
functions={'current':cur,'before_batch':old,**guards}
rows=[]
try:
 for name,args,expect,group,extra in cases:
  before=len(hits);p=subprocess.run(args,cwd=F,env=dict(env,**extra),capture_output=True,text=True,timeout=9)
  fixture=F/(name+'.jsonl');item={'type':'commandExecution','command':shlex.join(args),'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
  fixture.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
  row={'id':name,'group':group,'command':shlex.join(args),'exit':p.returncode,'actual_output':p.stdout+p.stderr,'expected':expect,'target_server_hits':hits[before:],'fixture':str(fixture),'loopback_env_overrides':extra}
  for label,f in functions.items():
   a=subprocess.run(['bash','-c',f+'\ncurl_direct_denied '+shlex.quote(str(fixture))],env=env,capture_output=True,text=True)
   row[label]={'anchor':a.stdout.strip(),'exit':a.returncode,'stderr':a.stderr}
  row['observed_bug']=row['current']['anchor']!=expect;rows.append(row)
  print(json.dumps({k:row[k] for k in ['id','group','exit','expected','current','observed_bug','target_server_hits']}),flush=True)
finally:reservation.close();server.shutdown();server.server_close();thread.join()
(W/'curl-adversarial-7.json').write_text(json.dumps({'curl_version':subprocess.check_output(['/usr/bin/curl','-q','--version'],text=True).splitlines()[0],'rows':rows,'source_sha256':hashlib.sha256(cur.encode()).hexdigest(),'all_task_servers_closed':True,'synthetic_events_from_actual_loopback_processes':True},ensure_ascii=False,indent=2))
