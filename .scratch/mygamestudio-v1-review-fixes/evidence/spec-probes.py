#!/usr/bin/env python3
"""Read-only review probes. All mutations target disposable /tmp fixtures.

No model calls, credentials, or external requests are used. The repository's
in-memory FakeTransport is imported with its test runner disabled.
"""
import json
import runpy
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path('/Users/cuilei/MyOS/01_Projects/plugins/MyGameStudio')
ns = runpy.run_path(str(REPO / 'tests/test_github_backend.py'), run_name='review_fixture')
Fake = ns['FakeTransport']
make = ns['make_github_project']
github = ns['mgs_github']
records = ns['mgs_records']


def emit(name, payload):
    print(json.dumps({'probe': name, **payload}, ensure_ascii=False))


with tempfile.TemporaryDirectory(prefix='mgs-spec-probe-') as tmp:
    base = Path(tmp)
    root = make(base / 'project')
    fake = Fake()
    fake.seed_issue('01-alpha', '甲')
    backend = github.GithubBackend(records.load_config(root), fake, base / 'cache')
    fake.drop('POST', '/comments')
    fake.fail('GET', '/comments', 'timeout')
    try:
        outcome = backend.append_result('01-alpha', '交付证据')
    except Exception as exc:
        outcome = {'error': str(exc)}
    posts = [c for c in fake.calls if c[0] == 'POST' and '/comments' in c[1]]
    assert len(fake.comments[1]) == len(posts) == 2
    assert fake.comments[1][0]['body'] == fake.comments[1][1]['body']
    emit('append_result_uncertain_readback', {
        'outcome': outcome, 'comment_count': len(fake.comments[1]),
        'comment_posts': len(posts), 'duplicate_comment': True})

with tempfile.TemporaryDirectory(prefix='mgs-spec-probe-') as tmp:
    base = Path(tmp)
    root = make(base / 'project')
    config = records.load_config(root)
    old = {**config, 'repo': {'host': 'github.com', 'owner': 'old-owner',
                             'repo': 'private-repo'},
           'external': 'github.com/old-owner/private-repo:issues-write(已授权旧仓库)'}
    offline = Fake()
    offline.offline()
    previous = github.GithubBackend(old, offline, base / 'shared-cache')
    previous.create_task('09-private', '仅旧仓库的任务', {'当前目标': '旧仓库材料'})
    fake = Fake()
    current = github.GithubBackend(config, fake, base / 'shared-cache')
    outcome = current.publish_drafts()
    published = next((base / 'shared-cache/drafts/published').glob('*.json'))
    saved = json.loads(published.read_text())
    writes = [c[1] for c in fake.calls if c[0] == 'POST']
    assert saved['repo'] == 'github.com/old-owner/private-repo'
    assert writes == ['/repos/mygamestudio/issue-accept/issues']
    assert outcome['published_count'] == 1
    emit('draft_cross_repo', {'saved_repo': saved['repo'],
                             'current_repo': config['repo'],
                             'published_count': outcome['published_count'],
                             'actual_write_paths': writes})

with tempfile.TemporaryDirectory(prefix='mgs-spec-probe-') as tmp:
    base = Path(tmp)
    root = make(base / 'project')
    fake = Fake()
    fake.seed_issue('01-alpha', '甲')
    plan = github.plan_backend_switch(root, target='local-markdown', transport=fake)
    plan_path = base / 'plan.json'
    plan_path.write_text(json.dumps(plan))
    outcome = github.apply_backend_switch(plan_path, confirmed=True,
        emit_dir=base / 'emit', project_root=root, transport=fake)
    config = records.load_config(base / 'emit', 'CONFIG.md')
    tasks = records.list_tasks(base / 'emit', 'CONFIG.md')
    actual = [str(p.relative_to(base / 'emit')) for p in (base / 'emit').rglob('task.md')]
    assert outcome['created'] == 1 and tasks == []
    assert config['task_root'] == 'github.com/mygamestudio/issue-accept'
    assert actual == ['docs/mygamestudio/work/01-alpha/task.md']
    emit('github_to_local', {'created': outcome['created'],
        'config_task_root': config['task_root'], 'actual_task_files': actual,
        'unified_list_tasks': tasks,
        'returned_emit_dir_exists': Path(outcome['emit_dir']).exists()})

with tempfile.TemporaryDirectory(prefix='mgs-spec-probe-') as tmp:
    root = make(Path(tmp) / 'project')
    config_path = root / 'docs/mygamestudio/CONFIG.md'
    config_path.write_text(config_path.read_text() + '\n已发布基线引用:'
        'GAME_DESIGN.md=https://example.invalid/design,'
        'PROJECT.md=https://example.invalid/goal,'
        'TECH_DESIGN.md=https://example.invalid/tech\n')
    fake = Fake()
    fake.offline()
    outcome = github.handover_baseline_check(root, transport=fake)
    assert outcome['ok'] is True and len(fake.calls) == 0
    emit('handover_unreachable_ref', {'ok': outcome['ok'],
        'remote_reachable': [doc['remote_reachable'] for doc in outcome['docs']],
        'network_calls': len(fake.calls)})

with tempfile.TemporaryDirectory(prefix='mgs-spec-probe-') as tmp:
    root = make(Path(tmp) / 'project')
    fake = Fake()
    fake.seed_issue('01-alpha', '甲')
    cache = Path(tmp) / 'cache'
    records.list_tasks(root, transport=fake, cache_dir=cache)
    fake.offline()
    outcome = records.startable_tasks(root, transport=fake, cache_dir=cache)
    assert [task['identity'] for task in outcome['startable']] == ['01-alpha']
    assert not any(key in outcome for key in ('cached', 'cached_read', 'fetched_at', 'source'))
    emit('ready_cached_metadata', outcome)

with tempfile.TemporaryDirectory(prefix='mgs-spec-probe-') as tmp:
    root = make(Path(tmp) / 'project')
    fake = Fake()
    fake.seed_issue('01-alpha', '甲')
    cache = Path(tmp) / 'cache'
    backend = github.GithubBackend(records.load_config(root), fake, cache)
    backend.fetch_tasks()
    fake.offline()
    # Freeze only the filename timestamp to make the same-second case stable.
    real_datetime = github._dt.datetime
    class FixedDatetime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 9, 1, 2, 3, tzinfo=tz)
    github._dt.datetime = FixedDatetime
    try:
        one = backend.append_result('01-alpha', '证据一')
        two = backend.append_result('01-alpha', '证据二')
    finally:
        github._dt.datetime = real_datetime
    paths = list((cache / 'drafts').glob('*.json'))
    remaining = [json.loads(path.read_text())['args']['result_markdown'] for path in paths]
    assert one['draft'] == two['draft'] and remaining == ['证据二']
    emit('draft_collision', {'same_path': one['draft'] == two['draft'],
        'draft_count': len(paths), 'remaining_result': remaining})

emit('summary', {'reproduced_findings': 6, 'external_network_calls': 0,
                 'repository_files_modified': 0})
