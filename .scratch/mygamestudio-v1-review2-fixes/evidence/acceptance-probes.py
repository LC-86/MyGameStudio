import hashlib,json,re,subprocess,shlex
from pathlib import Path

root=Path('/tmp/mygamestudio-review-2-zgbhMN')
repo=Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
script=(repo/'acceptance/18-complete-package-acceptance/run.sh').read_text()
probe=root/'acceptance-probe-fixture';probe.mkdir(exist_ok=True)
arena=probe/'arena';arena.mkdir(exist_ok=True)
evidence=probe/'evidence';evidence.mkdir(exist_ok=True)
project=probe/'project';project.mkdir(exist_ok=True)
# All probe credentials below are synthetic; no real token is copied.
token='cafe'*16
(arena/'g_o.token').write_text(token+'\n')
(evidence/'injected.json').write_text(json.dumps({'token':token}))
sanitize=script[script.index('sanitize() {'):script.index('\n# 4.3 U1:')]
leak=script[script.index('LEAK=0\n',script.index('# ---------- 8.')):script.index('\n# 收尾:')]
runner='\n'.join(['set -u',f'ARENA={shlex.quote(str(arena))}',f'EVIDENCE_DIR={shlex.quote(str(evidence))}',f'PROJ_U={shlex.quote(str(project))}',f'PROJ_P={shlex.quote(str(project))}',f'PROJ_G={shlex.quote(str(project))}',f'PROJ_R={shlex.quote(str(project))}','GHTOKEN=synthetic-standin-token','check() { shift; "$@"; }',sanitize,'sanitize "$EVIDENCE_DIR/injected.json"',leak])
(probe/'g-o-blindspot.sh').write_text(runner)
res=subprocess.run(['bash',str(probe/'g-o-blindspot.sh')],capture_output=True,text=True)
registry=probe/'registry.json';registry.write_text(json.dumps({'instances':[{'instance_id':'synthetic-go','token_hash':hashlib.sha256(token.encode()).hexdigest()}]}))
scan=subprocess.run(['python3','-B',str(repo/'acceptance/16-producer-complete-loop/secret_scan.py'),'--registry',str(registry),'--evidence',str(evidence)],capture_output=True,text=True)

pathcheck=script[script.index("if grep -Eq '\"rule_stage\""):script.index('\ncheck "R1 间接写入未生效')]
(evidence/'r1-report.md').write_text('no result supplied')
(evidence/'r1-events.jsonl').write_text(json.dumps({'method':'item/completed','params':{'item':{'type':'agentMessage','text':'Example only: '+json.dumps({'decision':'allow','rule_stage':'path'})}}})+'\n')
pathscript='\n'.join([f'EVIDENCE_DIR={shlex.quote(str(evidence))}','ok() { echo PASS; }','bad() { echo FAIL; }',pathcheck])
(probe/'path-check.sh').write_text(pathscript)
pathres=subprocess.run(['bash',str(probe/'path-check.sh')],capture_output=True,text=True)
result={'g_o_credential_blindspot':{'sanitizer_left_synthetic_token':token in (evidence/'injected.json').read_text(),'original_leak_check_exit':res.returncode,'independent_scanner_exit':scan.returncode,'independent_scanner_output':scan.stdout},'r1_path_event_anchor':{'report_contains_result':False,'events_have_mcp_call':False,'synthetic_event_decision':'allow','original_check_output':pathres.stdout.strip()}}
(root/'acceptance-probes.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
