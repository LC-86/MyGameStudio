#!/usr/bin/env python3
"""构建运行、评审、试玩、目标变更与统筹闭环入口的依据与纪律。

任务票 10 从 tests/test_plugin_package.py 按真实行为主题拆出;检查含义与原
案例保持一致,仅重组位置。原总入口仍聚合本主题。各主题文件可直接运行:

    python3 -B tests/test_package_skill_content_delivery.py
"""

import json
import re
import sys
from plugin_package_support import (PLUGIN_ROOT, make_checker, run_theme)

FAILURES, check = make_checker()

def test_game_status_skill_content() -> None:
    """任务票 24:Game-Status 只读状态检查的依据、引用与关键步骤序列。

    Game-Status 此前只有入口存在性检查(test_explicit_skills),无独立语义检查。
    本票补「关键步骤序列」断言:按步骤编号顺序核对真实只读流程(先定目标项目根
    → 读资料入口 INDEX → 按 INDEX 与协作配置读取约定/基线/任务 → 按分类规则
    逐项核对证据 → 按报告结构输出),而非零散关键词匹配;并断言只读语义与
    「记录声明不等于完成」的分类纪律。
    """

    status = PLUGIN_ROOT / "skills" / "game-status" / "SKILL.md"
    check(status.is_file(), "缺少 skills/game-status/SKILL.md")
    if not status.is_file():
        return
    text = status.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/management.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/contracts/task-triage.md",
        "../../internal/protocols/gate-protocol.md",
        "../../templates/work/result.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "references/status-check.md",
    ):
        check(ref in text, f"game-status SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "只读",            # 检查不写入、不创建、不删除
        "INDEX",           # 唯一默认资料入口
        "协作配置",        # 后端与文档映射
        "基线核对",        # 版本一致性核对
        "可接续",          # 可接续工作
        "未知/存疑",       # 缺失/矛盾归入存疑
        "不当作完成",      # 记录声明不等于完成
        "不替用户决定",    # 需要人决定的事项原样保留
    ):
        check(concept in text, f"game-status SKILL.md 应覆盖概念:{concept}")

    # 关键步骤序列:按编号顺序断言(不是零散关键词是否出现)。
    ordered_steps = [body for _, body in re.findall(r"^(\d+)\.\s*(.+)$", text, re.MULTILINE)]
    sequence = (
        "确定目标项目根",
        "读取资料入口",
        "按 INDEX 与协作配置",
        "分类规则逐项核对",
        "报告结构输出状态报告",
    )
    positions = []
    for fragment in sequence:
        positions.append(next((i for i, body in enumerate(ordered_steps)
                               if fragment in body), -1))
    missing = [s for s, p in zip(sequence, positions) if p < 0]
    check(not missing, f"game-status SKILL.md 缺少关键步骤:{missing}")
    check(positions == sorted(positions) and len(set(positions)) == len(positions),
          f"game-status SKILL.md 关键步骤顺序错乱:{list(zip(sequence, positions))}")

    # 只读语义:报告声明只读;发现资料需更新时作为可接续工作报告,不代为修改。
    check("只读检查:本次未写入、未创建、未删除" in text or
          ("只读" in text and "不使用" in text),
          "game-status 应明确本次检查不写入")
    check("可接续工作" in text and "不代为修改" in text,
          "game-status 应把需要更新的事项作为可接续工作报告而非代改")


