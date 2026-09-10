from pathlib import Path
import json,re,hashlib
W=Path('/tmp/mgs-review10-j5225ubn/spec')
d=json.loads((W/'arity-audit.json').read_text());manual=(W/'curl-manual.txt').read_text().splitlines()
notes={
'--header':'HTTP header or local header file; alters request, not URL count.',
'--max-time':'Whole-transfer timeout; alone does not prove connection rejection.',
'--request':'Changes HTTP method; one positional URL remains one transfer absent other expansion.',
'--data':'Request body; @file reads local input. No URL expansion by this option.',
'--data-raw':'Request body with literal @ handling; no URL expansion.',
'--data-binary':'Binary request body or local file; no URL expansion.',
'--output':'Local output path; can suppress stdout but does not add a network target.',
'--user-agent':'HTTP request header shaping; no URL expansion.',
'--user':'Authentication settings can affect protocol behavior. Arity-only subprocess used: no credentials supplied or persisted.',
'--write-out':'Formats post-transfer output and can manufacture diagnostic-looking text; accepted output-origin limitation not reopened.',
'--cookie':'Literal cookie or local input file; request/session shaping; no credential-bearing live case executed.',
'--cookie-jar':'Local cookie output; does not add a target. No live cookie-bearing case executed.',
'--referer':'HTTP header shaping; absent permitted redirects it adds no target.',
'--cert':'TLS client certificate source; affects authentication. No client certificate or credential file created/read.',
'--range':'Range request within a transfer; HTTP response-side behavior is not connection denial.',
'--upload-file':'Local filename accepts curl globbing: multiple uploads to one URL. SP-30 confirmed by six real HTTP loopback shapes.',
'--quote':'FTP/SFTP pre-transfer commands; FTP/SFTP URLs rejected by existing http/https URL filter.',
'--speed-time':'Low-speed failure condition after connect; generic timeout rejected by diagnostic-shape gate.',
'--speed-limit':'Low-speed failure condition after connect; generic timeout rejected by diagnostic-shape gate.',
'--time-cond':'Conditional request based on date or local timestamp; no URL expansion.',
'--dump-header':'Local header output; command-output origin remains the accepted residual limitation.',
'--silent':'Suppress progress and error output unless show-error used; can determine whether a diagnostic is present.',
'--show-error':'Re-enable error display with silent; no target expansion.',
'--insecure':'TLS certificate verification relaxed; does not alone add target/request.',
'--verbose':'Adds protocol diagnostics; does not itself change URL count.',
'--head':'HTTP HEAD request; no target expansion.',
'--include':'Includes response headers in stdout; accepted aggregate-output origin limit applies.',
'--fail':'Converts HTTP error responses to nonzero exit; error 22 alone not accepted by connection diagnostic gate.',
'--netrc':'May read credentials from isolated HOME; no netrc file created and no personal HOME used. Arity verified only.',
'--no-buffer':'Output buffering choice; no request expansion.',
'--ipv4':'Address-family restriction; positional hostname still must be literal 127.0.0.1.',
'--ipv6':'Address-family restriction can stop IPv4 literal request; no target expansion.',
'--disable':'Disables implicit curlrc when early in argv; all live probes passed -q first with empty HOME/CURL_HOME.',
'--globoff':'Disables URL and tested upload filename expansion; current URL glob-character policy still conservative.',
'--remote-header-name':'Output-name choice (with remote-name), no argument consumed. -JO/-J -O now reject unknown O; disclosed conservative consequence.',
'--parallel':'Permits parallel transfer scheduling; no-value classification correct. Single URL control OK, multiple URLs rejected.',
'--connect-timeout':'Connection-establishment timeout; accepted with same-host diagnostic.',
'--noproxy':'Exempts hosts from proxy; probes use wildcard plus an environment without proxy variables.',
'--url':'Adds URL via option value; explicitly accepted historical --url parsing limitation not reopened.',
'--form':'Multipart request input; local file/form specifications do not themselves add positional URLs.',
'--key':'TLS private-key source; no key generated/read in probes.',
'--cacert':'TLS server-trust source; no certificate file generated/read in probes.',
'--version':'Prints version and exits successfully without transfer; cannot satisfy failed curl event on actual output.',
'--compressed':'Negotiates compressed HTTP response; no target expansion.',
'--progress-bar':'Output formatting; does not itself add target.',
'--http1.1':'HTTP protocol-version choice; no redirect/retry option implied.',
'--http2':'HTTP/2 negotiation may support internal retry. Four specific h2c/HTTP1/closed probes reported separately; no general proof of retry safety.'}
for r in d['rows']:
 long=re.search(r'--[a-z0-9.-]+',r['help_line']).group();r['canonical_long']=long;r['connection_semantics_review']=notes[long]
 begin=next((i for i,l in enumerate(manual) if re.match(r'^    (?:-., )?'+re.escape(long)+r'(?:\s|$)',l)),None)
 end=next((i for i in range(begin+1,len(manual)) if re.match(r'^    (?:-., )?--[a-z]',manual[i])),len(manual)) if begin is not None else None
 r['manual_start_line']=begin+1 if begin is not None else None;r['manual_excerpt']='\n'.join(manual[begin:end]) if begin is not None else None
