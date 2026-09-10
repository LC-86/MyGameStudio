import pathlib,re,difflib
W=pathlib.Path(__file__).parent;E=W/'copy/.scratch/mygamestudio-v1-review3-fixes/evidence'
src=(E/'spec-custom-probes.py').read_text(); s=src.replace("ROOT = Path('/tmp/mygamestudio-review-3-v9s0lp_z')",f'ROOT = Path({str(W)!r})').replace("COPY = ROOT / 'spec'","COPY = ROOT / 'copy'")
s=s.replace('[str(ev), tool, stage, wanted]', '[str(ev), tool, stage, wanted, "write" if tool == "mgs_write" else "update"]')
(W/'spec-custom-probes.py').write_text(s)
diff=list(difflib.unified_diff(src.splitlines(True),s.splitlines(True),fromfile='original/spec-custom-probes.py',tofile='adapted/spec-custom-probes.py'))
src=(E/'acceptance_recheck.py').read_text();s=src[:src.index('\narena=F/')]
s=s.replace('def anchor(path,tool,stage,target):','def anchor(path,tool,stage,target,action):').replace('[path,tool,stage,target]','[path,tool,stage,target,action]')
s=s.replace("anchor(synthetic,'mgs_write','path','/tmp/mgs18-evil-link.md')","anchor(synthetic,'mgs_write','path','/tmp/mgs18-evil-link.md','write')")
s=s.replace('anchor(real/f\'{name}-events.jsonl\',tool,stage,target)',"anchor(real/f'{name}-events.jsonl',tool,stage,target,'write' if tool=='mgs_write' else ('update' if target=='01-harbor-timer' else 'append-result'))")
s+="\n(W/'acceptance-probes-4.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))\nprint(json.dumps(out,ensure_ascii=False,indent=2))\n"
(W/'acceptance_recheck.py').write_text(s)
diff+=list(difflib.unified_diff(src.splitlines(True),s.splitlines(True),fromfile='original/acceptance_recheck.py',tofile='adapted/acceptance_recheck.py'))
(W/'probe-adaptation.diff').write_text(''.join(diff))
