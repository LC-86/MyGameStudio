#!/usr/bin/env python3
"""Read-only product probing; every write is under the --out /tmp directory.
All remote operations use FakeTransport. No actual network/model calls.
"""
import argparse, hashlib, json, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, default=Path('/tmp/mygamestudio-review-5-niculnow/spec'))
parser.add_argument('--out', type=Path, default=Path('/tmp/mygamestudio-review-5-niculnow'))
args = parser.parse_args()
assert str(args.repo.resolve()).startswith('/private/tmp/') or str(args.repo.resolve()).startswith('/tmp/')
assert str(args.out.resolve()).startswith('/private/tmp/') or str(args.out.resolve()).startswith('/tmp/')
args.out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(args.repo / 'tests'))
import test_github_backend as gh
import test_runtime_gate as rt
A, B = 'collision-result-79891', 'collision-result-80657'

def setup(base, identity='01-task'):
    project = gh.make_github_project(base / 'project')
    svc = rt.GateService(base / 'runtime')
    resources = ['github://github.com/mygamestudio/issue-accept/issues/**', 'src/**']
    svc.init_policy(project, {'producer': resources}, {'production': None})
    instance = svc.create_instance('producer', 'review5-spec', 'production', resources)
    svc._write_json('remote.json', {'github': {'api_base': 'http://unused.invalid',
        'token_env': 'MGS_TEST_UNUSED', 'cache_dir': str(base / 'cache')}})
    fake = gh._OnceReadFailTransport()
    fake.seed_issue(identity, 'Existing')
    class Facade:
        def remote_record(self, token, action, payload):
            return svc.remote_record(token, action, payload, transport=fake)
    def call(result):
        return json.loads(rt.mcp_gate.handle_tools_call(Facade(), 'mgs_remote', {
            'token': instance.token, 'action': 'append-result',
            'payload': {'identity': identity, 'result_markdown': result}
        })['content'][0]['text'])
    return project, fake, call

def posts(fake):
    return sum(m == 'POST' and '/comments' in p for m, p, _ in fake.calls)

def snapshot_pending(base):
    return [{'name': p.name, 'data': json.loads(p.read_text())}
        for p in sorted((base / 'cache' / 'pending-index').rglob('*.json'))]

output = []
with tempfile.TemporaryDirectory(prefix='spec-extra-pending-state-', dir=args.out) as tmp:
    root = Path(tmp)
    base = root / 'collision-both-partial'
    project, fake, call = setup(base)
    backend = gh.backend_for(project, fake, base / 'cache')
    same_file = backend._pending_index_file('01-task', A) == backend._pending_index_file('01-task', B)
    assert not same_file and backend._pending_index_file('01-task', A).parent == backend._pending_index_file('01-task', B).parent
    fake.fail('PATCH', '/issues/1', 'timeout')
    first = call(A)
    pending_after_a = snapshot_pending(base)
    # Leave PATCH failing: B must now also keep its own pending identity.
    fake.read_fail = True
    second = call(B)
    pending_after_b = snapshot_pending(base)
    fake._fail = []
    fake.read_fail = True
    third = call(A)
    comments = fake.comments[1]
    duplicate_a = sum(c['body'] == f'任务:01-task\n\n{A}' for c in comments)
    output.append({'id': 'collision-both-partial-overwrites-a', 'entry': 'MCP -> GateService -> FakeTransport',
        'same_pending_file': same_file, 'result_a': A, 'result_b': B,
        'first': first, 'second': second, 'third': third,
        'pending_after_a': pending_after_a, 'pending_after_b': pending_after_b,
        'posts': posts(fake), 'comments': comments, 'a_comment_count': duplicate_a,
        'observed_bug': duplicate_a > 1,
        'expected': 'Keep both pending identities; A retry with failed read-first must not POST.'})
    # Corrupt-shape extension: operation identity survives, published identity does not.
    for fields in [('comment_id',), ('ref',), ('comment_id', 'ref')]:
        base = root / ('missing-' + '-'.join(fields))
        project, fake, call = setup(base)
        fake.fail('PATCH', '/issues/1', 'timeout')
        first = call('same result')
        path = next((base / 'cache' / 'pending-index').rglob('*.json'))
        pending = json.loads(path.read_text())
        for field in fields:
            pending.pop(field)
        path.write_text(json.dumps(pending), encoding='utf-8')
        fake._fail = []
        fake.read_fail = True
        second = call('same result')
        result = second.get('result', {})
        output.append({'id': 'missing-' + '-'.join(fields), 'first': first, 'second': second,
            'posts': posts(fake), 'disclosed_corrupt': '不可读' in result.get('note', ''),
            'missing_published_identity': not result.get('comment_id') or not result.get('ref')})
    # Valid empty, long and Unicode result arguments retain exact request identity.
    for label, body in [('empty', ''), ('unicode', '海鸥 🐦 café e\u0301 中文'), ('long', '长' * 100000)]:
        base = root / label
        project, fake, call = setup(base)
        fake.fail('PATCH', '/issues/1', 'timeout')
        first = call(body)
        fake._fail = []
        fake.read_fail = True
        second = call(body)
        third = call(body)
        a, b, c = (v.get('result', {}) for v in (first, second, third))
        output.append({'id': 'args-' + label, 'body_length': len(body),
            'first_comment_id': a.get('comment_id'), 'second_comment_id': b.get('comment_id'),
            'second_partial': b.get('partial'), 'final_index_updated': c.get('index_updated'),
            'posts': posts(fake), 'pending_remaining': len(snapshot_pending(base)),
            'observed_bug': posts(fake) != 1 or b.get('comment_id') != a.get('comment_id')
                or c.get('index_updated') is not True or bool(snapshot_pending(base))})
path = args.out / 'spec-extra-pending.json'
path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'artifact': str(path), 'summary': [
    {k:v for k,v in row.items() if k in ('id','posts','observed_bug','a_comment_count','disclosed_corrupt','missing_published_identity','body_length')}
    for row in output]}, ensure_ascii=False, indent=2))
