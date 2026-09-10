from pathlib import Path
import subprocess, re, shlex, socket, threading, http.server, json, os, time, hashlib, difflib
W=Path('/tmp/mgs-review9-3hpb5uhl'); F=W/'new-fixtures-9'; F.mkdir(exist_ok=True)
run=W/'repo/acceptance/18-complete-package-acceptance/run.sh'
extract=lambda s:re.search(r'^curl_direct_denied\(\) \{.*?^\}',s,re.M|re.S).group()
cur=extract(run.read_text())
old=extract(subprocess.check_output(['git','show','3f3031a:acceptance/18-complete-package-acceptance/run.sh'],cwd=W/'repro',text=True))
guard_short=cur.replace('CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzZDJg")','CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzZD")').replace('CURL_PLAIN_SHORT = set("sSkvIifnN46q")','CURL_PLAIN_SHORT = set("sSkvIifnN46qgJZ")')
guard_retry=cur.replace('"--retry", ','')
# Deliberately conservative causal control, not a proposed full URL parser.
guard_glob=cur.replace('        urls.append(tok)','        if any(ch in tok for ch in "{}[]"):\n            return None\n        urls.append(tok)').replace('            urls.extend(args[i + 1:])','            if any(any(ch in arg for ch in "{}[]") for arg in args[i + 1:]):\n                return None\n            urls.extend(args[i + 1:])')
for name,v in [('short',guard_short),('retry',guard_retry),('glob',guard_glob)]:
    assert v!=cur
    (W/f'new-{name}-guard.diff').write_text(''.join(difflib.unified_diff(cur.splitlines(True),v.splitlines(True),fromfile='current-extracted',tofile=name)))
functions={'current':cur,'before_batch':old,'short_guard':guard_short,'retry_guard':guard_retry,'glob_guard':guard_glob,'restored':cur}
env={'PATH':os.environ['PATH'],'LANG':'C','HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
reservation=socket.socket();reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
hits=[]
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code=302 if self.path=='/redirect' else 200
        hits.append({'path':self.path,'status':code,'host':self.headers.get('Host')})
        self.send_response(code)
        if code==302:
            self.send_header('Location',f'http://127.0.0.1:{port}/closed');self.end_headers();return
        body=(b'curl: (7) Failed to connect to 127.0.0.1 port 1 after 0 ms: Couldn\'t connect to server\n' if self.path=='/full-diagnostic-body' else b'TARGET_SUCCESS\n')
        slow=self.path=='/full-diagnostic-body'
        self.send_header('Content-Length',str(len(body)+(10 if slow else 0)));self.end_headers();self.wfile.write(body);self.wfile.flush()
        if slow:time.sleep(.7)
    def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True);thread.start()
url=f'http://127.0.0.1:{port}/closed';target=f'http://127.0.0.1:{server.server_port}'
base=['/usr/bin/curl','-q','--noproxy','*','--connect-timeout','.2','--max-time','2']
cases=[
 ('direct',base+[url],'OK','control'),
 ('no-value-g-two-urls',base+['-g',target+'/ok',url],'MISSING','short-arity'),
 ('no-value-J-two-urls',base+['-J',target+'/ok',url],'MISSING','short-arity'),
 ('no-value-Z-two-urls',base+['-Z',target+'/ok',url],'MISSING','short-arity'),
 ('no-value-g-single-url',base+['-g',url],'OK','short-arity'),
 ('two-urls-plain',base+[target+'/ok',url],'MISSING','control'),
 ('mixed-prefix-sLm2',base+['-sLm2',target+'/redirect'],'MISSING','control'),
 ('single-dash',base+['-',url],'MISSING','control'),
 ('terminator-attached-option',base+['--','-sSm2',url],'MISSING','control'),
 ('lowercase-lm2',base+['-lm2',url],'MISSING','control'),
 ('uppercase-M2',base+['-M2',url],'MISSING','control'),
 ('legitimate-aggregate',base+['-sSm2',url],'OK','control'),
 ('url-glob-two-ports',base+[f'http://127.0.0.1:{{{server.server_port},{port}}}/ok'],'MISSING','url-glob'),
 ('url-glob-after-terminator',base+['--',f'http://127.0.0.1:{{{server.server_port},{port}}}/ok'],'MISSING','url-glob'),
 ('url-glob-disabled-long',base+['--globoff',f'http://127.0.0.1:{{{server.server_port},{port}}}/ok'],'MISSING','control'),
 ('full-diagnostic-body',base+['--max-time','.2',target+'/full-diagnostic-body'],'MISSING','accepted-output-origin-limit'),
]
rows=[]
def execute(name,args,expected,group,hit_source):
    before=len(hit_source);p=subprocess.run(args,cwd=F,env=env,capture_output=True,text=True,timeout=12)
    item={'type':'commandExecution','command':shlex.join(args),'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
    fixture=F/(name+'.jsonl');fixture.write_text(json.dumps({'method':'item/completed','params':{'item':item}})+'\n')
    row={'id':name,'group':group,'expected':expected,'command':shlex.join(args),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'target_server_hits':hit_source[before:],'fixture':str(fixture)}
    for label,fn in functions.items():
        q=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(fixture))],env=env,capture_output=True,text=True)
        row[label]={'anchor':q.stdout.strip(),'exit':q.returncode,'stderr':q.stderr}
    row['observed_bug']=row['current']['anchor']!=expected;rows.append(row)
    print(json.dumps({k:row[k] for k in ['id','group','expected','exit','current','short_guard','retry_guard','glob_guard','observed_bug','target_server_hits']}),flush=True)
retry_servers=[]
try:
    for name,args,expected,group in cases:execute(name,args,expected,group,hits)
    for mode in ['stop-after-503','503-then-200']:
        rhits=[];stop_threads=[]
        class RetryHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                code=503 if not rhits else 200
                rhits.append({'path':self.path,'status':code,'host':self.headers.get('Host')})
                body=b'RETRY_RESPONSE\n';self.send_response(code);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);self.wfile.flush()
                if mode=='stop-after-503':
                    def stop():rs.shutdown();rs.server_close()
                    st=threading.Thread(target=stop);stop_threads.append(st);st.start()
            def log_message(self,*a):pass
        rs=http.server.ThreadingHTTPServer(('127.0.0.1',0),RetryHandler);rs.daemon_threads=True
        rt=threading.Thread(target=rs.serve_forever,kwargs={'poll_interval':.02},daemon=True);rt.start();retry_servers.append((rs,rt))
        execute('retry-'+mode,base+['--retry','1',f'http://127.0.0.1:{rs.server_port}/retry'],'MISSING','retry' if mode=='stop-after-503' else 'control',rhits)
        rs.shutdown();rs.server_close();rt.join()
        for st in stop_threads:st.join()
    execute('retry-closed-control',base+['--retry','1',url],'OK','control',hits)
finally:
    reservation.close();server.shutdown();server.server_close();thread.join()
    for rs,rt in retry_servers:rs.shutdown();rs.server_close();rt.join()
(W/'new-probes-9.json').write_text(json.dumps({'rows':rows,'all_task_servers_closed':True,'event_provenance':'command/exit/stdout/stderr from actual loopback-only curl processes, wrapped as item/completed; no product/model turn','source_sha256':hashlib.sha256(cur.encode()).hexdigest(),'guards_are_causal_controls_not_product_fixes':True},ensure_ascii=False,indent=2))
