from pathlib import Path
import subprocess,re,shlex,socket,threading,http.server,json,os,time,hashlib,difflib
W=Path('/tmp/mgs-review10-j5225ubn/spec');F=W/'fixtures';R=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
env={'PATH':os.environ['PATH'],'LANG':'C','HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
extract=lambda s:re.search(r'^curl_direct_denied\(\) \{.*?^\}',s,re.M|re.S).group()
cur=extract((R/'acceptance/18-complete-package-acceptance/run.sh').read_text())
functions={'current':cur,'restored':cur}
for ref in ['e3741c6','3f3031a']:
 functions[ref]=extract(subprocess.check_output(['git','show',ref+':acceptance/18-complete-package-acceptance/run.sh'],cwd=R,text=True))
# Separate minimal conservative causal guards; they are not product fixes.
functions['upload_guard']=cur.replace('CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzD")','CURL_VALUE_SHORT = set("HmXdoAuwbceErQyYzD")').replace('"--form", "--upload-file", "--cert",','"--form", "--cert",')
functions['protocol_guard']=cur.replace('return urlparse(u).hostname == "127.0.0.1"','return urlparse(u).scheme in ("http", "https") and urlparse(u).hostname == "127.0.0.1"')
functions['upload_glob_guard']=cur.replace('            if tok in CURL_VALUE_LONG:\n                i += 2', '            if tok in CURL_VALUE_LONG:\n                if tok == "--upload-file" and (i + 1 >= len(args) or any(ch in args[i + 1] for ch in "{}[]")):\n                    return None\n                i += 2').replace('                i += 2 if value_at == len(body) - 1 else 1', '                if body[value_at] == "T":\n                    value = args[i + 1] if value_at == len(body) - 1 and i + 1 < len(args) else body[value_at + 1:]\n                    if any(ch in value for ch in "{}[]"):\n                        return None\n                i += 2 if value_at == len(body) - 1 else 1')
for name in ['upload_guard','protocol_guard','upload_glob_guard']:
 assert functions[name]!=cur
 (W/(name+'.diff')).write_text(''.join(difflib.unified_diff(cur.splitlines(True),functions[name].splitlines(True),fromfile='current-extracted',tofile=name)))
rows=[];servers=[];threads=[];res=socket.socket();res.bind(('127.0.0.1',0));closedport=res.getsockname()[1]
base=['/usr/bin/curl','-q','--noproxy','*','--connect-timeout','.2','--max-time','2','-sS']
url=f'http://127.0.0.1:{closedport}/closed'
def execute(name,args,expected,group,hits=None):
 hits=hits if hits is not None else [];n=len(hits)
 p=subprocess.run(args,cwd=W,env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=8)
 item={'type':'commandExecution','command':shlex.join(args),'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
 f=F/(name+'.jsonl');f.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
 row={'id':name,'group':group,'command':shlex.join(args),'expected':expected,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'server_hits':hits[n:],'fixture':str(f)}
 for label,fn in functions.items():
  q=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(f))],env=env,capture_output=True,text=True,timeout=4)
  row[label]={'anchor':q.stdout.strip(),'exit':q.returncode,'stderr':q.stderr}
 row['observed_bug']=row['current']['anchor']!=expected;rows.append(row)
 print(json.dumps({k:row[k] for k in ['id','expected','exit','current','observed_bug','server_hits']}),flush=True)
 return row
hits=[]
class H(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  code=302 if self.path=='/redirect' else 401 if self.path=='/auth' else 200
  hits.append({'method':'GET','path':self.path,'status':code})
  self.send_response(code);self.send_header('Content-Length','0')
  if code==302:self.send_header('Location',url)
  if code==401:self.send_header('WWW-Authenticate','Basic realm="local-probe"')
  self.end_headers()
 def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),H);server.daemon_threads=True
thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start();servers.append(server);threads.append(thread)
target=f'http://127.0.0.1:{server.server_port}'
def once_upload():
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(4)
 port=listener.getsockname()[1];uhits=[]
 def serve():
  try:
   conn,addr=listener.accept();listener.close()
   with conn:
    conn.settimeout(3);data=b''
    while b'\r\n\r\n' not in data:data+=conn.recv(4096)
    head,body=data.split(b'\r\n\r\n',1);lines=head.decode().split('\r\n');method,path,_=lines[0].split(' ',2)
    length=int(next(l.split(':',1)[1].strip() for l in lines if l.lower().startswith('content-length:')))
    while len(body)<length:body+=conn.recv(4096)
    uhits.append({'method':method,'path':path,'status':200,'received_bytes':len(body),'listening_closed_before_response':True})
    conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 15\r\nConnection: close\r\n\r\nUPLOAD_SUCCESS\n')
  except Exception as e:uhits.append({'server_error':str(e)})
  finally:listener.close()
 t=threading.Thread(target=serve,daemon=True);t.start();threads.append(t)
 return port,uhits,t

