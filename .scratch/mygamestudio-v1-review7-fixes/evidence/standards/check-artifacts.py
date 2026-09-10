from pathlib import Path
import ast, hashlib, io, json, re, subprocess, tarfile

R = Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
OUT = Path('/tmp/mgs-review7-ADyk4of1/standards')
E = '.scratch/mygamestudio-v1-review6-fixes/evidence/'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=R)
def blob(rev, path):
    return git('show', f'{rev}:{path}')
def sha(data):
    return hashlib.sha256(data).hexdigest()
def compare(a_rev, a_path, b_rev, b_path):
    a, b = blob(a_rev, a_path), blob(b_rev, b_path)
    return {'a': f'{a_rev}:{a_path}', 'b': f'{b_rev}:{b_path}',
            'equal': a == b, 'sha256_a': sha(a), 'sha256_b': sha(b)}

report = {'head': git('rev-parse', 'HEAD').decode().strip(),
          'status': git('status', '--porcelain').decode(),
          'diff_command': 'git diff a3c43ce..3e6ae30'}
names = git('diff', '--name-only', 'a3c43ce..3e6ae30').decode().splitlines()
report['changed_file_count'] = len(names)
report['changed_files'] = names
report['commit_ids'] = git('rev-list', '--reverse', 'a3c43ce..3e6ae30').decode().splitlines()
report['commit_3e6ae30_product_paths'] = git('diff', '--name-only', '3e6ae30^', '3e6ae30', '--', 'plugin', 'acceptance', 'tests', 'dist').decode().splitlines()
report['head_extra_paths'] = git('diff', '--name-only', '3e6ae30..HEAD').decode().splitlines()

history = [compare('1eef7d8', 'plugin/records/mgs_github.py', 'HEAD', E+'mixed-layout/mgs_github_1eef7d8.py'),
           compare('c61cf9e', E+'curl-boundaries-6/curl-boundaries-6.json', 'HEAD', E+'curl-boundaries-6/curl-boundaries-6-spec-agent.json'),
           compare('c61cf9e', E+'curl-boundaries-6/curl-boundaries-6.py', 'HEAD', E+'curl-boundaries-6/curl-boundaries-6-spec-agent.py'),
           compare('c61cf9e', E+'mixed-layout/mixed-layout-probe.py', 'HEAD', E+'mixed-layout/mixed-layout-standards-probe.py')]
for name in ('direct', 'host-tab', 'ipv6-loopback', 'port-negative', 'port-overflow', 'port-text', 'proxy-overrides-url-host', 'resolve-overrides-url-host', 'target-success-other-failed', 'uppercase-dns-host', 'userinfo-correct-host'):
    history.append(compare('c61cf9e', E+f'curl-boundary-fixtures/{name}.jsonl', 'HEAD', E+f'curl-boundary-fixtures-spec-agent/{name}.jsonl'))
report['renamed_historical_bytes'] = history
immutable = [n for n in git('ls-tree', '-r', '--name-only', 'c61cf9e', E).decode().splitlines()
             if n not in git('diff', '--no-renames', '--name-only', 'c61cf9e..HEAD', '--', E).decode().splitlines()]
report['preserved_original_evidence_count'] = len(immutable)
report['preserved_original_evidence_changed'] = [n for n in immutable if blob('c61cf9e',n) != blob('HEAD',n)]
main_script = (R/E/'curl-boundaries-6/curl-boundaries-6-main.py').read_text()
triage_script = (R/E/'curl-boundaries-6-triage/curl-boundaries-6.py').read_text()
normalize_workdir = lambda t: re.sub(r"W=pathlib.Path\('[^']+'\)", "W=pathlib.Path('<workspace>')", t)
report['main_script_equals_triage_except_workspace'] = normalize_workdir(main_script)==normalize_workdir(triage_script)

tarpath = 'dist/mygamestudio-0.18.0.tar.gz'
def members(rev):
    with tarfile.open(fileobj=io.BytesIO(blob(rev,tarpath)), mode='r:gz') as tf:
        return ({m.name: tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()},
                [m.name for m in tf.getmembers() if m.pax_headers])
