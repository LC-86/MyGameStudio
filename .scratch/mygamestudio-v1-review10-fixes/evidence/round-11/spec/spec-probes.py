from pathlib import Path
import subprocess,re,shlex,socket,threading,json,hashlib,difflib
W=Path('/tmp/mgs-review11-kgohlovv/spec');R=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
for d in ['fixtures','home','tmp','outputs']:(W/d).mkdir(exist_ok=True)
env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin','LANG':'C','HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'ZDOTDIR':str(W/'home'),'TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
extract=lambda s:re.search(r'^curl_direct_denied\(\) \{.*?^\}',s,re.M|re.S).group()
cur=extract((R/'acceptance/18-complete-package-acceptance/run.sh').read_text())
old=extract(subprocess.check_output(['git','show','66b8506:acceptance/18-complete-package-acceptance/run.sh'],cwd=R,text=True))
functions={'current':cur,'before':old,'restored':cur}
# Fresh causal guard derived from current text: deliberately broad upload rejection.
broad=cur.replace('CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzD")','CURL_VALUE_SHORT = set("HmXdoAuwbceErQyYzD")').replace('"--form", "--upload-file", "--cert",','"--form", "--cert",')
assert broad != cur
functions['broad_upload_guard']=broad
(W/'broad-upload-guard.diff').write_text(''.join(difflib.unified_diff(cur.splitlines(True),broad.splitlines(True),fromfile='current',tofile='broad')))
res=socket.socket();res.bind(('127.0.0.1',0));closed=res.getsockname()[1]
base=['/usr/bin/curl','-q','--noproxy','*','--connect-timeout','.25','--max-time','2','-sS']
closed_url=f'http://127.0.0.1:{closed}/closed'
rows=[];threads=[]
for f in ['a.txt','b.txt','item1.txt','item2.txt','item3.txt','{a,b}.txt',r'\{a,b\}.txt']:(W/f).write_text('independent-upload-body\n')
def server_once():
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(.6)
 port=listener.getsockname()[1];hits=[]
 def worker():
  try:
   conn,_=listener.accept();listener.close()
   with conn:
    conn.settimeout(2.5);f=conn.makefile('rb');line=f.readline().decode().rstrip();method,path,_=line.split(' ',2);headers={}
    while True:
     h=f.readline()
     if h==b'\r\n':break
     if not h:raise RuntimeError('closed in headers')
     k,v=h.decode().split(':',1);headers[k.lower()]=v.strip()
    if headers.get('expect','').lower()=='100-continue':conn.sendall(b'HTTP/1.1 100 Continue\r\n\r\n')
    body=b''
    if headers.get('transfer-encoding','').lower()=='chunked':
     while True:
      size=int(f.readline().strip(),16)
      if size==0:
       f.readline();break
      body+=f.read(size);f.read(2)
    else:body=f.read(int(headers.get('content-length','0')))
    hits.append({'method':method,'path':path,'status':200,'bytes':len(body),'body_sha256':hashlib.sha256(body).hexdigest(),'listener_closed_before_response':True})
    conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 8\r\nConnection: close\r\n\r\nSUCCESS\n')
  except TimeoutError:pass
  except Exception as e:hits.append({'server_error':str(e)})
  finally:listener.close()
 t=threading.Thread(target=worker,daemon=True);t.start();threads.append(t)
 return f'http://127.0.0.1:{port}/upload/',hits,t

def execute(name,flags,expected='MISSING',live=True,url_suffix='',url_first=False,stdin=''):
 if live:url,hits,t=server_once()
 else:url,hits,t=closed_url,[],None
 url+=url_suffix
 args=base+([url]+flags if url_first else flags+[url])
 # No shell evaluates argv; every target is a numeric IPv4 loopback literal.
 p=subprocess.run(args,cwd=W,env=env,input=stdin,capture_output=True,text=True,timeout=5)
 if t:t.join(3)
 item={'type':'commandExecution','command':shlex.join(args),'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
 f=W/'fixtures'/(name+'.jsonl');f.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
 row={'id':name,'command':shlex.join(args),'expected':expected,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'server_hits':hits,'fixture':str(f),'stdin_bytes':len(stdin.encode())}
 for label,fn in functions.items():
  q=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(f))],cwd=W,env=env,text=True,capture_output=True,timeout=4)
  row[label]={'anchor':q.stdout.strip(),'exit':q.returncode,'stderr':q.stderr}
 row['observed_bug']=row['current']['anchor']!=expected
 rows.append(row)
 print(json.dumps({k:row[k] for k in ['id','expected','exit','server_hits','current','observed_bug']}),flush=True)
