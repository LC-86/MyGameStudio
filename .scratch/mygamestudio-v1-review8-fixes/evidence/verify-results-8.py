from pathlib import Path
import json,subprocess,hashlib,re,os
W=Path('/tmp/mgs-review8-60iu1bo4');R=W/'repo';REAL=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
load=lambda n:json.loads((W/n).read_text())
checks=[]
def ck(name,ok,detail=None):checks.append({'id':name,'pass':bool(ok),'detail':detail})
original=load('curl-adversarial-7.json')['rows']
ck('original17',len(original)==17 and all(not r['observed_bug'] and not r['current']['exit'] for r in original))
mut=load('mutation-results-8.json');ck('mutation_counts',all(r['matches_expected'] for r in mut['runs']),{r['id']:r['failure_count'] for r in mut['runs']});ck('mutation_restored',mut['byte_restored'])
ck('five_suites',len(load('suite-results.json'))==5 and all(r['exit']==0 for r in load('suite-results.json')))
driver=(W/'logs/driver-probes.log').read_text();ck('driver33',load('driver-result.json')['exit']==0 and bool(re.search(r'^PASS: 33  FAIL: 0$',driver,re.M)))
ck('six_history_scripts',len(load('history-execution.json'))==6 and all(r['exit']==0 for r in load('history-execution.json')))
ck('additional_history_scripts',all(r['exit']==0 for r in load('additional-history-execution.json')))
sp=load('spec-probes.json');ck('sp7',sp[0]['post_count']==1 and not sp[0]['observed_bug']);ck('old_target_actions',all(not r['observed_bug'] for r in sp[1:]))
si={r['id']:r for r in load('spec-independent-probes.json')}
ck('sp10_accepted_no_cache',si['no-cache-partial-retry']['posts']==2 and si['no-cache-partial-retry']['first_has_warning'])
ck('sp11_corrupt',all(si[n]['posts']==1 for n in ['corrupt-json','corrupt-shape-object']))
ck('sp12_hash_identity',si['pending-hash-collision']['posts']==2 and si['pending-hash-collision']['second_body_exists'])
ck('resource_identity',all(si[n]['anchor']=='MISSING' for n in ['absolute-prefix','identity-comments-suffix','identity-double-comments']))
ck('sp13',all(not r['observed_bug'] for r in load('curl-new-probes.json')))
se=load('spec-extra-pending.json');ck('sp14',not se[0]['same_pending_file'] and se[0]['posts']==2 and se[0]['a_comment_count']==1)
ck('missing_receipts',all(r['posts']==1 and r['disclosed_corrupt'] for r in se[1:4]));ck('body_identity',all(not r['observed_bug'] for r in se[4:]))
ce=load('curl-extra-probes-5.json');ck('sp15',all(not r['observed_bug'] for r in ce if r['id']!='true-url-flag'));ck('accepted_url_limit',next(r for r in ce if r['id']=='true-url-flag')['anchor']=='MISSING')
ck('sp16',all(not r['observed_bug'] for r in load('path-extra-probes-5.json')))
ck('path_unicode',all(r['matches_target']['anchor']==r['expected'] and r['matches_self']['anchor']=='OK' for r in load('path-boundaries-6.json')))
for n in ['mixed-plain/result.json','mixed-guard/result.json']:
    j=load(n);ck('sp17-'+n,j['posts']==2 and j['b_comment_count']==1 and not j['observed_bug'] and not j['manual_receipt_edits'])
ms=json.loads((W/'logs/mixed-standards.log').read_text());ck('sp17-standards',ms['post_count']==2 and ms['b_comment_count']==1 and ms['b_initial_id']==ms['b_recovery_id'])
bound=load('curl-boundaries-6.json');ck('sp18_19',len(bound)==11 and all(not r['observed_bug'] for r in bound))
ret=load('acceptance-probes-6.json');ck('retained',ret['passed']==10 and ret['total']==10 and all(x['unchanged_from_batch_base'] for x in ret['streams']))
new=load('new-probes-8.json')['rows'];groups={'short-prefix':'prefix_guard','output-origin':'diagnostic_guard','host-boundary':'host_guard'}
for group,guard in groups.items():
    rows=[r for r in new if r['group']==group];ck('new-causal-'+group,all(r['current']['anchor']=='OK' and r[guard]['anchor']=='MISSING' and r['restored']['anchor']=='OK' for r in rows),[r['id'] for r in rows])
ck('new_true_controls',all(not r['observed_bug'] for r in new if r['group']=='control'))
syntax=[]
for p in sorted((R/'acceptance').glob('*/run.sh')):
    q=subprocess.run(['bash','-n',str(p)],capture_output=True,text=True);syntax.append({'file':str(p.relative_to(R)),'exit':q.returncode,'stderr':q.stderr})
ck('bash_syntax',all(x['exit']==0 for x in syntax),{'files':len(syntax)})
(W/'syntax-checks.json').write_text(json.dumps(syntax,indent=2))
for label,args in [('batch',['git','diff','--check','3e6ae30..3f3031a']),('product',['git','diff','--check','3e6ae30..3f3031a','--','acceptance','tests','plugin','dist'])]:
    q=subprocess.run(args,cwd=REAL,capture_output=True,text=True);(W/'logs'/f'diff-check-{label}.log').write_text(q.stdout+q.stderr)
    if label=='product':ck('product_diff_check',q.returncode==0)
    else:(W/'diff-check-batch.json').write_text(json.dumps({'exit':q.returncode,'nonzero_reason':'archived patch blank context lines contain trailing spaces','log':str(W/'logs/diff-check-batch.log')},indent=2))
ck('old_module_git_equality',(R/'.scratch/mygamestudio-v1-review6-fixes/evidence/mixed-layout/mgs_github_1eef7d8.py').read_bytes()==subprocess.check_output(['git','show','1eef7d8:plugin/records/mgs_github.py'],cwd=REAL))
ck('driver_script_restored',(R/'acceptance/18-complete-package-acceptance/driver-probes.sh').read_bytes()==(REAL/'acceptance/18-complete-package-acceptance/driver-probes.sh').read_bytes())
ck('run_script_restored',(R/'acceptance/18-complete-package-acceptance/run.sh').read_bytes()==(REAL/'acceptance/18-complete-package-acceptance/run.sh').read_bytes())
result={'checks':checks,'passed':sum(r['pass'] for r in checks),'failed':sum(not r['pass'] for r in checks),'preserved_raw_known_limit':{'file':'curl-extra-probes-5.json','id':'true-url-flag','observed_bug':True,'classification':'accepted support limit, not new finding'}}
(W/'verified-results-8.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
