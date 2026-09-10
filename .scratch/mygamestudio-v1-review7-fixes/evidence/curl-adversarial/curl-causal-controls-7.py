from pathlib import Path
import re,subprocess,shlex,json
W=Path('/tmp/mgs-review7-ADyk4of1');text=(W/'repo/acceptance/18-complete-package-acceptance/run.sh').read_text();cur=re.search(r'^curl_direct_denied\(\) \{.*?^\}',text,re.M|re.S).group()
rows=json.loads((W/'curl-adversarial-7.json').read_text())['rows']
oldrows=json.loads((W/'curl-boundaries-6.json').read_text())
guards={
 'original':cur,
 'short-xK-only':cur.replace('CURL_VALUE_SHORT = set("HmXdoAuwbceEKrTQyYzZDxUJg")','CURL_VALUE_SHORT = set("HmXdoAuwbceErTQyYzZDUJg")'),
 'redirect-only':cur.replace('CURL_PLAIN_SHORT = set("sSLkvIifnN46q")','CURL_PLAIN_SHORT = set("sSkvIifnN46q")').replace('"--location", ',''),
 'attached-value-only':cur.replace('''            if any(ch in CURL_VALUE_SHORT for ch in body):
                i += 2
                continue
''','''            value_at = next((j for j, ch in enumerate(body) if ch in CURL_VALUE_SHORT), None)
            if value_at is not None:
                i += 1 if value_at < len(body) - 1 else 2
                continue
'''),
 # Causal control only, not a complete fix: remove ambiguous timeout vocabulary.
 'exclude-generic-timeout-only':cur.replace("couldn't connect|timed out", "couldn't connect"),
 'restored':cur}
results=[]
for name,fn in guards.items():
 result={'variant':name,'cases':[]}
 for row in [*rows,*oldrows]:
  q=subprocess.run(['bash','-c',fn+'\ncurl_direct_denied '+shlex.quote(row['fixture'])],capture_output=True,text=True)
  result['cases'].append({'id':row['id'],'fixture':row['fixture'],'expected':row['expected'],'anchor':q.stdout.strip(),'exit':q.returncode,'stderr':q.stderr})
 results.append(result)
(W/'curl-causal-controls-7.json').write_text(json.dumps({'caveat':'Narrow causal controls in extracted text, not proposed complete fixes or product edits.','variants':results},ensure_ascii=False,indent=2))
for r in results:print(r['variant'],{x['id']:x['anchor'] for x in r['cases'] if x['id'] in ['short-proxy','short-config','redirect-short','attached-short-value-hides-first-url','target-200-body-then-timeout','direct','userinfo-correct-host']})