try:
 execute('direct-closed',[],expected='OK',live=False)
 for name,flags in [('output-short',['-o','outputs/{a,b}.txt']),('output-long',['--output','outputs/item[1-2].txt']),('data-short',['-d','field={a,b}[1-2]']),('data-long',['--data','field={a,b}[1-2]']),('data-raw',['--data-raw','@{a,b}[1-2]']),('data-binary',['--data-binary','{a,b}[1-2]'])]:
  execute(name+'-success',flags)
  execute(name+'-closed',flags,expected='OK',live=False)
 execute('form-short-glob-literal',['-F','file=@{a,b}.txt'])
 execute('form-long-glob-literal',['--form','file=@{a,b}.txt'])
 execute('form-long-two-files-one-post',['--form','file=@a.txt,b.txt'])
 execute('form-long-data-glob',['--form','field={a,b}[1-2]'])
 execute('form-long-two-files-closed',['--form','file=@a.txt,b.txt'],expected='OK',live=False)
 execute('upload-stdin-dash',['-T','-'],stdin='loopback stdin body\n')
 execute('upload-stdin-dot',['-T','.'],stdin='loopback stdin body\n')
 execute('upload-empty-value',['-T',''])
 execute('upload-short-missing-value',['-T'],url_first=True)
 execute('upload-long-missing-value',['--upload-file'],url_first=True)
 execute('upload-aggregate-missing-value',['-sST'],url_first=True)
 execute('upload-stdin-closed',['-T','-'],expected='OK',live=False,stdin='loopback stdin body\n')
 execute('upload-dot-closed',['-T','.'],expected='OK',live=False,stdin='loopback stdin body\n')
 for name,flags in [('upload-step-braces',['-T','{1..10..2}']),('upload-step-range',['-T','item[1-3:2].txt']),('upload-nested-braces',['-T','{{a,b},c}.txt']),('upload-escaped-braces',['-T',r'\{a,b\}.txt']),('upload-singleton-glob',['-T','{a}.txt']),('upload-unmatched-open',['-T','a[.txt']),('upload-unmatched-close',['-T','a].txt']),('upload-long-aggregate',['-sSTa.txt']),('upload-duplicate-flags',['-T','a.txt','-T','b.txt']),('upload-disabled-literal-glob',['-g','-T','{a,b}.txt'])]:execute(name,flags)
 execute('upload-disabled-literal-glob-closed',['-g','-T','{a,b}.txt'],live=False)
 execute('upload-long-single-closed',['--upload-file','a.txt'],expected='OK',live=False)
 execute('upload-short-single-closed',['-T','a.txt'],expected='OK',live=False)
 execute('upload-aggregate-single-closed',['-sSTa.txt'],expected='OK',live=False)
 for name,flags,suffix in [('upload-plus-url-glob',['-T','{a.txt,b.txt}'],'{one,two}'),('upload-plus-retry',['-T','{a.txt,b.txt}','--retry','1'],''),('upload-plus-redirect',['-T','{a.txt,b.txt}','-L'],''),('upload-all-three',['-T','{a.txt,b.txt}','--retry','1','-L'],'{one,two}')]:execute(name,flags,url_suffix=suffix)
finally:
 res.close()
 for t in threads:t.join(3)
summary={'rows':rows,'total':len(rows),'bugs':[r['id'] for r in rows if r['observed_bug']],'all_task_threads_closed':all(not t.is_alive() for t in threads),'source_sha256':hashlib.sha256(cur.encode()).hexdigest(),'network_boundary':'clean allowlisted environment; all HTTP URL arguments use numeric 127.0.0.1; argv run without shell; curl -q --noproxy *; only loopback servers; no credentials used','causal_guard':'fresh broad upload rejection for conservative-cost control, not a product fix'}
(W/'spec-probes.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:summary[k] for k in ['total','bugs','all_task_threads_closed']}))
