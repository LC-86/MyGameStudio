#!/usr/bin/env python3
"""最小插件包的确定性完整性检查(任务票 01 建立,票 02-04 扩展,票 10 分主题)。

总入口:本文件聚合票 10 从巨型检查拆出的全部行为主题,仍返回完整的通过或
失败结果,运行方式不变:

    python3 -B tests/test_plugin_package.py

各主题各自可独立运行(见下),失败能定位到具体职责;事件判据经票 08/09 的
同一 interface(acceptance/18 的 evidence_judgement.py),重复事件构造改为
具名案例数据(tests/plugin_package_fixtures.json)。

覆盖:包完整性(清单/入口/模板/引用)、来源与许可、交付物一致性与可复现
构建、业务 Skill 说明、样例与验收注入夹具、凭据脱敏与泄漏扫描、事件判据。

接缝说明:本脚本只覆盖可静态核实的包内约定与离线事件回放。真实安装、显式
调用与结果回读由 acceptance/<票号>/ 的隔离验收流程覆盖,本脚本不替代。
"""

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# 行为主题(文件,标题,入口函数名):聚合顺序即原总入口的历史顺序。
THEMES = (
    ("test_package_manifest.py",
     "包完整性(清单/入口/模板/引用)",
     ("test_manifest", "test_explicit_skills", "test_mcp_gate_config",
      "test_records_backend_module", "test_templates_and_game_init",
      "test_internal_methods_closure", "test_internal_references_resolve",
      "test_config_template_adaptation")),
    ("test_package_provenance.py",
     "来源/许可/指纹",
     ("test_internal_material_provenance", "test_no_dev_machine_paths",
      "test_provenance_version_consistency")),
    ("test_package_fixtures_samples.py",
     "样例夹具",
     ("test_sample_fixtures", "test_role_scope_demo_fixture",
      "test_stardust_dash_fixture", "test_nebula_drift_fixture",
      "test_tide_pool_fixture", "test_gear_city_fixture")),
    ("test_package_skill_content_design.py",
     "业务 Skill 说明(设计/原型/制作)",
     ("test_design_skills_content", "test_prototype_skill_content",
      "test_game_plan_skill_content", "test_production_skills_content",
      "test_game_art_skill_content", "test_game_audio_skill_content")),
    ("test_package_fixtures_acceptance_a.py",
     "验收注入夹具(07-12)",
     ("test_accept07_fixture", "test_accept08_fixture", "test_accept09_fixture",
      "test_accept10_fixture", "test_accept11_fixture", "test_accept12_fixture")),
    ("test_package_skill_content_delivery.py",
     "业务 Skill 说明(构建/评审/试玩/统筹)",
     ("test_game_build_skill_content", "test_game_review_skill_content",
      "test_game_playtest_skill_content", "test_goal_change_skills_content",
      "test_producer_loop_skills_content", "test_github_issue_workflow_content")),
    ("test_package_fixtures_acceptance_b.py",
     "验收注入夹具(13-16/18)",
     ("test_accept13_fixture", "test_accept14_fixture", "test_accept15_fixture",
      "test_accept16_fixture", "test_accept18_fixture")),
    ("test_package_dist.py",
     "交付物一致性与可复现构建",
     ("test_dist_package_consistent", "test_dist_rebuild_byte_reproducible")),
    ("test_package_secret_scan.py",
     "凭据脱敏与泄漏扫描",
     ("test_accept16_sanitize_covers_unenumerated_tokens",
      "test_accept16_secret_scan_gate", "test_accept18_leak_checks_mechanized")),
    ("test_package_event_judgement.py",
     "事件判据(工具拒绝/curl 直连)",
     ("test_event_judgement_shell_adapter", "test_event_judgement_core_sp6",
      "test_event_judgement_sp8", "test_event_judgement_sp12_sp13",
      "test_event_judgement_sp15_sp16", "test_event_judgement_sp18_sp19",
      "test_event_judgement_sp20_sp23", "test_event_judgement_sp24_sp26",
      "test_event_judgement_sp27_sp29", "test_event_judgement_sp30",
      "test_event_judgement_input_consistency",
      "test_event_judgement_retained_evidence",
      "test_event_judgement_legacy_branches_red",
      "test_event_judgement_runsh_wiring")),
)


def _load_module(filename: str):
    path = REPO_ROOT / "tests" / filename
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures: list[str] = []
    for filename, title, funcs in THEMES:
        module = _load_module(filename)
        for name in funcs:
            getattr(module, name)()
        theme_failures = list(module.FAILURES)
        if theme_failures:
            failures.append(f"[{title}]")
            failures.extend(theme_failures)
    if failures:
        print(f"FAIL ({len(failures)} 行):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OK: 最小插件包静态完整性检查全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