def ftp_server():
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(4)
 port=listener.getsockname()[1];fhits=[]
 def serve():
  try:
   conn,addr=listener.accept();listener.close()
   with conn:
    conn.settimeout(3);conn.sendall(b'220 loopback FTP probe\r\n');f=conn.makefile('rb')
    while True:
     line=f.readline()
     if not line:break
     verb=line.split(b' ',1)[0].strip().decode();fhits.append({'verb':verb})
     # Arguments to USER/PASS are deliberately neither persisted nor emitted.
     response={
      'USER':b'331 continue\r\n','PASS':b'230 logged in\r\n','PWD':b'257 "/"\r\n',
      'EPSV':f'229 Entering Extended Passive Mode (|||{closedport}|)\r\n'.encode(),
      'PASV':f'227 Entering Passive Mode (127,0,0,1,{closedport//256},{closedport%256})\r\n'.encode(),
      'TYPE':b'200 Type set\r\n','SIZE':b'213 1\r\n','QUIT':b'221 bye\r\n',
     }.get(verb,b'200 OK\r\n')
     conn.sendall(response)
     if verb=='QUIT':break
  except Exception as e:fhits.append({'server_error':str(e)})
  finally:listener.close()
 t=threading.Thread(target=serve,daemon=True);t.start();threads.append(t)
 return port,fhits,t
try:
 cases=[('direct',base+[url],'OK','control'),
 ('aggregate-Zg-single',base+['-Zg',url],'OK','short'),('aggregate-gJ-single',base+['-gJ',url],'OK','short'),
 ('aggregate-Zg-two',base+['-Zg',target+'/ok',url],'MISSING','short'),('aggregate-gJ-two',base+['-gJ',target+'/ok',url],'MISSING','short'),
 ('aggregate-JO-single',base+['-JO',url],'MISSING','short-conservative'),('J-O-single',base+['-J','-O',url],'MISSING','short-conservative'),
 ('glob-query-plain',base+[url+'?a[]=1'],'MISSING','glob-conservative'),('glob-query-off-short',base+['-g',url+'?a[]=1'],'MISSING','glob-conservative'),
 ('glob-query-off-long',base+['--globoff',url+'?a[]=1'],'MISSING','glob-conservative'),
 ('glob-encoded-braces',base+[url+'/%7Ba,b%7D'],'OK','glob'),('glob-encoded-brackets',base+[url+'?a%5B%5D=1'],'OK','glob'),
 ('glob-escaped-braces',base+[url+r'/\{a,b\}'],'MISSING','glob-conservative'),
 ('glob-after-terminator-encoded',base+['--',url+'/%7Ba,b%7D'],'OK','glob'),
 ('glob-after-terminator-query',base+['--',url+'?a[]=1'],'MISSING','glob-conservative'),
 ('glob-retry-redirect',base+['--retry','1','-L',target+'/{redirect,ok}'],'MISSING','composed'),
 ('retry-all-errors-no-retry',base+['--retry-all-errors',url],'MISSING','retry-conservative'),
 ('retry-connrefused-no-retry',base+['--retry-connrefused',url],'MISSING','retry-conservative'),
 ('retry-delay-no-retry',base+['--retry-delay','0',url],'MISSING','retry-conservative'),
 ('retry-max-time-no-retry',base+['--retry-max-time','1',url],'MISSING','retry-conservative'),
 ('auth-challenge-no-credentials',base+[target+'/auth'],'MISSING','auth-control'),
 ('http2-plain',base+['--http2',target+'/ok'],'MISSING','http-control'),
 ('encoded-literal-success',base+[target+'/%7Ba,b%7D'],'MISSING','glob-control')]
 for name,args,expected,group in cases:execute(name,args,expected,group,hits)
 for filename in ['a.txt','b.txt','item1.txt','item2.txt']:(W/filename).write_text('upload probe body\n')
 for name,flags in [
  ('upload-glob-short',['-T','{a.txt,b.txt}']),
  ('upload-glob-long',['--upload-file','{a.txt,b.txt}']),
  ('upload-glob-short-attached',['-T{a.txt,b.txt}']),
  ('upload-glob-short-aggregate',['-sST{a.txt,b.txt}']),
  ('upload-glob-range',['-T','item[1-2].txt']),
  ('upload-glob-after-terminator',['-T','{a.txt,b.txt}','--']),
  ('upload-glob-with-g',['-g','-T','{a.txt,b.txt}']),
  ('upload-glob-long-equals',['--upload-file={a.txt,b.txt}'])]:
  port,uhits,t=once_upload();execute(name,base+flags+[f'http://127.0.0.1:{port}/upload/'],'MISSING','upload-glob',uhits);t.join(timeout=5)
 execute('upload-single-closed',base+['-T','a.txt',url],'OK','upload-control')
 execute('upload-long-single-closed',base+['--upload-file','a.txt',url],'OK','upload-control')
 for name,flags in [('ftp-passive-default',[]),('ftp-passive-parallel',['-Z'])]:
  port,fhits,t=ftp_server();execute(name,base+flags+[f'ftp://127.0.0.1:{port}/file'],'MISSING','protocol',fhits);t.join(timeout=5)
 execute('ftp-control-port-closed',base+[f'ftp://127.0.0.1:{closedport}/file'],'MISSING','protocol-control')
finally:
 res.close()
 for s in servers:s.shutdown();s.server_close()
 for t in threads:t.join(timeout=5)
(W/'new-curl-probes.json').write_text(json.dumps({'rows':rows,'all_task_server_threads_closed':all(not t.is_alive() for t in threads),'source_sha256':hashlib.sha256(cur.encode()).hexdigest(),'event_provenance':'real loopback /usr/bin/curl command, exit, stdout and stderr wrapped as item/completed; not a product/model run; FTP server records only command verbs','guards':'conservative causal controls, not product changes'},indent=2))
print(json.dumps({'total':len(rows),'bugs':[r['id'] for r in rows if r['observed_bug']],'all_task_servers_closed':all(not t.is_alive() for t in threads)}))
