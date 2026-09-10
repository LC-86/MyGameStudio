from pathlib import Path
import json,hashlib,re,subprocess
W=Path('/tmp/mgs-review9-3hpb5uhl');REAL=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
load=lambda p:json.loads((W/p).read_text())
spec=load('agents/spec/evidence.json');boundary=load('final-boundary-check.json')
groups=[]
for name,p,base in [('SP-18/19','curl-boundaries-6.json','1eef7d8'),('SP-20/23','curl-adversarial-7.json','a3c43ce'),('SP-24/26','new-probes-8.json','3e6ae30')]:
    d=load(p);rows=d['rows'] if isinstance(d,dict) else d
    groups.append({'scope':name,'source':str(W/p),'original_script_before_batch_ref':base,'total':len(rows),'observed_bug_count':sum(r['observed_bug'] for r in rows),'rows':[{k:r[k] for k in ['id','expected','current','observed_bug']} for r in rows]})
new=[]
for name in ['new-probes-9.json','parallel-curl-supplement.json']:
    for r in load(name)['rows']:
        guards={k:v for k,v in r.items() if 'guard' in k}
        new.append({'source':str(W/name),**{k:r[k] for k in ['id','expected','current','observed_bug','restored','exit','target_server_hits']},'group':r.get('group','SP-27-supplement'),'guards':guards,'before_batch':r.get('before_batch',r.get('3f3031a'))})
history_files=['spec-probes.json','spec-independent-probes.json','curl-new-probes.json','spec-extra-pending.json','curl-extra-probes-5.json','path-extra-probes-5.json','path-boundaries-6.json','mixed-plain/result.json','mixed-guard/result.json']
j={
    'review':9,'date':'2026-09-10','workspace':str(W),'source_repo':str(REAL),
    'fixed_range':'3f3031a..e3741c6','product_target':'e3741c6','actual_head':boundary['end_head'],'commits':['1512d11','91991d9','e3741c6'],'batch_commit_count':3,
    'verdict':{'SP24_SP25_SP26_original_counterexamples_repaired':True,'new_confirmed_findings_count':3,'new_batch_regressions_found':0,'new_findings_origin':'already present at 3f3031a','v1_technical_closure_ready':False,'blocking_findings':['SP-27','SP-28','SP-29'],'release_authorized':False},
    'axes':{'Standards':{'hard_violations':0,'reportable_smells':0,'worst_priority':None,'evidence':str(W/'agents/standards/evidence.json')},'Spec':{'findings':3,'worst_priority':'P2','evidence':str(W/'agents/spec/evidence.json')}},
    'original_probe_groups':groups,
    'historical_probes':{'execution':load('history-execution.json'),'additional_execution':load('additional-history-execution.json'),'results':{p:load(p) for p in history_files},'raw_observed_bug_preserved':True},
    'new_findings':spec['confirmed_findings'],'new_probe_rows':new,
    'accepted_limits':[{'id':'true-url-flag','raw_observed_bug':True,'source':str(W/'curl-extra-probes-5.json'),'counted_as_new_finding':False},{'id':'full-diagnostic-body','raw_observed_bug':True,'source':str(W/'new-probes-9.json'),'counted_as_new_finding':False}],
    'mutations':load('mutation-results-9.json'),'retained':load('acceptance-probes-6.json'),
    'suites':load('suite-results.json'),'driver':load('driver-result.json'),'syntax':load('syntax-checks.json'),'result_audit':load('verified-results-9.json'),
    'dist':{'changed':False,'rebuilt_delivered_artifact':False,'sha256':'3c44e2c0aaa0f02571fc394b30dd4ed34a9d0833c554531856b6a04f47c37ea7','package_files':79,'pax_members':0,'package_suite_temporary_rebuilds':2},
    'source_boundary':boundary,
    'validation_boundaries':{'acceptance_run_sh_startups':0,'product_acceptance_model_turns':0,'real_remote_writes':0,'real_github_requests':0,'daily_client_install_changes':0,'review_agents':2,'fresh_real_curl_executor':'root','spec_agent_independent_evidence_audit':True,'implementation_historical_original_outputs_byte_provenance_verified':False,'temporary_test_token_files_ever_created':True,'real_account_credentials_read_or_output':False,'temporary_test_token_states_cleaned':True,'copied_historical_token_fields_redacted':2,'literal_no_test_token_ever_on_disk_requirement_met':False,'token_scan':load('token-output-scan.json'),'all_task_servers_closed':True,'remaining_task_processes':0,'scope_of_claim':'acceptance predicate correctness, not proof of runtime permission bypass or fresh client/model acceptance'},
    'experiment_calibrations':{'diagnostic':load('mutation-results-9.json')['initial_diagnostic_calibration'],'bare_parallel_Z':'initial progress prefix rejects diagnostic; silent -sS -Z independently confirms arity issue','retry_guard':'also rejects true retry failure control, causal control only; not complete fix'},
    'artifacts':{'report':str(W/'review-9.md'),'summary':str(W/'verification-summary-9.json'),'ast_fixture_literals':str(W/'test-fixtures-ast.json'),'original_fixture_replay':str(W/'agents/spec/original-fixture-replay.json')}
}
report=(W/'review-9.md').read_text();j['report_sha256']=hashlib.sha256(report.encode()).hexdigest()
missing=[]
for target in re.findall(r'\]\((/[^)]+)\)',report):
    p=re.sub(r':\d+$','',target)
    if p==str(W/'verification-summary-9.json'):continue
    if not Path(p).exists():missing.append(target)
assert not missing,missing
assert j['mutations']['byte_restored'] and all(r['matches_expected'] for r in j['mutations']['runs'])
assert j['result_audit']['failed']==0
assert len(load('test-fixtures-ast.json')['rows'])==17
(W/'verification-summary-9.json').write_text(json.dumps(j,ensure_ascii=False,indent=2))
end_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REAL,text=True).strip();end_status=subprocess.check_output(['git','status','--porcelain'],cwd=REAL,text=True)
assert end_head==boundary['start']['head'] and not end_status
print(json.dumps({'report':str(W/'review-9.md'),'summary':str(W/'verification-summary-9.json'),'axes':j['axes'],'missing_links':missing,'source_unchanged':True,'result_audit_pass':j['result_audit']['passed'],'run_sha256':j['mutations']['run_sha256']},ensure_ascii=False,indent=2))