def test_game_build_skill_content() -> None:
    """任务票 12:Game-Build 构建运行工作流的包内依据与关键纪律。"""

    build = PLUGIN_ROOT / "skills" / "game-build" / "SKILL.md"
    check(build.is_file(), "缺少 skills/game-build/SKILL.md")
    if not build.is_file():
        return
    text = build.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/production.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/protocols/gate-protocol.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "../../templates/work/result.md",
    ):
        check(ref in text, f"game-build SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "指定成果或工程版本",  # 输入:构建对象有明确版本
        "构建与运行约定",      # 输入:当前约定(来自项目实际配置)
        "目标格式",            # 输入:输出格式及环境
        "可用环境",            # 输入:可用环境
        "实际配置",            # 构建方式从项目实际配置读取
        "不硬编码",            # 不硬编码某个引擎或发布平台
        "输出格式",            # 明确输出格式及环境
        "实际构建或导出",      # 构建、导出真实发生
        "约定入口",            # 启动约定入口
        "版本对应",            # 产物与源成果版本的对应
        "日志",                # 构建与运行日志
        "运行检查",            # 运行检查结果
        "不把存在文件等同于本次构建成功",  # 旧产物/存在文件不算成功
        "旧产物",              # 同上(缺依赖/入口不可用/只有旧产物如实报告)
        "入口不可用",          # 同上
        "子进程",              # 构建脚本及其子进程在已验证边界内
        "会话工作区",          # 构建脚本放会话工作区,不进项目
        "获准",                # 输出只写获准位置(构建输出区)
        "同步技术设计",        # 约定变化同步技术设计
        "技术依据",            # 必要工程配置变更保留技术依据
        "不自行",              # 不自行上传、签名发布、部署或购买服务
        "上传", "签名", "部署", "购买",  # 外部动作边界
        "准确目标",            # 需要外部动作时列明准确目标
        "缺口",                # 缺依赖/缺能力时报告具体缺口
        "可接手材料",          # 缺口时交付可接手材料
        "mgs_scope",           # 写入前确认有效范围
        "允许修改范围",        # 任务范围核对(以 mgs_scope 为准)
        "expected_sha256",     # 更新走版本校验
        "content_base64",      # 二进制产物载荷
        "实际运行",            # 检查必须真实运行并记录输出
        "待验收",              # 约定审查/试玩未完成保留待验收
        "Review", "Playtest",  # 结果供审查与试玩读取
        "试玩流程",            # 不启动完整试玩流程
        "适配",                # 工具输入输出适配与角色资源策略分离
        "资源策略",            # 分离的另一侧:策略由运行保障承担
        "不被假定",            # 外部构建服务或 GUI 不被假定继承本地边界
        "继承本地边界",        # 外部写入通路未验证不视为已受控
        "results/",            # 结果落点
        "进度",                # 任务进度与分流归统筹,直接调用不改
        "不自动",              # 不自动提交、推送、发布
        "受控",                # 新增命令执行路径保持受控
        "mgs_records",         # 统一接口
    ):
        check(concept in text, f"game-build SKILL.md 应覆盖概念:{concept}")
def test_game_review_skill_content() -> None:
    """任务票 13:Game-Review 独立审查工作流的包内依据与关键纪律。"""

    review = PLUGIN_ROOT / "skills" / "game-review" / "SKILL.md"
    check(review.is_file(), "缺少 skills/game-review/SKILL.md")
    if not review.is_file():
        return
    text = review.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/verification.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/protocols/gate-protocol.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "../../templates/evidence/review.md",
    ):
        check(ref in text, f"game-review SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "明确的待审成果和版本",  # 输入:待审对象必须明确
        "当前要求与规范",        # 输入:规范与规格
        "需要检查的范围",        # 输入:范围
        "独立",                  # 独立于原执行上下文
        "同专业",                # 按被审对象选择独立同专业执行实例
        "不新增常设评审角色",     # 审查不增设常设角色
        "作者总结",              # 不仅依赖作者总结
        "直接读取",              # 直接读取规范、实际成果、规格与证据
        "Standards", "Spec",     # 代码两轴
        "两轴",                  # 两轴独立执行、分别呈现
        "分别",                  # 分别呈现(不合并结论)
        "待审版本",              # 固定待审版本
        "文件清单",              # 完整范围用文件清单固定
        "SHA-256",               # 版本指纹登记
        "已提交", "暂存", "未暂存", "新建",  # 四类成果范围完整性
        "HEAD",                  # 不以 HEAD/暂存区对比替代实际文件读取
        "证据",                  # 每项问题关联具体证据
        "影响",                  # 每项问题关联影响
        "明确规则违背",          # 问题分类一
        "专业判断",              # 问题分类二
        "未能检查",              # 问题分类三
        "不修改",                # 审查实例不修改待审专业成果
        "修复",                  # 修复由对应制作或设计任务执行
        "复核",                  # 修复后针对实际新版本复核
        "新版本",                # 旧结论不挪作新版本通过证明
        "不挪用",                # 同上
        "覆盖限制",              # 未实现的运行能力标为覆盖限制
        "不代验收",              # 报告生成不等于验收通过
        "待验收",                # 审查后仍区分待人工验收
        "evidence/",             # 审查记录与证据落点
        "mgs_scope",             # 写入前确认有效范围
        "mgs_write",             # 审查记录经受控通道写入
        "实际运行",              # 能自动核验的检查实际运行
        "审查记录",              # 写入仅限审查记录与证据
        "mgs_records",           # 统一接口(读任务与规格引用)
    ):
        check(concept in text, f"game-review SKILL.md 应覆盖概念:{concept}")
