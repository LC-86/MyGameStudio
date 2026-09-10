import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path('/tmp/mygamestudio-review-5-niculnow')
COPY = ROOT / 'copy'
sys.path.insert(0, str(COPY / 'tests'))
import test_github_backend as gh
import test_runtime_gate as rt

results = []

class OneReadFailure(gh.FakeTransport):
    read_failure_pending = False
    def request(self, method, path, body=None, *, auth=None):
        if self.read_failure_pending and method == 'GET' and '/comments?' in path:
            self.read_failure_pending = False
            self.calls.append((method, path, body))
            raise gh.mgs_github.TransportError('timeout', 'one read-first timeout')
        return super().request(method, path, body, auth=auth)

with tempfile.TemporaryDirectory(prefix='spec-probes-', dir=ROOT) as temp:
    b = Path(temp)
    project = gh.make_github_project(b / 'project')
    svc = rt.GateService(b / 'runtime')
    resources = ['github://github.com/mygamestudio/issue-accept/issues/**', 'src/**']
    svc.init_policy(project, {'producer': resources}, {'production': None})
    inst = svc.create_instance('producer', 'spec-probe', 'production', resources)
    svc._write_json('remote.json', {'github': {'api_base': 'http://unused.invalid',
                   'token_env': 'MGS_TEST_UNUSED', 'cache_dir': str(b / 'cache')}})
    fake = OneReadFailure()
    fake.seed_issue('01-task', 'Existing')
    fake.fail('PATCH', '/issues/1', 'timeout')
    class Facade:
        def remote_record(self, token, action, payload):
            return svc.remote_record(token, action, payload, transport=fake)
    def call():
        out = rt.mcp_gate.handle_tools_call(Facade(), 'mgs_remote',
            {'token': inst.token, 'action': 'append-result',
             'payload': {'identity': '01-task', 'result_markdown': 'same result'}})
        return json.loads(out['content'][0]['text'])
    first = call()
    fake._fail = []
    fake.read_failure_pending = True
    second = call()
    results.append({'id': 'partial-retry-read-first-timeout', 'first': first,
                    'second': second, 'comments': len(fake.comments[1]),
                    'post_count': sum(m == 'POST' and '/comments' in p
                                      for m, p, _ in fake.calls),
                    'observed_bug': len(fake.comments[1]) == 2})

    # Real GateService denials, transported in the retained event schema.
    run_text = (COPY / 'acceptance/18-complete-package-acceptance/run.sh').read_text()
    fn = re.search(r'^mcp_deny_anchor\(\) \{.*?^\}', run_text, re.M | re.S).group()
    def anchored(name, tool, stage, wanted, args, ret):
        ev = ROOT / f'{name}.jsonl'
        ev.write_text(json.dumps({'method': 'item/completed', 'params': {'item': {
            'type': 'mcpToolCall', 'tool': tool, 'status': 'completed',
            'arguments': args, 'result': {'content': [{'type': 'text',
                                                      'text': json.dumps(ret)}]}}}}) + '\n')
        cmd = fn + '\nmcp_deny_anchor ' + ' '.join(map(shlex.quote,
                                            [str(ev), tool, stage, wanted, 'write' if tool == 'mgs_write' else 'update']))
        out = subprocess.run(['bash', '-c', cmd], text=True, capture_output=True)
        results.append({'id': name, 'arguments': args, 'real_gate_result': ret,
                        'expected_anchor': 'MISSING', 'actual_anchor': out.stdout.strip(),
                        'observed_bug': out.stdout.strip() == 'OK'})
    wrong_path = '/tmp/mgs18-evil-link.md.bak'
    wrong_path_result = svc.write(inst.token, wrong_path, 'X', expected_sha256='absent')
    anchored('wrong-target-prefix', 'mgs_write', 'path', '/tmp/mgs18-evil-link.md',
             {'path': wrong_path}, wrong_path_result)
    limited = svc.create_instance('producer', 'limited', 'production',
        ['github://github.com/mygamestudio/issue-accept/issues/04-fog-layer/**'])
    read_result = svc.remote_record(limited.token, 'read',
                                  {'identity': '01-harbor-timer'}, transport=fake)
    anchored('read-denial-as-update-proof', 'mgs_remote', 'task_grant', '01-harbor-timer',
             {'action': 'read', 'payload': {'identity': '01-harbor-timer'}}, read_result)
    append_result = svc.remote_record(limited.token, 'append-result',
        {'identity': '01-harbor-timer', 'result_markdown': 'wrong operation'}, transport=fake)
    anchored('append-denial-as-update-proof', 'mgs_remote', 'task_grant', '01-harbor-timer',
             {'action': 'append-result', 'payload': {'identity': '01-harbor-timer'}},
             append_result)

(ROOT / 'spec-probes.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
print(json.dumps([{'id': x['id'], 'observed_bug': x['observed_bug'],
                   'comments': x.get('comments'), 'actual_anchor': x.get('actual_anchor')}
                  for x in results], ensure_ascii=False, indent=2))
