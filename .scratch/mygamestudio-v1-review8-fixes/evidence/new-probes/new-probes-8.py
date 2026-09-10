from pathlib import Path
import subprocess,re,shlex,socket,threading,http.server,json,os,time,hashlib
W=Path('/tmp/mgs-review8-60iu1bo4');F=W/'new-fixtures';F.mkdir(exist_ok=True)
text=(W/'repo/acceptance/18-complete-package-acceptance/run.sh').read_text()
extract=lambda s:re.search(r'^curl_direct_denied\(\) \{.*?^\}',s,re.M|re.S).group()
cur=extract(text)
old=extract(subprocess.check_output(['git','show','3e6ae30:acceptance/18-complete-package-acceptance/run.sh'],cwd=W/'repro',text=True))
guard_prefix=cur.replace('            if value_at is not None:\n','            if value_at is not None:\n                if not all(ch in CURL_PLAIN_SHORT for ch in body[:value_at]):\n                    return None\n')
guard_host=cur.replace('STANDBY_HOST in line','re.search(r"(?<![0-9.])127\\.0\\.0\\.1(?![0-9.])", line)')
guard_diag=cur.replace('connect_fail_words.search(line) and STANDBY_HOST in line','re.search(r"^curl: \\((?:7|28)\\) (?:Failed to connect to|Couldn\'t connect to) 127\\.0\\.0\\.1(?: |:)", line, re.I)')
assert all(v!=cur for v in [guard_prefix,guard_host,guard_diag])
reservation=socket.socket();reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
hits=[]
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        code=302 if self.path=='/redirect' else 200
        hits.append({'path':self.path,'status':code,'host':self.headers.get('Host')})
        self.send_response(code)
        if code==302:
            self.send_header('Location',f'http://127.0.0.1:{port}/closed');self.end_headers();return
        body=b'Failed to connect to 127.0.0.1\n' if self.path in ['/diagnostic-body','/complete-diagnostic-body'] else b'TARGET_SUCCESS\n'
        slow=self.path!='/complete-diagnostic-body'
        self.send_header('Content-Length',str(len(body)+(10 if slow else 0)));self.end_headers();self.wfile.write(body);self.wfile.flush()
        if slow:time.sleep(.7)
    def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
url=f'http://127.0.0.1:{port}/closed';target=f'http://127.0.0.1:{server.server_port}'
env={'PATH':os.environ['PATH'],'HOME':str(W/'home'),'CURL_HOME':str(W/'home'),'LANG':'C','TMPDIR':str(W/'tmp'),'PYTHONDONTWRITEBYTECODE':'1'}
config=F/'resolve.curlrc';config.write_text(f'resolve = \"127.0.0.1:{port}:127.0.0.2\"\n')
base=['/usr/bin/curl','-q','--noproxy','*','--connect-timeout','.2','--max-time','2']
cases=[
    ('direct',base+[url],'OK','control',{}),
    ('aggregate-redirect-attached',base+['-Lm2',target+'/redirect'],'MISSING','short-prefix',{}),
    ('aggregate-redirect-separate',base+['-Lm','2',target+'/redirect'],'MISSING','short-prefix',{}),
    ('aggregate-redirect-sSm2',base+['-LsSm2',target+'/redirect'],'MISSING','short-prefix',{}),
    ('attached-config',base+['-K'+str(config),url],'MISSING','short-prefix',{}),
    ('standalone-config',base+['-K',str(config),url],'MISSING','control',{}),
    ('standalone-redirect',base+['-L',target+'/redirect'],'MISSING','control',{}),
    ('valid-aggregate-attached',base+['-sSm2',url],'OK','control',{}),
    ('valid-aggregate-separate',base+['-sSm','2',url],'OK','control',{}),
    ('terminator-url',base+['--',url],'OK','control',{}),
    ('invalid-short-value',base+['-ms2',url],'MISSING','control',{}),
    ('proxy-user-short',base+['-U','demo:fixture',url],'MISSING','control',{}),
    ('response-body-then-timeout',base+['--max-time','.2',target+'/diagnostic-body'],'MISSING','output-origin',{}),
    ('plain-body-then-timeout',base+['--max-time','.2',target+'/plain-body'],'MISSING','control',{}),
    ('response-body-completed',base+[target+'/complete-diagnostic-body'],'MISSING','control',{}),
    ('ambient-proxy-dot10',['/usr/bin/curl','-q','--connect-timeout','.2','--max-time','.5',url],'MISSING','host-boundary',{'http_proxy':f'http://127.0.0.10:{port}','no_proxy':''}),
    ('ambient-proxy-dot2',['/usr/bin/curl','-q','--connect-timeout','.2','--max-time','.5',url],'MISSING','control',{'http_proxy':f'http://127.0.0.2:{port}','no_proxy':''}),
]
functions={'current':cur,'before_batch':old,'prefix_guard':guard_prefix,'host_guard':guard_host,'diagnostic_guard':guard_diag,'restored':cur}
rows=[]
try:
    for name,args,expect,group,extra in cases:
        before=len(hits);p=subprocess.run(args,cwd=F,env=dict(env,**extra),capture_output=True,text=True,timeout=6)
        event={'type':'commandExecution','command':shlex.join(args),'status':'failed' if p.returncode else 'completed','exitCode':p.returncode,'aggregatedOutput':p.stdout+p.stderr}
        f=F/(name+'.jsonl');f.write_text(json.dumps({'method':'item/completed','params':{'item':event}})+'\n')
        row={'id':name,'group':group,'expected':expect,'command':shlex.join(args),'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'aggregated_output':p.stdout+p.stderr,'target_server_hits':hits[before:],'fixture':str(f),'loopback_env_overrides':extra}
        for label,fn in functions.items():
            q=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(str(f))],env=env,capture_output=True,text=True)
            row[label]={'anchor':q.stdout.strip(),'exit':q.returncode,'stderr':q.stderr}
        row['observed_bug']=row['current']['anchor']!=expect;rows.append(row)
        print(json.dumps({k:row[k] for k in ['id','expected','exit','current','before_batch','prefix_guard','host_guard','diagnostic_guard','observed_bug','target_server_hits']}),flush=True)
finally:reservation.close();server.shutdown();server.server_close();thread.join()
(W/'new-probes-8.json').write_text(json.dumps({'rows':rows,'synthetic_events_from_actual_loopback_processes':True,'output_aggregation':'stdout + stderr, same convention as original review7 probe','all_task_servers_closed':True,'current_source_sha256':hashlib.sha256(cur.encode()).hexdigest(),'guards_are_scoped_causal_controls_not_product_fixes':True},ensure_ascii=False,indent=2))
