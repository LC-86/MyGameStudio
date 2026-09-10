import ast
import collections
import hashlib
import json
import pathlib
import re
import subprocess
import tarfile

REAL = pathlib.Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
SAFE = pathlib.Path('/tmp/mgs-review11-kgohlovv/repo')
OUT = pathlib.Path('/tmp/mgs-review11-kgohlovv/standards')
BASE = '66b8506'
PRODUCT = 'd604b92'
def git(*args):
    return subprocess.check_output(['git', '-C', str(REAL), *args])
def blob(rev, p):
    return git('show', f'{rev}:{p}')
def sha(b):
    return hashlib.sha256(b).hexdigest()
def dump(node):
    return ast.dump(node, include_attributes=False)
def diff_values(a,b,p='$'):
    if type(a)!=type(b): return [p]
    if isinstance(a,dict):
        r=[]
        for k in sorted(a.keys()|b.keys()):
            if k not in a or k not in b:r.append(p+'.'+k)
            else:r += diff_values(a[k],b[k],p+'.'+k)
        return r
    if isinstance(a,list):
        if len(a)!=len(b):return [p+'.length']
        return sum((diff_values(x,y,f'{p}[{i}]') for i,(x,y) in enumerate(zip(a,b))),[])
    return [] if a==b else [p]

result={'axis':'Standards','baseline':BASE,'product':PRODUCT,'start_head':git('rev-parse','HEAD').decode().strip(),
        'start_porcelain_clean':not git('status','--porcelain'), 'hard_violations':[], 'judgment_smells':[],
        'hard_violation_count':0,'judgment_smell_count':0,
        'standards_read':['AGENTS.md','AGENTS.zh-CN.md','CONTEXT.md','docs/agents/issue-tracker.md','docs/agents/triage-labels.md','docs/agents/domain.md','user supplied global rules and review handoff']}
commits=git('rev-list','--reverse',BASE+'..'+PRODUCT).decode().splitlines()
result['commits']=[{'sha':c,'changed_files':len(git('diff-tree','--no-commit-id','--name-only','-r',c).decode().splitlines())} for c in commits]
run='acceptance/18-complete-package-acceptance/run.sh'
before=blob(BASE,run).decode();after=blob(PRODUCT,run).decode()
pattern=r'^curl_direct_denied\(\).*?^}\n'
bmatch=re.search(pattern,before,re.M|re.S);amatch=re.search(pattern,after,re.M|re.S)
result['run_scope']={
 'outside_function_identical':before[:bmatch.start()]+before[bmatch.end():]==after[:amatch.start()]+after[amatch.end():],
 'sha256':sha(after.encode()),'function_start_line':after[:amatch.start()].count('\n')+1,
 'heredoc_top_level_closing_brace_count':len(re.findall(r'^}',amatch.group(),re.M)),
 'value_tables_unchanged': all(re.findall(r'^'+key+r'.*$',before,re.M)==re.findall(r'^'+key+r'.*$',after,re.M) for key in ['CURL_VALUE_SHORT','CURL_PLAIN_SHORT','CURL_VALUE_LONG','CURL_PLAIN_LONG'])}
old_py=bmatch.group().split("<<'PYEOF'\n",1)[1].split('\nPYEOF',1)[0]
new_py=amatch.group().split("<<'PYEOF'\n",1)[1].split('\nPYEOF',1)[0]
ob=ast.parse(old_py);nb=ast.parse(new_py)
old_url=next(n for n in ob.body if isinstance(n,ast.FunctionDef) and n.name=='url_targets')
new_url=next(n for n in nb.body if isinstance(n,ast.FunctionDef) and n.name=='url_targets')
removed=[]
class RemoveGuard(ast.NodeTransformer):
    def visit_If(self,node):
        if isinstance(node.test,ast.BoolOp) and isinstance(node.test.op,ast.And) and isinstance(node.test.values[0],ast.Compare) and dump(node.test.values[0])==dump(ast.parse("tok == '--upload-file'",mode='eval').body):
            removed.append('long');return None
        if dump(node.test)==dump(ast.parse("body[value_at] == 'T'",mode='eval').body):
            removed.append('short');return None
        return self.generic_visit(node)
