# 票 10 原案例 → 新位置映射(包完整性检查拆分)

原 `tests/test_plugin_package.py`(4100 行,51 个顶层函数,含 1 个 1550 行
巨型函数)按真实行为主题拆为 9 个可独立运行的主题文件 + 1 个事件判据
文件 + 1 个共享支撑;原总入口保留为聚合器。

## 一、原顶层函数 → 主题文件

| 原函数 | 原行数 | 新位置 |
| --- | --- | --- |
| `check` | 3 | `tests/plugin_package_support.py(make_checker)` |
| `sha256` | 2 | `tests/plugin_package_support.py` |
| `load_fingerprints` | 7 | `tests/test_package_provenance.py` |
| `test_manifest` | 25 | `test_package_manifest.py(包完整性(清单/入口/模板/引用))` |
| `test_explicit_skills` | 45 | `test_package_manifest.py(包完整性(清单/入口/模板/引用))` |
| `test_mcp_gate_config` | 22 | `test_package_manifest.py(包完整性(清单/入口/模板/引用))` |
| `test_internal_material_provenance` | 35 | `test_package_provenance.py(来源/许可/指纹)` |
| `test_no_dev_machine_paths` | 8 | `test_package_provenance.py(来源/许可/指纹)` |
| `test_sample_fixtures` | 48 | `test_package_fixtures_samples.py(样例夹具)` |
| `test_role_scope_demo_fixture` | 28 | `test_package_fixtures_samples.py(样例夹具)` |
| `test_records_backend_module` | 22 | `test_package_manifest.py(包完整性(清单/入口/模板/引用))` |
| `test_templates_and_game_init` | 46 | `test_package_manifest.py(包完整性(清单/入口/模板/引用))` |
| `test_stardust_dash_fixture` | 5 | `test_package_fixtures_samples.py(样例夹具)` |
| `test_nebula_drift_fixture` | 39 | `test_package_fixtures_samples.py(样例夹具)` |
| `test_design_skills_content` | 56 | `test_package_skill_content_design.py(业务 Skill 说明(设计/原型/制作))` |
| `test_internal_methods_closure` | 25 | `test_package_manifest.py(包完整性(清单/入口/模板/引用))` |
| `_check_task_record` | 12 | `tests/test_package_fixtures_samples.py` |
| `test_tide_pool_fixture` | 68 | `test_package_fixtures_samples.py(样例夹具)` |
| `test_gear_city_fixture` | 35 | `test_package_fixtures_samples.py(样例夹具)` |
| `test_prototype_skill_content` | 35 | `test_package_skill_content_design.py(业务 Skill 说明(设计/原型/制作))` |
| `test_accept07_fixture` | 74 | `test_package_fixtures_acceptance_a.py(验收注入夹具(07-12))` |
| `test_game_plan_skill_content` | 41 | `test_package_skill_content_design.py(业务 Skill 说明(设计/原型/制作))` |
| `test_accept08_fixture` | 53 | `test_package_fixtures_acceptance_a.py(验收注入夹具(07-12))` |
| `test_production_skills_content` | 74 | `test_package_skill_content_design.py(业务 Skill 说明(设计/原型/制作))` |
| `test_accept09_fixture` | 50 | `test_package_fixtures_acceptance_a.py(验收注入夹具(07-12))` |
| `test_game_art_skill_content` | 48 | `test_package_skill_content_design.py(业务 Skill 说明(设计/原型/制作))` |
| `test_accept10_fixture` | 47 | `test_package_fixtures_acceptance_a.py(验收注入夹具(07-12))` |
| `test_game_audio_skill_content` | 56 | `test_package_skill_content_design.py(业务 Skill 说明(设计/原型/制作))` |
| `test_accept11_fixture` | 71 | `test_package_fixtures_acceptance_a.py(验收注入夹具(07-12))` |
| `test_game_build_skill_content` | 62 | `test_package_skill_content_delivery.py(业务 Skill 说明(构建/评审/试玩/统筹))` |
| `test_accept12_fixture` | 95 | `test_package_fixtures_acceptance_a.py(验收注入夹具(07-12))` |
| `test_game_review_skill_content` | 55 | `test_package_skill_content_delivery.py(业务 Skill 说明(构建/评审/试玩/统筹))` |
| `test_accept13_fixture` | 87 | `test_package_fixtures_acceptance_b.py(验收注入夹具(13-16/18))` |
| `test_game_playtest_skill_content` | 56 | `test_package_skill_content_delivery.py(业务 Skill 说明(构建/评审/试玩/统筹))` |
| `test_accept14_fixture` | 56 | `test_package_fixtures_acceptance_b.py(验收注入夹具(13-16/18))` |
| `test_goal_change_skills_content` | 62 | `test_package_skill_content_delivery.py(业务 Skill 说明(构建/评审/试玩/统筹))` |
| `test_accept15_fixture` | 30 | `test_package_fixtures_acceptance_b.py(验收注入夹具(13-16/18))` |
| `test_producer_loop_skills_content` | 35 | `test_package_skill_content_delivery.py(业务 Skill 说明(构建/评审/试玩/统筹))` |
| `test_accept16_fixture` | 84 | `test_package_fixtures_acceptance_b.py(验收注入夹具(13-16/18))` |
| `test_github_issue_workflow_content` | 62 | `test_package_skill_content_delivery.py(业务 Skill 说明(构建/评审/试玩/统筹))` |
| `test_provenance_version_consistency` | 18 | `test_package_provenance.py(来源/许可/指纹)` |
| `test_config_template_adaptation` | 35 | `test_package_manifest.py(包完整性(清单/入口/模板/引用))` |
| `test_internal_references_resolve` | 21 | `test_package_manifest.py(包完整性(清单/入口/模板/引用))` |
| `test_accept18_fixture` | 41 | `test_package_fixtures_acceptance_b.py(验收注入夹具(13-16/18))` |
| `test_dist_package_consistent` | 57 | `test_package_dist.py(交付物一致性与可复现构建)` |
| `test_dist_rebuild_byte_reproducible` | 71 | `test_package_dist.py(交付物一致性与可复现构建)` |
| `test_accept16_sanitize_covers_unenumerated_tokens` | 59 | `test_package_secret_scan.py(凭据脱敏与泄漏扫描)` |
| `test_accept16_secret_scan_gate` | 153 | `test_package_secret_scan.py(凭据脱敏与泄漏扫描)` |
| `test_accept18_leak_checks_mechanized` | 148 | `test_package_secret_scan.py(凭据脱敏与泄漏扫描)` |
| `test_accept18_probe_checks_anchored_to_events` | 1550 | `tests/test_package_event_judgement.py(按 SP 分组)` |
| `main` | 54 | `tests/test_plugin_package.py(聚合入口)` |

