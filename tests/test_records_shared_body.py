#!/usr/bin/env python3
"""共享正文、来源归属与错误身份。

任务票 11 从 tests/test_records_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_records_shared_body.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

from records_backend_support import (
    RECORDS_DIR, SAMPLE, _imported_modules, make_checker, make_project,
    run_theme,
)

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_record_model_shared_body_and_error_identity() -> None:
    """票 02:共同正文规则与错误类型由中性记录 module 提供、不反向依赖查询。

    覆盖:本地读取直接使用共享正文解析;空字段、未知小节与字段分隔保持可见;
    畸形任务不被提前过滤,仍进入核验;RecordsError 与共享 module 同一身份。
    """

    import mgs_record_model

    check(mgs_records.RecordsError is mgs_record_model.RecordsError,
          "mgs_records.RecordsError 应与共享记录 module 同一身份")
    for name in ("parse_task_body", "_sections", "_bullets", "_field",
                 "task_core_problems", "dependency_problems",
                 "label_mapping_checks", "docmap_checks", "check_item"):
        check(hasattr(mgs_record_model, name),
              f"共享记录 module 应提供 {name}")
    # 共同记录语义不反向依赖查询/命令行:model 不导入 mgs_records / mgs_github
    model_source = Path(mgs_record_model.__file__).read_text(encoding="utf-8")
    check("import mgs_records" not in model_source
          and "import mgs_github" not in model_source,
          "共享记录 module 不得反向依赖查询或 GitHub adapter")

    body = (
        "# 畸形任务\n\n"
        "任务身份:。当前分流:ready-for-agent。进度:待执行;负责人:张三。\n\n"
        "## 工作请求\n\n"
        "- 当前目标:演示目标\n"
        "- 完成标准:\n"
        "- 执行责任:Agent（制作实现）\n\n"
        "## 未知小节\n\n"
        "未知内容仍需保留\n\n"
        "## 结果索引\n\n"
        "(暂无)\n"
    )
    parsed = mgs_record_model.parse_task_body(body)
    check(parsed["identity"] == "", f"空身份字段应保持为空,实际 {parsed['identity']!r}")
    check(parsed["progress"] == "待执行",
          f"字段分隔(分号)应正确截断,实际 {parsed['progress']!r}")
    check(parsed["request"].get("完成标准") == "",
          "空值字段应保留键且值为空")
    check(parsed["request"].get("执行责任") == "Agent（制作实现）",
          "全角冒号应作为字段分隔")
    check(parsed["sections"].get("未知小节") is True,
          "未知小节应保留在 sections 中")
    check(parsed["result_index_text"].strip() == "(暂无)",
          "结果索引原文应保留")

    with tempfile.TemporaryDirectory() as tmp:
        root = make_project(Path(tmp), extra_task=False)
        task_dir = root / "docs" / "mygamestudio" / "work" / "05-malformed"
        task_dir.mkdir(parents=True)
        (task_dir / "task.md").write_text(body, encoding="utf-8")
        tasks = mgs_records.list_tasks(root)
        check([t["directory"] for t in tasks] == ["05-malformed"],
              f"畸形任务应仍被列出而非提前过滤,实际 {tasks}")
        local = mgs_records.read_task(root, "05-malformed")
        check(local["identity"] == "" and local["directory"] == "05-malformed",
              "本地读取应同时保留空身份与目录专有字段")
        check(local["request"].get("完成标准") == ""
              and local["sections"].get("未知小节") is True,
              "本地读取应保持空字段与未知小节可见")
        report = mgs_records.verify_project(root)
        tasks_check = next(c for c in report["checks"] if c["name"] == "tasks-valid")
        check(tasks_check["ok"] is False
              and "正文身份缺失或不合规" in tasks_check["detail"],
              f"畸形任务应进入核验并报告身份问题:{tasks_check['detail']}")


def test_dependency_direction_static() -> None:
    """依赖方向:分层自下而上,任一层不反向依赖其上各层。

    用 AST 扫描全部 import(含函数内),证明方向靠职责归属实现,而不是
    延迟导入。分层(model/source 中性共同语义 → transport 最底层接缝 →
    pending-index 登记存储与归属 → publication 发布恢复 → github 业务
    适配器)固定为对称的负向断言:传输不得导入发布恢复/登记存储/适配器/
    查询组织,登记存储不得导入发布恢复/适配器/查询组织,发布恢复不得
    导入适配器/查询组织。
    """

    model = _imported_modules(RECORDS_DIR / "mgs_record_model.py")
    source = _imported_modules(RECORDS_DIR / "mgs_record_source.py")
    github = _imported_modules(RECORDS_DIR / "mgs_github.py")
    records = _imported_modules(RECORDS_DIR / "mgs_records.py")
    transport = _imported_modules(RECORDS_DIR / "mgs_github_transport.py")
    pending_index = _imported_modules(RECORDS_DIR / "mgs_pending_index.py")
    publication = _imported_modules(RECORDS_DIR / "mgs_result_publication.py")

    for banned in ("mgs_records", "mgs_github", "mgs_record_source"):
        check(banned not in model,
              f"mgs_record_model 不得依赖 {banned}(含延迟导入),实际 {sorted(model)}")
    for banned in ("mgs_records", "mgs_github"):
        check(banned not in source,
              f"mgs_record_source 不得依赖 {banned}(含延迟导入),实际 {sorted(source)}")
    check("mgs_records" not in github,
          f"mgs_github 不得反向调用查询组织 mgs_records,实际 {sorted(github)}")
    # 票 18:传输/错误接缝是最底层,发布恢复建在其上,适配器在最上;任一层
    # 不得回指其上各层(对称负向断言)。adapter 实际依赖发布恢复 module。
    for banned in ("mgs_result_publication", "mgs_pending_index",
                   "mgs_github", "mgs_records"):
        check(banned not in transport,
              f"mgs_github_transport(最底层接缝)不得依赖 {banned},"
              f"实际 {sorted(transport)}")
    # 票 19:登记存储与归属是独立恢复职责,建在传输接缝之上、发布恢复之下;
    # 不反向依赖发布恢复/适配器/查询组织。
    for banned in ("mgs_result_publication", "mgs_github", "mgs_records"):
        check(banned not in pending_index,
              f"mgs_pending_index(登记存储与归属)不得依赖 {banned},"
              f"实际 {sorted(pending_index)}")
    for banned in ("mgs_github", "mgs_records"):
        check(banned not in publication,
              f"mgs_result_publication 不得依赖 {banned},实际 {sorted(publication)}")
    check("mgs_result_publication" in github,
          f"mgs_github 应依赖发布恢复 module(真实接入),实际 {sorted(github)}")
    check("mgs_pending_index" in publication,
          "发布恢复应在真实追加路径上使用登记存储与归属 module"
          f"(单一恢复职责,非另建助手),实际 {sorted(publication)}")
    check("mgs_github_transport" in github
          and "mgs_github_transport" in publication
          and "mgs_github_transport" in pending_index,
          "发布恢复、登记存储与 adapter 应共用传输/错误接缝 mgs_github_transport,"
          f"实际 github={sorted(github)} publication={sorted(publication)} "
          f"pending_index={sorted(pending_index)}")
    # 正向:查询组织与 adapter 都依赖来源 module 与共同语义
    check("mgs_record_source" in records,
          f"mgs_records 应依赖来源 module,实际 {sorted(records)}")
    check("mgs_record_source" in github,
          f"mgs_github 应直接依赖来源 module,实际 {sorted(github)}")


def test_source_shared_with_query_and_import_orders() -> None:
    """两种导入顺序下共同语义/来源同一身份、无循环导入错误(READ-10/13)。

    来源先导入与查询先导入都必须成功,且配置读取是同一实现。
    """

    records_dir = str(RECORDS_DIR)
    probe = (
        "import sys\n"
        f"sys.path.insert(0, {records_dir!r})\n"
        "{first}\n"
        "{second}\n"
        "import mgs_record_source, mgs_records, mgs_record_model\n"
        "assert mgs_records.load_config is mgs_record_source.load_config\n"
        "assert mgs_records.RecordsError is mgs_record_model.RecordsError\n"
        "assert mgs_record_source.RecordsError is mgs_record_model.RecordsError\n"
        "print('OK')\n"
    )
    for label, first, second in (
            ("source-first", "import mgs_record_source", "import mgs_records"),
            ("records-first", "import mgs_records", "import mgs_record_source")):
        result = subprocess.run(
            [sys.executable, "-B", "-c", probe.format(first=first, second=second)],
            capture_output=True, text=True)
        check(result.returncode == 0 and "OK" in result.stdout,
              f"{label} 导入顺序来源身份应单一且无循环导入:{result.stderr[-300:]}")


def test_loaded_config_local_read_is_same_source() -> None:
    """已加载配置的本地读取经现有入口可用,且与正式入口同一结果(AC1/AC5)。

    - ``load_config_document`` 由同一 CONFIG 原文返回 (config, text);
    - 本地 adapter 接收本次已加载配置,不再重读 CONFIG;
    - 经现有公开入口 list_tasks/read_task 得到的结果与直接来源读取一致。
    """

    import mgs_record_source

    config, text = mgs_record_source.load_config_document(SAMPLE)
    check(config == mgs_records.load_config(SAMPLE),
          "同一 CONFIG 原文应解析出与正式入口相同的配置字段")
    check(text and "- 后端:local-markdown" in text,
          "同一原文应随配置返回,供本次调用内派生执行条件")

    # 已加载配置的本地读取不重读 CONFIG:审计钩子统计 open 调用
    import sys as _sys
    opened: list[str] = []

    def _hook(event: str, args: tuple) -> None:
        if event == "open" and args and isinstance(args[0], str):
            opened.append(args[0])

    _sys.addaudithook(_hook)
    tasks = mgs_record_source.local_list_tasks(SAMPLE, config)
    task = mgs_record_source.local_read_task(SAMPLE, config, "02-coin-magnet")
    config_reads = [p for p in opened if p.endswith("CONFIG.md")]
    check(config_reads == [],
          f"接收已加载配置的本地读取不得再读 CONFIG,实际打开 {config_reads}")

    # 与现有公开入口的结果一致
    check([t["identity"] for t in tasks]
          == [t["identity"] for t in mgs_records.list_tasks(SAMPLE)],
          "已加载配置的来源列举应与现有入口 list_tasks 一致")
    check(task == mgs_records.read_task(SAMPLE, "02-coin-magnet"),
          "已加载配置的来源读取应与现有入口 read_task 一致")

TESTS = (
    test_record_model_shared_body_and_error_identity,
    test_dependency_direction_static,
    test_source_shared_with_query_and_import_orders,
    test_loaded_config_local_read_is_same_source,
)

if __name__ == "__main__":
    sys.exit(run_theme("共享正文、来源归属与错误身份", TESTS, FAILURES))
