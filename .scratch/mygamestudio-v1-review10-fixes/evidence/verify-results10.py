from pathlib import Path
import json,re
W=Path('/tmp/mgs-review10-j5225ubn')
read=lambda n:json.loads((W/n).read_text())
checks=[]
def check(name,ok,detail=None):checks.append({'id':name,'passed':bool(ok),'detail':detail})
def rows(name):
 d=read(name);return d['rows'] if isinstance(d,dict) and 'rows' in d else d
history=read('history-execution-10.json');check('history-15-scripts-exit0',len(history)==15 and all(r['exit']==0 for r in history))
for name,total in [('curl-new-probes.json',5),('path-extra-probes-5.json',8),('path-boundaries-6.json',8),('curl-boundaries-6.json',11),('curl-adversarial-7.json',17),('new-probes-8.json',17),('parallel-curl-supplement.json',3)]:
 data=rows(name);check(name,len(data)==total and all(not r.get('observed_bug',False) for r in data))
data=rows('new-probes-9.json');check('new9-original-19-rows-preserved',len(data)==19)
check('new9-two-disclosed-exceptions-only',{r['id'] for r in data if r['observed_bug']}=={'full-diagnostic-body','retry-closed-control'})
check('new9-SP27-29-current-outcomes',all(r['current']['anchor']==r['expected'] for r in data if r['id'] not in {'full-diagnostic-body','retry-closed-control'}))
check('new9-full-diagnostic-body-accepted',next(r for r in data if r['id']=='full-diagnostic-body')['current']['anchor']=='OK')
check('new9-retry-closed-accepted-flip',next(r for r in data if r['id']=='retry-closed-control')['current']['anchor']=='MISSING')
data=rows('spec-probes.json');check('SP7-partial-retry-post1',data[0]['post_count']==1 and not data[0]['observed_bug']);check('SP8-anchor-retained',all(not r['observed_bug'] for r in data[1:]))
data={r['id']:r for r in rows('spec-independent-probes.json')}
check('SP10-no-cache-disclosed',data['no-cache-partial-retry']['posts']==2 and data['no-cache-partial-retry']['first_has_warning'])
for n in ['corrupt-json','corrupt-shape-object']:check('SP11-'+n,data[n]['posts']==1)
check('SP12-collision-own-body',data['pending-hash-collision']['posts']==2 and data['pending-hash-collision']['second_body_exists'])
check('SP12-resource-anchors',all(data[n]['anchor']=='MISSING' for n in ['absolute-prefix','identity-comments-suffix','identity-double-comments']))
data=rows('spec-extra-pending.json');check('SP14-dual-identities',data[0]['posts']==2 and data[0]['a_comment_count']==1 and not data[0]['observed_bug'])
check('SP14-corrupt-receipts',all(r['posts']==1 and r['disclosed_corrupt'] for r in data[1:4]))
check('SP14-body-boundaries',all(not r['observed_bug'] for r in data[4:]))
data=rows('curl-extra-probes-5.json');check('SP15-url-known-limit-only',{r['id'] for r in data if r['observed_bug']}=={'true-url-flag'})
for tag in ['plain','guard']:
 d=read(f'mixed-{tag}/result.json');check('SP17-mixed-'+tag,d['posts']==2 and d['b_comment_count']==1 and not d['observed_bug'])
d=json.loads((W/'logs/mixed-layout-standards.py.log').read_text());check('SP17-standards',d['post_count']==2 and d['b_comment_count']==1 and d['b_initial_id']==d['b_recovery_id'])
d=read('acceptance-probes-6.json');check('retained-10-of-10',d['passed']==d['total']==10);check('retained-original-bytes-unchanged',all(r['unchanged_from_batch_base'] for r in d['streams']))
d=read('mutation-results-10.json');check('mutations-expected-counts',all(r['matches_expected'] for r in d['runs']));check('mutations-byte-restored',d['byte_restored'])
d=read('suite-results-10.json');check('four-complete-suites-pass',all(r['exit']==0 and r['complete_suite'] for r in d[1:]));check('package-permitted-checks-pass',d[0]['exit']==0 and len(d[0]['skipped'])==3)
log=(W/'logs/driver-probes-10.log').read_text();check('driver-33-pass',bool(re.search(r'^PASS: 33  FAIL: 0$',log,re.M)))
check('syntax18-pass',len(read('syntax-checks-10.json'))==18 and all(r['exit']==0 for r in read('syntax-checks-10.json')))
check('product-diff-check',read('product-diff-check-10.json')['exit']==0)
(W/'verified-results-10.json').write_text(json.dumps({'checks':checks,'passed':sum(c['passed'] for c in checks),'total':len(checks),'meaning':'evidence and expected-result consistency, not overall product acceptance'},ensure_ascii=False,indent=2))
print(json.dumps({'passed':sum(c['passed'] for c in checks),'total':len(checks),'failures':[c['id'] for c in checks if not c['passed']]}))