old, old_pax = members('a3c43ce')
new, new_pax = members('HEAD')
manifest={line.split('  ',1)[1]:line.split('  ',1)[0] for line in blob('HEAD','dist/package-manifest.txt').decode().splitlines()}
source_files = git('ls-tree','-r','--name-only','HEAD','plugin').decode().splitlines()
report['dist'] = {'sha256': sha(blob('HEAD',tarpath)), 'file_count': len(new),
    'source_file_count':len(source_files), 'manifest_file_count':len(manifest),
    'source_paths_equal_archive':set(source_files)==set(new),
    'source_byte_mismatches':[n for n in new if new[n]!=blob('HEAD',n)],
    'manifest_mismatches':[n for n in new if manifest.get(n.removeprefix('plugin/'))!=sha(new[n])],
    'changed_archive_members':[n for n in sorted(set(old)|set(new)) if old.get(n)!=new.get(n)],
    'pax_headers':new_pax,
    'unchanged_since_4f938e4':all(blob('HEAD','dist/'+n)==blob('4f938e4','dist/'+n) for n in ('mygamestudio-0.18.0.tar.gz','package-manifest.txt','SHA256SUMS.txt'))}
report['sha256sums_match'] = all(sha(blob('HEAD', 'dist/'+line.split('  ',1)[1]))==line.split('  ',1)[0] for line in blob('HEAD','dist/SHA256SUMS.txt').decode().splitlines())

def leaf_changes(a,b,path=''):
    if type(a)!=type(b): return [path]
    if isinstance(a,dict):
        return sum((leaf_changes(a.get(k),b.get(k),path+'.'+k) for k in sorted(set(a)|set(b))),[])
    if isinstance(a,list):
        if len(a)!=len(b): return [path+'.length']
        return sum((leaf_changes(x,y,f'{path}[{i}]') for i,(x,y) in enumerate(zip(a,b))),[])
    return [path] if a!=b else []
driver={}
for n in names:
    if n.startswith('acceptance/') and '/evidence/' in n and n.endswith('.json'):
        a,b=json.loads(blob('a3c43ce',n)),json.loads(blob('HEAD',n))
        driver[n]=leaf_changes(a,b)
report['driver_changed_leaf_paths']=driver
report['driver_protected_top_level_field_changes']={}
for n in driver:
    a,b=json.loads(blob('a3c43ce',n)),json.loads(blob('HEAD',n))
    changed=[k for k in ('op','decision','target','policy_sha256','written_sha256','rule_stage') if a.get(k)!=b.get(k)]
    if changed:report['driver_protected_top_level_field_changes'][n]=changed
report['retained_streams']=[compare('a3c43ce','acceptance/18-complete-package-acceptance/evidence/'+name+'-events.jsonl','HEAD','acceptance/18-complete-package-acceptance/evidence/'+name+'-events.jsonl') for name in ('r1','g1','p1','p2','r1b')]

parse_errors=[]
file_audit=[]
for n in names:
    data=blob('HEAD',n)
    try:
        text=data.decode()
    except UnicodeDecodeError:
        file_audit.append({'path':n,'bytes':len(data),'binary':True,'sha256':sha(data)})
        continue
    file_audit.append({'path':n,'bytes':len(data),'lines':len(text.splitlines()),'sha256':sha(data)})
    try:
        if n.endswith('.json'): json.loads(text)
        elif n.endswith('.jsonl'):
            for line in text.splitlines():
                if line.strip():json.loads(line)
        elif n.endswith('.py'):ast.parse(text, filename=n)
    except (ValueError,SyntaxError) as exc:
        parse_errors.append({'path':n,'error':str(exc)})
report['changed_file_format_parse_errors']=parse_errors
report['file_audit']=file_audit
(OUT/'artifact-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('changed_files','renamed_historical_bytes','retained_streams','file_audit')},ensure_ascii=False,indent=2))
