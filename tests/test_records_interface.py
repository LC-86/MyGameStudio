#!/usr/bin/env python3
"""公开接口兼容面。

任务票 11 从 tests/test_records_backend.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。本主题可直接运行:

    python3 -B tests/test_records_interface.py
"""

import sys

from records_backend_support import (
    make_checker, run_theme,
)

import mgs_records  # noqa: E402

FAILURES, check = make_checker()


def test_public_interface_surface_and_factory_parameters() -> None:
    """阶段收口 AC2:公开函数、后端工厂与 transport 构造入口的参数保持。

    重组后的入口相容性不仅看结果,也看调用方实际依赖的调用面:公开读取
    函数的位置/关键字参数、默认值,以及 github_backend 工厂与 GitHub
    transport/后端的构造参数都不新增、不重排、不改名。迁移/交接入口一并
    固定,供现有脚本与导入继续使用。
    """

    import inspect

    import mgs_github

    def params(func) -> list[tuple[str, object, str]]:
        return [(p.name, p.default, p.kind.name)
                for p in inspect.signature(func).parameters.values()]

    default_rel = mgs_records.DEFAULT_CONFIG_REL
    read_entrypoints = ("list_tasks", "task_dependencies",
                        "startable_tasks", "baseline_report", "verify_project")
    for name in read_entrypoints:
        fn = getattr(mgs_records, name)
        found = params(fn)
        check(found[0][0] == "project_root" and found[0][2] == "POSITIONAL_OR_KEYWORD",
              f"{name} 第一位置参数应为 project_root,实际 {found}")
        # config_rel 默认值保持 CONFIG 相对路径;其后为关键字专有的可选注入面
        check(found[1] == ("config_rel", default_rel, "POSITIONAL_OR_KEYWORD"),
              f"{name} 应保留 config_rel 位置参数与默认值,实际 {found[1]}")
        tail = {p[0]: p for p in found[2:]}
        check(set(tail) == {"transport", "api_base", "cache_dir"}
              and all(p[1] is None and p[2] == "KEYWORD_ONLY"
                      for p in tail.values()),
              f"{name} 应保留 transport/api_base/cache_dir 关键字注入参数,"
              f"实际 {found[2:]}")

    # 单任务读取:task_id 位置参数与 config_rel 默认值均保持
    show = params(mgs_records.read_task)
    check(show[1] == ("task_id", inspect.Parameter.empty, "POSITIONAL_OR_KEYWORD")
          and show[2] == ("config_rel", default_rel, "POSITIONAL_OR_KEYWORD"),
          f"read_task 应保留 task_id / config_rel 位置参数,实际 {show}")

    # github_backend 工厂:与读取入口同一注入面
    factory = {p[0]: p for p in params(mgs_records.github_backend)}
    check(list(factory)[:2] == ["project_root", "config_rel"]
          and set(factory) == {"project_root", "config_rel", "transport",
                               "api_base", "cache_dir"},
          f"github_backend 工厂参数应保持,实际 {list(factory)}")

    # GitHub transport / 后端构造入口:迁移与替身注入依赖
    check(params(mgs_github.UrllibTransport.__init__)[:3]
          == [("self", inspect.Parameter.empty, "POSITIONAL_OR_KEYWORD"),
              ("api_base", inspect.Parameter.empty, "POSITIONAL_OR_KEYWORD"),
              ("token", inspect.Parameter.empty, "POSITIONAL_OR_KEYWORD")],
          f"UrllibTransport(api_base, token) 参数应保持,实际 "
          f"{params(mgs_github.UrllibTransport.__init__)}")
    backend = params(mgs_github.GithubBackend.__init__)
    check([p[0] for p in backend] == ["self", "config", "transport", "cache_dir"]
          and backend[3][1] is None,
          f"GithubBackend(config, transport, cache_dir=None) 参数应保持,实际 {backend}")

    # 迁移与交接读取入口:现有脚本的显式调用面
    plan = [p[0] for p in params(mgs_github.plan_backend_switch)]
    check(plan[0] == "project_root" and set(plan) == {"project_root", "target",
                                                      "repo", "transport",
                                                      "cache_dir"},
          f"plan_backend_switch 参数应保持,实际 {plan}")
    handover = params(mgs_github.handover_baseline_check)
    check(handover[0][0] == "project_root"
          and handover[1] == ("config_rel", default_rel, "POSITIONAL_OR_KEYWORD")
          and [p[0] for p in handover[2:]] == ["transport"],
          f"handover_baseline_check 参数应保持,实际 {handover}")

TESTS = (
    test_public_interface_surface_and_factory_parameters,
)

if __name__ == "__main__":
    sys.exit(run_theme("公开接口兼容面", TESTS, FAILURES))