def test_game_playtest_skill_content() -> None:
    """任务票 14:Game-Playtest 试玩工作流的包内依据与关键纪律。"""

    playtest = PLUGIN_ROOT / "skills" / "game-playtest" / "SKILL.md"
    check(playtest.is_file(), "缺少 skills/game-playtest/SKILL.md")
    if not playtest.is_file():
        return
    text = playtest.read_text(encoding="utf-8")
    for ref in (
        "../../internal/contracts/verification.md",
        "../../internal/contracts/common.md",
        "../../internal/contracts/records.md",
        "../../internal/protocols/gate-protocol.md",
        "../../internal/methods/writing-for-agents/SKILL.md",
        "../../templates/evidence/playtest.md",
    ):
        check(ref in text, f"game-playtest SKILL.md 应引用包内依据 {ref}")
    for concept in (
        "明确的版本与入口",  # 输入:版本与入口必须明确
        "场景",              # 输入:要检查的场景或问题
        "适用要求",          # 输入:适用要求
        "可用控制",          # 输入:可用控制工具
        "人工参与约定",      # 输入:人工参与约定
        "制定",              # 制定必要场景
        "实际执行",          # 实际执行可用的检查
        "输入", "观察",      # 记录输入与观察
        "证据",              # 逐项记录证据
        "试玩任务",          # 需要人时给出明确试玩任务
        "回传要求",          # 反馈的回传要求
        "实际反馈",          # 人工结论来自实际反馈
        "来源",              # 实际反馈保留来源
        "未反馈",            # 三态表达一
        "明确通过",          # 三态表达二
        "需要修改",          # 三态表达三
        "SHA-256",           # 结果绑定实际测试版本(指纹)
        "缺陷",              # 发现缺陷时输出交接
        "交接",              # 交接返回执行流程
        "不改产品基线",      # 不改产品基线来迁就观察结果
        "尚未执行",          # 仅写了计划的部分明确尚未执行
        "计划",              # 仅制定计划的工作明确标为计划
        "运行状态",          # 运行状态和测试输出受本次用途限制
        "测试输出",          # 同上
        "GUI",               # 新增 GUI 通路不被假定继承本地边界
        "MCP",               # 新增 MCP 通路同理
        "未就绪",            # 未覆盖能力保持未就绪
        "覆盖限制",          # 如实标注覆盖限制
        "evidence/",         # 试玩记录与证据落点
        "mgs_scope",         # 写入前确认有效范围
        "mgs_write",         # 试玩记录经受控通道写入
        "复测",              # 新修改/失败/疑点触发复测
        "不代验收",          # 试玩记录不等于验收通过
        "待验收",            # 人工项保持待验收
        "统筹",              # 进度与分流归统筹
        "mgs_records",       # 统一接口(读任务与约定)
    ):
        check(concept in text, f"game-playtest SKILL.md 应覆盖概念:{concept}")
