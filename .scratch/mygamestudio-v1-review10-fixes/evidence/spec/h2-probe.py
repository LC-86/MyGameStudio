from pathlib import Path
import subprocess,re,shlex,socket,threading,json,os,hashlib,difflib,time
W=Path('/tmp/mgs-review10-j5225ubn/spec');R=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
env={'PATH':os.environ['PATH'],'LANG':'C','HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
extract=lambda s:re.search(r'^curl_direct_denied\(\) \{.*?^\}',s,re.M|re.S).group()
cur=extract((R/'acceptance/18-complete-package-acceptance/run.sh').read_text());funcs={'current':cur,'restored':cur,'http2_guard':cur.replace(', "--http2",',',')}
for ref in ['e3741c6','3f3031a']:funcs[ref]=extract(subprocess.check_output(['git','show',ref+':acceptance/18-complete-package-acceptance/run.sh'],cwd=R,text=True))
assert funcs['http2_guard']!=cur
(W/'http2_guard.diff').write_text(''.join(difflib.unified_diff(cur.splitlines(True),funcs['http2_guard'].splitlines(True),fromfile='current-extracted',tofile='http2_guard')))
def frame(kind,stream,payload,flags=0):return len(payload).to_bytes(3,'big')+bytes([kind,flags])+stream.to_bytes(4,'big')+payload
rows=[]
for mode in ['refused-stream','goaway-unprocessed','http1-control','closed-http2-control']:
 listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1];hits=[]
 def serve():
  try:
   conn,_=listener.accept();listener.close()
   with conn:
    conn.settimeout(3);data=b''
    while b'\r\n\r\n' not in data:data+=conn.recv(4096)
    head,tail=data.split(b'\r\n\r\n',1)
    lines=head.decode().split('\r\n');method,path,_=lines[0].split(' ',2);hits.append({'method':method,'path':path,'upgrade_h2c':b'Upgrade: h2c' in head,'listener_closed_before_response':True})
    if mode=='http1-control':conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n');return
    conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nConnection: Upgrade\r\nUpgrade: h2c\r\n\r\n'+frame(4,0,b''))
    data=tail
    while len(data)<24:data+=conn.recv(4096)
    hits.append({'http2_client_preface':data[:24]==b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n'})
    if mode=='refused-stream':payload=frame(3,1,(7).to_bytes(4,'big'));hits.append({'sent':'RST_STREAM','stream':1,'error_code':7})
    else:payload=frame(7,0,(0).to_bytes(4,'big')+(0).to_bytes(4,'big'));hits.append({'sent':'GOAWAY','last_stream_id':0,'error_code':0})
    conn.sendall(payload)
    try:
     while conn.recv(4096):pass
    except (TimeoutError,ConnectionResetError):pass
  except Exception as e:hits.append({'server_error':str(e)})
  finally:listener.close()
 t=None
 if mode!='closed-http2-control':listener.listen(1);listener.settimeout(4);t=threading.Thread(target=serve,daemon=True);t.start()
 args=['/usr/bin/curl','-q','--noproxy','*','--connect-timeout','.2','--max-time','2','-sS','--http2',f'http://127.0.0.1:{port}/h2']
 p=subprocess.run(args,cwd=W,env=env,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5)
 if t:t.join(timeout=5)
 else:listener.close()
 expected='OK' if mode=='closed-http2-control' else 'MISSING'
 item={'type':'commandExecution','command':shlex.join(args),'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
 f=W/'fixtures'/('h2-'+mode+'.jsonl');f.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
 row={'id':'h2-'+mode,'expected':expected,'command':shlex.join(args),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'server_hits':hits,'fixture':str(f),'server_thread_closed':t is None or not t.is_alive()}
 for label,fn in funcs.items():
  q=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(f))],env=env,capture_output=True,text=True,timeout=4)
  row[label]={'anchor':q.stdout.strip(),'exit':q.returncode,'stderr':q.stderr}
 row['observed_bug']=row['current']['anchor']!=expected;rows.append(row);print(json.dumps(row),flush=True)
(W/'h2-probe.json').write_text(json.dumps({'rows':rows,'source_sha256':hashlib.sha256(cur.encode()).hexdigest(),'event_provenance':'real loopback curl; h2c upgrade followed by protocol-native RST_STREAM/GOAWAY; no --retry, auth or TLS credentials'},indent=2))