事件判据巨型函数按复审轮次拆为 SP 分组(全部经同一 interface):

| SP 分组 | 案例数 | 新入口 |
| --- | --- | --- |
| 现场接入对照 | 4 | `test_event_judgement_shell_adapter` |
| 核心区分 | 5 | `test_event_judgement_core_sp6` |
| review3 SP-8/9 | 6 | `test_event_judgement_sp8` |
| review4 SP-12/13 | 10 | `test_event_judgement_sp12_sp13` |
| review5 SP-15/16 | 12 | `test_event_judgement_sp15_sp16` |
| review6 SP-18/19 | 5 | `test_event_judgement_sp18_sp19` |
| review7 SP-20~23 | 16 | `test_event_judgement_sp20_sp23` |
| review8 SP-24~26 | 17 | `test_event_judgement_sp24_sp26` |
| review9 SP-27~29 | 22 | `test_event_judgement_sp27_sp29` |
| review10 SP-30 | 10 | `test_event_judgement_sp30` |
| 留存证据重跑 | 10 | `test_event_judgement_retained_evidence` |
| 双输入形态一致 | 1 | `test_event_judgement_input_consistency` |
| 旧词串分支假绿(红) | 2 | `test_event_judgement_legacy_branches_red` |
| run.sh 接线形态 | 14 | `test_event_judgement_runsh_wiring` |

## 二、案例计数口径

- 合成事件夹具:98 个具名事件(`events`),重建后与原内联夹具逐字节一致。
- 事件判据案例:103 条(去留存证据),另 4 条 Shell 现场接入、10 条留存证据重跑。
- 原总入口 check() 消息数:1630;新聚合入口:1631(0 丢失,+1 为新增缺失文件守卫)。
- 原 46 个 test_* 函数全部保留身份;仅位置改变,判定含义不变。