def test_goal_change_skills_content() -> None:
    """任务票 15:目标变化/并发/中断恢复纪律在 producer/spec/status 的覆盖。"""

    producer = PLUGIN_ROOT / "skills" / "game-producer" / "SKILL.md"
    check(producer.is_file(), "缺少 skills/game-producer/SKILL.md")
    if producer.is_file():
        text = producer.read_text(encoding="utf-8")
        for concept in (
            "目标或范围变化",      # 影响检查触发条件
            "影响检查",            # 先组织影响检查
            "受影响基线",          # 识别受影响基线
            "受影响任务",          # 识别受影响任务
            "重新分流",            # 受影响任务进入重新分流
            "完成事实",            # 原版本下完成事实保留
            "不自动算作满足新目标",  # 完成事实不自动算作满足新目标
            "基线采纳",            # 基线采纳归设计侧,统筹只识别与安排
            "baseline",            # 统一接口内容指纹核对
            "疑似格式修正",        # 格式修正分类
            "不作废",              # 格式修正不作废成果与证据
            "实质变更",            # 实质变更分类
            "不自行修改该基线",    # 统筹不代设计修改基线
            "交回开发者",          # 未确认变更交回开发者
            "一个有效写入者",      # 单写入者
            "集成责任",            # 独立资源并行时集成责任明确
            "occupancy",           # 占用冲突处理
            "version",             # 版本核对冲突处理
            "不覆盖他人",          # 不覆盖他人已完成成果
            "别名",                # 别名不能绕过占用
            "中断恢复",            # 中断恢复纪律
            "实际内容为准",        # 以实际文件内容为准
            "用户修改",            # 用户后续修改保留
            "只继续仍适用",        # 只继续仍适用的剩余工作
            "不回滚",              # 不回滚用户修改
            "mgs_records",         # 统一接口回读
        ):
            check(concept in text, f"game-producer SKILL.md 应覆盖概念:{concept}")

    spec = PLUGIN_ROOT / "skills" / "game-spec" / "SKILL.md"
    if spec.is_file():
        text = spec.read_text(encoding="utf-8")
        for concept in (
            "内容指纹",    # 双指纹之一
            "归一指纹",    # 双指纹之二
            "64 个",       # 登记方法(先写 0 再回填)
            "格式修正",    # 格式修正不触发新版本
            "同步更新",    # 格式修正同步更新指纹
            "baseline",    # 登记后经统一接口回读确认
            "一致",        # 回读确认状态为一致
        ):
            check(concept in text, f"game-spec SKILL.md 应覆盖概念:{concept}")

    status_ref = PLUGIN_ROOT / "skills" / "game-status" / "references" / "status-check.md"
    if status_ref.is_file():
        text = status_ref.read_text(encoding="utf-8")
        for concept in (
            "内容指纹",          # 状态检查核对内容指纹
            "baseline",          # 经统一接口核对
            "疑似格式修正",      # 格式修正不影响既有结论
            "实质变更",          # 实质变更列入依据过时
            "不自行改判",        # 不自行改判成果与证据有效性
        ):
            check(concept in text, f"status-check.md 应覆盖概念:{concept}")
def test_producer_loop_skills_content() -> None:
    """任务票 16:制作统筹完整闭环纪律——入口分类、按需委派与完成判定。"""

    producer = PLUGIN_ROOT / "skills" / "game-producer" / "SKILL.md"
    check(producer.is_file(), "缺少 skills/game-producer/SKILL.md")
    if producer.is_file():
        text = producer.read_text(encoding="utf-8")
        for concept in (
            "仅讨论",            # 入口一:仅讨论
            "已有规格",          # 入口二:已有规格制作
            "直接调用",          # 入口三:直接专业调用后的状态同步
            "直接专业调用",      # 入口三全称(与上一条至少其一,全要求)
            "状态同步",          # 直接调用结果在下次介入时同步
            "下次介入",          # 同步时点:统筹下次显式介入
            "按事实核对",        # 同步依据实际成果而非作者自述
            "合适环节",          # 按已有资料从合适环节开始
            "中间进入",          # 输入充足时从中间环节进入
            "跳过原型",          # 无需原型的工作跳过原型
            "不强制",            # 不强制每轮执行全部技能
            "全部技能",          # 同上(完整短语「不强制…全部技能」)
            "隔离",              # 设计原型保持隔离
            "Game-Implement",    # 本次制作由 Game-Implement 组织
            "委派",              # 统筹按需明确委派业务入口
            "独立审查",          # 审查完成是验收事实之一
            "约定检查",          # 约定检查完成且无需人判断可标记完成
            "无需人判断",        # 可标记完成的条件
            "待验收",            # 需要人的验收保持待验收
            "作者自报",          # 作者自报不能代替验收
            "旧版本",            # 旧版本结果不能代替当前验收
            "短规格",            # 较小任务可用短规格
            "单项工作",          # 单项工作完成闭环
            "粗粒度",            # 未来目标保持粗粒度
            "阶段门槛",          # 不引入固定阶段门槛
        ):
            check(concept in text, f"game-producer SKILL.md 应覆盖概念:{concept}")
