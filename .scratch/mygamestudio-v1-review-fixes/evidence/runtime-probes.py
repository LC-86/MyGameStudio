#!/usr/bin/env python3
"""Reproduce review findings using only disposable local fixtures."""
import hashlib
import json
import runpy
import stat
import sys
import tempfile
import threading
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
sys.path.insert(0, str(REPO / 'plugin/runtime'))
from mgs_runtime import GateService
import mcp_gate


def emit(name, **payload):
    print(json.dumps({'probe': name, **payload}, ensure_ascii=False))


with tempfile.TemporaryDirectory(prefix='mgs-runtime-review-', dir='/tmp') as tmp:
    root = Path(tmp)
    project = root / 'project'
    (project / 'src').mkdir(parents=True)
    writer = GateService(root / 'runtime')
    admin = GateService(root / 'runtime')
    writer.init_policy(project, {'implement': ['src/**']}, {'production': None})
    instance = writer.create_instance('implement', 'probe', 'production', ['src/**'])
    original = writer._resolve_instance
    checked = threading.Event()
    released = threading.Event()
    result = {}

    def pause_after_identity(token):
        resolved = original(token)
        checked.set()
        assert released.wait(5)
        return resolved

    writer._resolve_instance = pause_after_identity

    def run():
        result['write'] = writer.write(instance.token, 'src/old-token.txt', 'STALE')

    thread = threading.Thread(target=run)
    thread.start()
    assert checked.wait(5)
    revoke = admin.release_instance(instance.instance_id)
    released.set()
    thread.join(5)
    assert revoke['found'] and admin._resolve_instance(instance.token)[0] is None
    assert result['write']['decision'] == 'allow'
    assert (project / 'src/old-token.txt').read_text() == 'STALE'
    emit('revoked_inflight_write', release_confirmed=True,
         current_identity_valid=False, resumed_write='allow', target='STALE')

with tempfile.TemporaryDirectory(prefix='mgs-runtime-review-', dir='/tmp') as tmp:
    root = Path(tmp)
    project = root / 'project'
    (project / 'src').mkdir(parents=True)
    service = GateService(root / 'runtime')
    service.init_policy(project, {'implement': ['src/**']},
                        {'production': None, 'prototype': ['prototypes/**']})
    instance = service.create_instance('implement', 'prototype-probe',
                                       'prototype', ['src/**'])
    before = service.write(instance.token, 'src/escaped.txt', 'BYPASS')
    policy = json.loads((service.runtime_root / 'policy.json').read_text())
    del policy['purposes']['prototype']
    (service.runtime_root / 'policy.json').write_text(json.dumps(policy))
    after = service.write(instance.token, 'src/escaped.txt', 'BYPASS')
    assert before['rule_stage'] == 'purpose' and before['decision'] == 'deny'
    assert after['decision'] == 'allow'
    emit('missing_purpose_policy', before='deny', before_stage='purpose',
         after='allow', target=(project / 'src/escaped.txt').read_text())

with tempfile.TemporaryDirectory(prefix='mgs-runtime-review-', dir='/tmp') as tmp:
    root = Path(tmp)
    project = root / 'project'
    (project / 'src').mkdir(parents=True)
    service = GateService(root / 'runtime')
    service.init_policy(project, {'implement': ['src/**']}, {'production': None})
    instance = service.create_instance('implement', 'mode-probe', 'production', ['src/**'])
    for name, mode in [('run.sh', 0o755), ('private.txt', 0o600)]:
        path = project / 'src' / name
        path.write_text('old')
        path.chmod(mode)
        result = service.write(instance.token, 'src/' + name, 'new',
                               expected_sha256=hashlib.sha256(b'old').hexdigest())
        actual = stat.S_IMODE(path.stat().st_mode)
        assert actual == 0o644 and result['decision'] == 'allow'
        emit('existing_file_mode', file=name, before=oct(mode), after=oct(actual))

fixture = runpy.run_path(str(REPO / 'tests/test_github_backend.py'), run_name='review_fixture')
with tempfile.TemporaryDirectory(prefix='mgs-runtime-review-', dir='/tmp') as tmp:
    root = Path(tmp)
    project = fixture['make_github_project'](root / 'project')
    service = GateService(root / 'runtime')
    resources = ['github://github.com/mygamestudio/issue-accept/issues/**']
    service.init_policy(project, {'producer': resources}, {'production': None})
    instance = service.create_instance('producer', 'audit-probe', 'production', resources)
    service._write_json('remote.json', {'github': {
        'api_base': 'http://unused.invalid', 'token_env': 'MGS_TEST_UNUSED',
        'cache_dir': str(root / 'cache')}})
    transport = fixture['FakeTransport']()
    transport.seed_issue('01-task', 'Existing')
    audit = service.runtime_root / 'audit/audit.jsonl'
    audit.unlink()
    audit.mkdir()

    class Facade:
        def remote_record(self, token, action, payload):
            return service.remote_record(token, action, payload, transport=transport)

    response = mcp_gate.handle_tools_call(Facade(), 'mgs_remote', {
        'token': instance.token, 'action': 'append-result',
        'payload': {'identity': '01-task', 'result_markdown': 'Verified local fixture'}})
    body = json.loads(response['content'][0]['text'])
    assert body['decision'] == 'deny' and len(transport.comments[1]) == 1
    emit('remote_audit_failure', mcp_decision=body['decision'],
         mcp_stage=body['rule_stage'], actual_remote_comments=len(transport.comments[1]),
         audit_file_exists=audit.is_file(), external_network_requests=0)

emit('summary', reproduced_findings=4, repository_files_modified=0,
     external_network_requests=0, model_calls=0)
