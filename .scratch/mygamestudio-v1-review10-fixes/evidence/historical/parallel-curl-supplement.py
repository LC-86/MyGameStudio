from pathlib import Path
import json,subprocess,shlex,socket,threading,http.server,os,re
W=Path('/tmp/mgs-review10-j5225ubn');F=W/'parallel-fixtures';F.mkdir(exist_ok=True)
s=(W/'repo/acceptance/18-complete-package-acceptance/run.sh').read_text();pat=r'^curl_direct_denied\(\) \{.*?^\}';cur=re.search(pat,s,re.M|re.S).group()
guard=cur.replace('CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzZDJg")','CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzD")').replace('CURL_PLAIN_SHORT = set("sSkvIifnN46q")','CURL_PLAIN_SHORT = set("sSkvIifnN46qgJZ")')
functions={'current':cur,'short_arity_guard':guard,'restored':cur}
for ref in ['a3c43ce','3e6ae30','3f3031a']:
 text=subprocess.check_output(['git','show',ref+':acceptance/18-complete-package-acceptance/run.sh'],cwd='/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio',text=True);functions[ref]=re.search(pat,text,re.M|re.S).group()
env={'PATH':os.environ['PATH'],'LANG':'C','HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];hits=[]
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  hits.append({'path':self.path,'status':200,'host':self.headers.get('Host')});body=b'PARALLEL_SUCCESS\n';self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
base=['/usr/bin/curl','-q','--noproxy','*','--connect-timeout','.2','--max-time','2','-sS'];url=f'http://127.0.0.1:{port}/closed';target=f'http://127.0.0.1:{server.server_port}/ok'
out=[]
try:
 for name,args,expected in [('silent-Z-two-urls',base+['-Z',target,url],'MISSING'),('silent-Z-one-url',base+['-Z',url],'OK'),('silent-direct',base+[url],'OK')]:
  n=len(hits);p=subprocess.run(args,env=env,cwd=F,capture_output=True,text=True,timeout=5);item={'type':'commandExecution','command':shlex.join(args),'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr};f=F/(name+'.jsonl');f.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
  r={'id':name,'command':shlex.join(args),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'target_server_hits':hits[n:],'fixture':str(f),'expected':expected}
  for label,fn in functions.items():
   q=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(f))],env=env,capture_output=True,text=True);r[label]={'anchor':q.stdout.strip(),'exit':q.returncode,'stderr':q.stderr}
  r['observed_bug']=r['current']['anchor']!=expected;out.append(r)
finally:sock.close();server.shutdown();server.server_close();thread.join()
(W/'parallel-curl-supplement.json').write_text(json.dumps({'rows':out,'all_task_servers_closed':True},ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