RemoveGuard().visit(nb)
result['run_scope']['added_guard_types']=removed
result['run_scope']['python_ast_without_two_new_guards_equals_baseline']=dump(ob)==dump(nb)

test='tests/test_plugin_package.py'
ot=ast.parse(blob(BASE,test));nt=ast.parse(blob(PRODUCT,test))
old_test=next(n for n in ot.body if isinstance(n,ast.FunctionDef) and n.name=='test_accept18_probe_checks_anchored_to_events')
new_test=next(n for n in nt.body if isinstance(n,ast.FunctionDef) and n.name=='test_accept18_probe_checks_anchored_to_events')
old_calls=[dump(n) for n in ast.walk(old_test) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check']
new_calls=[dump(n) for n in ast.walk(new_test) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check']
remaining=list(new_calls)
for c in old_calls:
    if c in remaining:remaining.remove(c)
result['tests']={'old_check_calls':len(old_calls),'new_check_calls':len(new_calls),'added_check_calls':len(remaining),
 'existing_check_multiset_unchanged':not (collections.Counter(old_calls)-collections.Counter(new_calls)),
 'new_fixture_names':sorted({n.id for n in ast.walk(new_test) if isinstance(n,ast.Name) and re.fullmatch(r'g1_fixture_c[k-t]_events',n.id)})}
new_test.body[0]=old_test.body[0]
def new_fixture_node(n):
    return any(isinstance(x,ast.Name) and re.fullmatch(r'g1_fixture_c[k-t]_events',x.id) for x in ast.walk(n))
class RemoveFixture(ast.NodeTransformer):
    def visit_Expr(self,node):
        return None if new_fixture_node(node) else self.generic_visit(node)
    def visit_Assign(self,node):
        return None if new_fixture_node(node) else self.generic_visit(node)
RemoveFixture().visit(new_test)
result['tests']['entire_test_ast_after_removing_added_doc_fixtures_assertions_equals_baseline']=dump(ot)==dump(nt)

changed=git('diff','--name-only',BASE+'..'+PRODUCT,'--','acceptance/18-complete-package-acceptance/evidence').decode().splitlines()
drivers=[]
driver_data=[]
for p in changed:
    if p.endswith('.json'):
        a=json.loads(blob(BASE,p));b=json.loads(blob(PRODUCT,p))
        drivers.append({'file':p,'changed_json_paths':diff_values(a,b)})
        driver_data.append((p,a,b))
    else:
        a=blob(BASE,p).decode();b=blob(PRODUCT,p).decode()
        drivers.append({'file':p,'changed_line_numbers':[i+1 for i,(x,y) in enumerate(zip(a.splitlines(),b.splitlines())) if x!=y], 'line_counts':[len(a.splitlines()),len(b.splitlines())]})
result['driver_refresh']={'json_files':sum(x['file'].endswith('.json') for x in drivers),'environment_files':sum(not x['file'].endswith('.json') for x in drivers),'files':drivers}
id_pairs={}
def collect_ids(a,b):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in a.keys()&b.keys():
            if k=='instance_id' and isinstance(a[k],str):id_pairs[a[k]]=b[k]
            collect_ids(a[k],b[k])
    elif isinstance(a,list) and isinstance(b,list):
        for x,y in zip(a,b):collect_ids(x,y)
for _,a,b in driver_data:collect_ids(a,b)
semantic_differences=[]
semantic_fields_unchanged={'decision':True,'rule_stage':True,'target':True,'policy_sha256':True}
hash_checks=[]
def normalized_string(v):
    for old,new in id_pairs.items():v=v.replace(old,new)
    return re.sub(r'\d{4}-\d\d-\d\d','<DATE>',v)
def classify(a,b,path='$'):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in a.keys()|b.keys():
            if k not in a or k not in b:semantic_differences.append(path+'.'+k);continue
            if k in semantic_fields_unchanged and a[k]!=b[k]:semantic_fields_unchanged[k]=False
            if k=='body_sha256' and isinstance(b.get('body'),str):
                hash_checks.append({'path':path,'base_valid':sha(a['body'].encode())==a[k],'product_valid':sha(b['body'].encode())==b[k]})
            if a[k]==b[k]:continue
            if k in {'ts','token_fp','instance_id','installedPath','body_sha256'}:continue
            if k=='api_base':
                if re.fullmatch(r'http://127\.0\.0\.1:\d+',a[k]) and re.fullmatch(r'http://127\.0\.0\.1:\d+',b[k]):continue
            if k=='draft':
                # Driver draft paths differ only by their generated timestamp.
                if re.sub(r'\d{8}-\d{6}','<STAMP>',a[k])==re.sub(r'\d{8}-\d{6}','<STAMP>',b[k]):continue
            if k in {'reason','body'} and isinstance(a[k],str) and normalized_string(a[k])==normalized_string(b[k]):continue
            classify(a[k],b[k],path+'.'+k)
    elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        for i,(x,y) in enumerate(zip(a,b)):classify(x,y,f'{path}[{i}]')
    elif a!=b:semantic_differences.append(path)
for p,a,b in driver_data:classify(a,b,p)
result['driver_refresh']['semantic_fields_unchanged']=semantic_fields_unchanged
result['driver_refresh']['body_sha256_checks']=hash_checks
result['driver_refresh']['unclassified_changes']=semantic_differences
result['plugin_dist']={'changed_paths':git('diff','--name-only',BASE+'..'+PRODUCT,'--','plugin','dist').decode().splitlines()}
pack=SAFE/'dist/mygamestudio-0.18.0.tar.gz'
result['plugin_dist']['package_sha256']=sha(pack.read_bytes())
result['plugin_dist']['expected_sha256']='3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7'
result['plugin_dist']['sha256_matches_declared']=result['plugin_dist']['package_sha256']==result['plugin_dist']['expected_sha256']
result['plugin_dist']['sha256_manifest_contains_digest']=result['plugin_dist']['package_sha256'] in (SAFE/'dist/SHA256SUMS.txt').read_text()
package_members=[]
with tarfile.open(pack,'r:gz') as tf:
    for member in tf.getmembers():
        if member.isfile():
            p=pathlib.PurePosixPath(member.name)
            rel=pathlib.Path(*p.parts[1:])
            candidate=SAFE/'plugin'/rel
            if candidate.is_file(): package_members.append({'path':str(rel),'matches':tf.extractfile(member).read()==candidate.read_bytes()})
result['plugin_dist']['tar_matching_plugin_members']=len(package_members)
result['plugin_dist']['tar_plugin_mismatches']=[x['path'] for x in package_members if not x['matches']]

archive='.scratch/mygamestudio-v1-review10-fixes/evidence/'
added=git('diff-tree','--no-commit-id','--name-only','--diff-filter=A','-r','1927a46').decode().splitlines()
result['archive']={'triage_added_evidence_count':len([x for x in added if x.startswith(archive)])}
result['archive']['triage_followup_evidence']=[x for x in added if x.startswith(archive) and '/triage-' in x]
result['archive']['prior_review_archive_count']=result['archive']['triage_added_evidence_count']-len(result['archive']['triage_followup_evidence'])
audit=json.loads((SAFE/archive/'final-artifact-audit-10.json').read_text())
result['archive']['archived_report_and_summary_hashes']={p:{'stored':v['sha256'],'actual':sha((SAFE/archive/p).read_bytes()),'matches':v['sha256']==sha((SAFE/archive/p).read_bytes())} for p,v in audit['artifacts'].items()}
result['end_head']=git('rev-parse','HEAD').decode().strip()
result['end_porcelain_clean']=not git('status','--porcelain')
result['boundary']={'source_head_unchanged':result['start_head']==result['end_head'],'executed_suites':False,'executed_acceptance_run_sh':False,'remote_requests':0,'product_model_calls':0,'driver_raw_values_output':False}
(OUT/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