assert len(d['rows'])==67 and not d['mismatches'] and all(r['manual_excerpt'] for r in d['rows'])
d['scope']='All 67 admitted table entries independently compared to this host curl 8.7.1 help and no-argument execution. Manual-based per-entry semantic review; selected risky combinations exercised with real loopback curl. This is not exhaustive validation of every option value and protocol behavior.'
(W/'arity-audit.json').write_text(json.dumps(d,indent=2))
p=json.loads((W/'new-curl-probes.json').read_text());h=json.loads((W/'h2-probe.json').read_text());o=json.loads((W/'original-replay.json').read_text())
causal=[]
for r in p['rows']:
 if r['group'].startswith('upload'):
  causal.append({'id':r['id'],'expected':r['expected'],'current':r['current']['anchor'],'e3741c6':r['e3741c6']['anchor'],'3f3031a':r['3f3031a']['anchor'],'precise_upload_glob_guard':r['upload_glob_guard']['anchor'],'broad_upload_guard':r['upload_guard']['anchor'],'restored':r['restored']['anchor']})
(W/'upload-causal-matrix.json').write_text(json.dumps({'rows':causal,'six_counterexample_actual_assertion_failures':{'current':6,'precise_upload_glob_guard':0,'restored':6},'two_normal_upload_controls':{'current':'OK/OK','precise_upload_glob_guard':'OK/OK','broad_upload_guard':'MISSING/MISSING','restored':'OK/OK'},'guards_are_extracted_function_variants_only':True},indent=2))
summary={'axis':'Spec','original_fixes':{'SP-27':'confirmed','SP-28':'confirmed with disclosed retry-closed-control MISSING flip','SP-29':'specified positional URL examples confirmed'},'finding_count':1,'finding':{'id':'SP-30','priority':'P2','title':'Upload filename glob expands one admitted HTTP URL into multiple transfers','introduced_by_batch':False,'present_at':['3f3031a','e3741c6','current'],'source_locations':['acceptance/18-complete-package-acceptance/run.sh:258','acceptance/18-complete-package-acceptance/run.sh:264','acceptance/18-complete-package-acceptance/run.sh:314','acceptance/18-complete-package-acceptance/run.sh:335'],'violated_specs':['.scratch/mygamestudio-v1-review7-fixes/issues/01-curl-anchor-connection-proof-completion.md:16','.scratch/mygamestudio-v1-review6-fixes/issues/02-curl-anchor-connection-params-and-single-url.md:14'],'cases':[r['id'] for r in p['rows'] if r['observed_bug']]},'new_probe_count':len(p['rows']),'new_raw_observed_bug_rows':[r['id'] for r in p['rows'] if r['observed_bug']],'h2_probe_count':len(h['rows']),'h2_raw_observed_bug_rows':[r['id'] for r in h['rows'] if r['observed_bug']],'archive_replay_count':len(o['rows']),'archive_raw_observed_bug_rows':o['raw_current_mismatches'],'accepted_limitations':['full-diagnostic-body raw observed_bug=true retained','retry-closed-control MISSING per disclosed policy','-JO/-J -O now MISSING after correcting J arity; O is outside whitelist','query [] and escaped literal glob characters conservatively rejected','FTP is outside existing HTTP/HTTPS subset; initial expectation corrected with original retained'],'arity_entries':67,'arity_mismatches':0,'technical_closeout':False,'all_spec_task_server_threads_closed':p['all_task_server_threads_closed'] and all(r['server_thread_closed'] for r in h['rows']),'network_boundary':'Live curl invocations only explicit loopback URL targets; proxy-free environment with -q and task HOME/CURL_HOME. Arity calls have no URL. No packet capture; does not claim global network isolation. curl.se official source search/read also performed, no real GitHub access.','credentials':'No credentials or tokens supplied, emitted or persisted by these probes. FTP receives default anonymous exchanges in memory and persists only command verbs.','h2_limit':'Two concrete raw h2c reset/goaway conversations ended with curl error 56, not a confirmed retry sequence. This does not prove every HTTP2 internal-retry path safe.'}
(W/'spec-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
