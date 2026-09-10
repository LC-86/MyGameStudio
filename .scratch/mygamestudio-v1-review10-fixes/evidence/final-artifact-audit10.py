from pathlib import Path
import json,hashlib,re,subprocess,datetime
W=Path('/tmp/mgs-review10-j5225ubn');S=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
p=W/'verification-summary-10.json';d=json.loads(p.read_text());report=(W/'review-10.md').read_text()
checks=[]
def ck(name,ok,detail=None):checks.append({'id':name,'passed':bool(ok),'detail':detail})
ck('required-artifacts-exist',p.is_file() and (W/'review-10.md').is_file())
ck('conclusion-leading',all(x in report[:500] for x in ['SP-27','SP-30','不具备','三个']))
ck('axes-consistent',d['axes']['Standards']['findings']==0 and d['axes']['Spec']['findings']==len(d['new_findings'])==1)
ck('finding-priority-and-provenance',d['new_findings'][0]['id']=='SP-30' and d['new_findings'][0]['priority']=='P2' and not d['new_findings'][0]['introduced_by_batch'])
ck('original-observed-fields-retained',len(d['original_probes'])==113 and all('observed_bug' in r and 'observed_bug_field_present' in r for r in d['original_probes']))
for ident in ['full-diagnostic-body','retry-closed-control','true-url-flag']:
 ck('raw-exception-'+ident,next(r for r in d['original_probes'] if r['id']==ident)['observed_bug'] is True)
ck('new-six-probes-confirmed',d['independent_confirmation']['row_count']==36 and d['independent_confirmation']['same_results_as_independent_spec'] and len(d['independent_confirmation']['observed_bug_ids'])==6)
ck('mutations-nine-runs',len(d['mutations']['runs'])==9 and all(r['matches_expected'] for r in d['mutations']['runs']) and d['mutations']['byte_restored'])
ck('no-placeholder-comments','<!--' not in report and 'SOURCE/' not in report)
missing=[]
for target in re.findall(r'\]\(([^)]+)\)',report):
 if target.startswith(('https://','http://','#')):continue
 target=re.sub(r':\d+$','',target)
 q=Path(target) if target.startswith('/') else W/target
 if not q.exists():missing.append(str(q))
ck('all-report-file-links-exist',not missing,missing)
ck('coverage-limits-prominent','三项测试未执行' in report and '严格网络隔离存在证据缺口' in report and len(d['suites'][0]['skipped'])==3 and not d['suites'][0]['complete_suite'])
ck('history-audit-pass',d['evidence_audit']['passed']==d['evidence_audit']['total']==36)
current_files=subprocess.check_output(['git','ls-files','-z'],cwd=S).decode().split('\0')
current={f:hashlib.sha256((S/f).read_bytes()).hexdigest() for f in filter(None,current_files) if (S/f).is_file()}
source_start=json.loads((W/'source-manifest-start.json').read_text())
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip();status=subprocess.check_output(['git','status','--porcelain'],cwd=S,text=True)
ck('source-head-unchanged',head==d['actual_head']);ck('source-worktree-clean',status=='');ck('source-all-tracked-bytes-unchanged',current==source_start)
boundary=json.loads((W/'final-boundary-check-10.json').read_text());boundary.update(head=head,status_porcelain=status,changed_tracked_bytes=[f for f in set(current)|set(source_start) if current.get(f)!=source_start.get(f)])
(W/'final-boundary-check-10.json').write_text(json.dumps(boundary,indent=2))
# Scan after report creation, with exact quoted field names (not filename suffixes).
matches=[];file_count=0
for f in W.rglob('*'):
 if not f.is_file() or f.is_symlink():continue
 file_count+=1
 if re.search(rb'(?i)["\\]token(?:_in_args)?[\\"\s:]+[a-f0-9]{64}',f.read_bytes()):matches.append(str(f.relative_to(W)))
scan=json.loads((W/'token-output-scan-10.json').read_text());scan.update(scanned_files=file_count,raw_token_field_hits=matches,token_files=[str(f.relative_to(W)) for f in W.rglob('*.token') if f.is_file()])
(W/'token-output-scan-10.json').write_text(json.dumps(scan,indent=2));ck('artifact-raw-token-scan-zero',not matches and not scan['token_files'])
d.update(source_boundary=boundary,secret_scan=scan,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),artifact_audit='final-artifact-audit-10.json')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
audit={'checks':checks,'passed':sum(c['passed'] for c in checks),'total':len(checks),'artifacts':{n:{'sha256':hashlib.sha256((W/n).read_bytes()).hexdigest(),'bytes':(W/n).stat().st_size} for n in ['review-10.md','verification-summary-10.json']}}
(W/'final-artifact-audit-10.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':audit['passed'],'total':audit['total'],'failures':[r for r in checks if not r['passed']],'artifact_sizes':{k:v['bytes'] for k,v in audit['artifacts'].items()}}))
