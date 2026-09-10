from pathlib import Path
import re,json,subprocess,shlex
W=Path('/tmp/mgs-review6-zonhimd1/spec-agent')
source=(W/'repo-tracked/acceptance/18-complete-package-acceptance/run.sh').read_text()
fn=re.search(r'^curl_direct_denied\(\) \{.*?^\}',source,re.M|re.S).group()
a=fn.replace('        tok = args[i]\n','        tok = args[i]\n        if tok in ("--proxy", "--resolve"):\n            return None\n')
b=fn.replace('    if not urls or not all(', '    if len(urls) != 1 or not all(')
c=a.replace('    if not urls or not all(', '    if len(urls) != 1 or not all(')
rows=[]
for name in ['direct','userinfo-correct-host','proxy-overrides-url-host','resolve-overrides-url-host','target-success-other-failed']:
    fixture=W/'curl-boundary-fixtures'/(name+'.jsonl')
    row={'id':name}
    for label,script in [('baseline',fn),('reject_overrides_only',a),('single_url_only',b),('both_controls',c),('baseline_restore',fn)]:
        p=subprocess.run(['bash','-c',script+'\ncurl_direct_denied '+shlex.quote(str(fixture))],capture_output=True,text=True)
        assert p.returncode==0,p.stderr
        row[label]=p.stdout.strip()
    rows.append(row)
(W/'curl-causal-controls.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
