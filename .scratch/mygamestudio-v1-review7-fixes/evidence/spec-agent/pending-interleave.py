"""Controlled thread schedule; every receipt is produced by product append_result.

The only injected schedule point is between the completed legacy read and unlink
while a live older client publishes a different, colliding result. FakeTransport
is process local. No credentials, sockets, or real remote calls are involved.
"""
import argparse, importlib.util, json, sys, threading
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--version',choices=['current','a3c43ce'],default='current');P.add_argument('--guard',action='store_true');P.add_argument('--out',type=Path,required=True);args=P.parse_args()
W=Path(__file__).resolve().parent;sys.path.insert(0,str(W/'repo/tests'))
import test_github_backend as gh
def module(ref):
 spec=importlib.util.spec_from_file_location('version_'+ref,W/f'mgs_github_{ref}.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 mod.TransportError=gh.mgs_github.TransportError
 return mod
old=module('1eef7d8');product=gh.mgs_github if args.version=='current' else module(args.version)
args.out.mkdir(parents=True);project=gh.make_github_project(args.out/'project')
fake=gh._OnceReadFailTransport();fake.seed_issue('01-task','Existing')
original=gh.backend_for(project,fake,args.out/'cache')
backend=product.GithubBackend(original.config,fake,args.out/'cache');legacy=old.GithubBackend(original.config,fake,args.out/'cache')
A,B='collision-result-79891','collision-result-80657'
shared_path=legacy._pending_index_file('01-task',A)
assert shared_path==legacy._pending_index_file('01-task',B)
fake.fail('PATCH','/issues/1','timeout');first=legacy.append_result('01-task',A);fake._fail=[]
read_done=threading.Event();writer_done=threading.Event();read_text=Path.read_text;unlink=Path.unlink;results={};log=[]
def paused_read(path,*a,**kw):
 contents=read_text(path,*a,**kw)
 if path==shared_path and threading.current_thread().name=='a-complete' and not read_done.is_set():
  log.append({'event':'a-read-legacy','body':json.loads(contents)['args']['result_markdown']})
  read_done.set()
  if not writer_done.wait(10): raise RuntimeError('schedule timed out')
 return contents
def guarded_unlink(path,*a,**kw):
 if args.guard and path==shared_path and threading.current_thread().name=='a-complete':
  receipt=json.loads(read_text(path))
  if {k:receipt.get(k) for k in ['op','args','repo']}!=backend._pending_identity('01-task',A):
   log.append({'event':'guard-preserved-replacement','body':receipt['args']['result_markdown']});return
 return unlink(path,*a,**kw)
def complete_a():
 try: results['a_complete']=backend.append_result('01-task',A)
 except Exception as exc:results['thread_error']=repr(exc)
Path.read_text=paused_read;Path.unlink=guarded_unlink
try:
 thread=threading.Thread(target=complete_a,name='a-complete');thread.start()
 if not read_done.wait(10): raise RuntimeError('reader not paused')
 fake.read_fail=True;fake.fail('PATCH','/issues/1','timeout')
 results['b_partial']=legacy.append_result('01-task',B)
 log.append({'event':'old-client-wrote-b','body':json.loads(read_text(shared_path))['args']['result_markdown']})
 fake._fail=[];writer_done.set();thread.join(10)
 if thread.is_alive():raise RuntimeError('reader did not finish')
 results['b_receipt_survives_a_complete']=shared_path.exists()
 fake.read_fail=True;results['b_retry']=backend.append_result('01-task',B)
finally:
 writer_done.set();Path.read_text=read_text;Path.unlink=unlink
results.update({'version':args.version,'guard':args.guard,'first_old_a':first,'schedule':log,'manual_receipt_edits':False,'entry':'old GithubBackend append_result concurrently with upgraded GithubBackend append_result; local FakeTransport only','posts':sum(m=='POST' and '/comments' in p for m,p,_ in fake.calls),'b_comment_count':sum(c['body']==f'任务:01-task\n\n{B}' for c in fake.comments[1])})
results['observed_bug']=results['b_comment_count']>1
(args.out/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps({k:results[k] for k in ['version','guard','posts','b_comment_count','b_receipt_survives_a_complete','observed_bug']},ensure_ascii=False))