def test_github_issue_workflow_content() -> None:
    """任务票 17:GitHub Issues 任务后端的包内组件与关键纪律。"""

    module = PLUGIN_ROOT / "records" / "mgs_github.py"
    check(module.is_file(), "缺少 records/mgs_github.py(GitHub Issues 后端适配器)")
    if module.is_file():
        # 公开接缝用导入与调用验证:仓库坐标/授权解析归来源 module,
        # adapter 保持同名可用接缝(错误身份与既有捕获分支不变)。
        records_dir = str(module.parent)
        if records_dir not in sys.path:
            sys.path.insert(0, records_dir)
        import mgs_github
        for seam in ("parse_repo_location", "parse_remote_authorizations"):
            check(callable(getattr(mgs_github, seam, None)),
                  f"records/mgs_github.py 缺少可用公开接缝 {seam}")
        check(isinstance(getattr(mgs_github, "GithubBackend", None), type),
              "records/mgs_github.py 缺少 GithubBackend")
        for method in ("create_task", "update_task", "set_triage", "append_result",
                       "set_relations", "set_parent", "close_task", "publish_drafts"):
            check(callable(getattr(mgs_github.GithubBackend, method, None)),
                  f"GithubBackend 缺少公开接缝 {method}")
        for seam in ("plan_backend_switch", "apply_backend_switch",
                     "handover_baseline_check"):
            check(callable(getattr(mgs_github, seam, None)),
                  f"records/mgs_github.py 缺少可用公开接缝 {seam}")
        text = module.read_text(encoding="utf-8")
        for concept in ("issues-write", "不等于批准远端写入", "不静默切换本地后端",
                        "未发布草稿", "避免重复创建", "关闭 Issue 不自动等于验证通过"):
            check(concept in text, f"mgs_github.py 应覆盖概念:{concept}")
    skill_md = PLUGIN_ROOT / "skills" / "game-init" / "SKILL.md"
    if skill_md.is_file():
        text = skill_md.read_text(encoding="utf-8")
        for concept in ("host/owner/repository",       # 明确坐标(任务票 17 AC1)
                        "标签映射",                     # 五类标签映射
                        "不把设计文档复制进每个 Issue",   # 核心设计留本地 Markdown
                        "不自动授权远端写入",           # 选择后端不等于授权(AC4)
                        "issues-write",                 # 授权记录形态
                        "mgs_remote",                   # 会话内受控远端通道
                        "不直连",                       # 不直连远端
                        "先回读再重试",                 # 超时回读(AC5)
                        "未发布草稿",                   # 草稿标注
                        "不静默改用本地后端",           # 不静默切后端
                        "switch-plan",                  # 迁移清单(AC6)
                        "handover",                     # 交接基线可达
                        "不可访问"):                    # 未发布资料不宣称可达
            check(concept in text, f"game-init SKILL.md 应覆盖概念:{concept}")
    protocol = PLUGIN_ROOT / "internal" / "protocols" / "gate-protocol.md"
    if protocol.is_file():
        text = protocol.read_text(encoding="utf-8")
        for concept in ("mgs_remote", "remote_scope", "remote_upstream",
                        "不等于批准远端写入", "未发布草稿", "expected_body_sha256"):
            check(concept in text, f"gate-protocol.md 应覆盖概念:{concept}")
    admin = PLUGIN_ROOT / "runtime" / "mgsrt_admin.py"
    if admin.is_file():
        text = admin.read_text(encoding="utf-8")
        check("set-remote-config" in text and "token_env" in text,
              "mgsrt_admin 应提供 set-remote-config(凭据只登记环境变量名)")
    manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text())
    check(manifest.get("version") == "0.18.0", "任务票 18 后包版本应为 0.18.0")
    check("github-issues-backend" in manifest.get("keywords", []),
          "plugin.json keywords 应含 github-issues-backend")


TESTS = (
    test_game_status_skill_content,
    test_game_build_skill_content,
    test_game_review_skill_content,
    test_game_playtest_skill_content,
    test_goal_change_skills_content,
    test_producer_loop_skills_content,
    test_github_issue_workflow_content,

)


def main() -> int:
    return run_theme("业务 Skill 说明(构建/评审/试玩/统筹)", TESTS, FAILURES)


if __name__ == "__main__":
    sys.exit(main())
