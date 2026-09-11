#!/usr/bin/env python3
"""MyGameStudio 工作结果发布的完整生命周期(票 18)。

把「追加一条结果」从发布前回读、评论发布、结果索引更新,到部分成功、
结果未知、待补索引登记、碰撞归属与旧布局迁移的完整恢复事实集中在这一
个 module:GitHub 适配器 ``mgs_github`` 只在自己的公开写接缝上调用本
module,不再各自维护一份恢复分支。

发布事实(与第一、三、四阶段设计一致,保持既有语义):
- **未发布**:离线或读前核对失败时保存未发布草稿(草稿身份与重放归
  属仍由适配器的草稿职责承担;本 module 在需要时经注入的 ``save_draft``
  调用它),绝不报告为已发布;
- **结果未知**(uncertain):结果评论请求超时且回读失败——可能已落地,
  停止重发、不存草稿,如实回报不确定;
- **部分成功**(partial):评论已真实发布而结果索引更新失败——携带已
  发布评论身份与索引未完成状态,不整体报错;并把「已确认发布、索引未
  完成」的操作身份登记到本地待补索引,读前收养查询失败时凭登记保留
  待恢复状态,不当作全新发布;
- **完成**:评论与索引都完成,清除待补索引登记并回读任务。

待补索引登记(登记存储与归属,审查修复票 review3-01~review6-01 的既有
契约逐条保留)只做文件语义,不发起任何远端调用;身份核验、碰撞共存、
损坏披露、旧布局迁移与逐请求清除的规则在下面各函数的 docstring 中说明。

依赖纪律:只依赖共同正文规则 ``mgs_record_model`` 与传输/错误接缝
``mgs_github_transport``,不反向导入 ``mgs_github``;远端动作经注入的
协作者(``authorize``/``load_issue``/``save_draft``/``read_back``)完成,
不在本 module 复制适配器的读取与草稿实现。同一状态不会被在线调用与
草稿重放解释成不同结果——两条路径都经 ``execute_op`` → 本 module 的
``append``。
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_model import (  # noqa: E402
    _edit_body, _section_lines, _today)
from mgs_github_transport import (  # noqa: E402
    GithubRecordsError, TransportError, repo_path, repo_str)


# ---------- 待补索引登记:存储与完整请求归属 ----------

def pending_identity(repo: dict, identity: str, result_markdown: str) -> dict:
    """待补索引登记的**完整内容身份**:操作+参数+**目标仓库**(审查
    修复票 review4-01/SP-11,与草稿身份及登记文件名的摘要构造同一
    形态)。登记文件内容即保留该全量身份;登记归属以文件内的完整
    身份核对为准(文件名摘要只是寻址,见 pending_index_file)。"""

    return {"op": "append_result",
            "args": {"identity": identity,
                     "result_markdown": result_markdown},
            "repo": repo_str(repo)}


def pending_identity_digest(repo: dict, identity: str,
                            result_markdown: str) -> str:
    """完整内容身份的 SHA-256 **全长**摘要(pending_identity 的唯一
    摘要形态;前 8 hex 与草稿身份及既有登记文件名的短摘要逐字节
    一致,review5-01 抽出共用)。"""

    return hashlib.sha256(json.dumps(
        pending_identity(repo, identity, result_markdown),
        ensure_ascii=False, sort_keys=True)
        .encode("utf-8")).hexdigest()


def pending_index_file(repo: dict, cache_dir: Path | str | None, identity: str,
                       result_markdown: str) -> Path | None:
    """待补索引登记文件路径(当前请求的**完整身份全长哈希**作文件名,
    审查修复票 review5-01/SP-14):布局为 pending-index/
    append-result-{safe}-{短摘要 8 hex}/{完整身份全长哈希}.json。
    短摘要仍与草稿身份的摘要构造同一形态(review2-02/SP-3 的仓库
    身份纪律:同一缓存目录服务多个仓库时各仓各的登记),但只作
    **目录**名;文件名用完整身份全长哈希——确定性碰撞对(同一短
    摘要)同目录不同文件,不同完整身份的登记**共存**、互不覆盖,
    任一请求的重试都能找回自己的登记(此前平铺短摘要文件名在碰撞
    对先后 partial 时后者覆盖前者,前者的重试失去登记被当作全新
    发布而重复)。读入/清除仍以登记内的完整身份核对归属(SP-11)。
    未配置缓存目录时不可用(能力边界,由调用侧如实说明)。"""

    if cache_dir is None:
        return None
    cache = Path(cache_dir)
    digest = pending_identity_digest(repo, identity, result_markdown)
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", identity)
    return (cache / "pending-index"
            / f"append-result-{safe}-{digest[:8]}" / f"{digest}.json")


def legacy_pending_index_file(repo: dict, cache_dir: Path | str | None,
                              identity: str,
                              result_markdown: str) -> Path | None:
    """修复前布局(review5-01 之前写入)的登记文件路径:平铺的
    append-result-{safe}-{短摘要 8 hex}.json。只读兼容——在盘旧登记
    的读入/清除与当前布局走同一身份核验语义;经核验属于当前请求的
    健康登记在读入时按当前布局重写迁移(见 load_pending_index)。
    与当前布局的目录同名不同型(一个带 .json 后缀的文件、一个是
    目录),互不冲突。"""

    if cache_dir is None:
        return None
    cache = Path(cache_dir)
    digest = pending_identity_digest(repo, identity, result_markdown)
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", identity)
    return (cache / "pending-index"
            / f"append-result-{safe}-{digest[:8]}.json")


def _receipt_matches_request(repo: dict, pending: object, identity: str,
                             result_markdown: str) -> bool:
    """单份登记内容是否经**完整身份核验与回执核验**归属当前请求
    (审查修复票 review6-01/SP-17):{op,args,repo} 逐键等于当前请求
    pending_identity() 的对应值(逐键相等蕴含身份字段形态完整),
    且回执字段完整(comment_id 非 None、ref 为非空字符串)。形态不
    完整、身份不一致(他人登记)或回执缺失都不归属——与读入路径
    (load_pending_index)同一核验粒度;清除路径据此对每个待删除
    文件独立判定,不由任一路径的核验代劳另一路径。"""

    if not isinstance(pending, dict):
        return False
    if {key: pending.get(key) for key in ("op", "args", "repo")} \
            != pending_identity(repo, identity, result_markdown):
        return False
    ref = pending.get("ref")
    return pending.get("comment_id") is not None \
        and isinstance(ref, str) and bool(ref)


def record_pending_index(repo: dict, cache_dir: Path | str | None, identity: str,
                         result_markdown: str, comment: dict, ref: str,
                         cause: object) -> str | None:
    """登记已发布评论身份(审查修复票 review3-01/SP-7):部分成功发生时
    把「已确认发布、索引未完成」的操作身份(含完整内容身份,SP-11)
    留在本地——重试的读前收养查询失败(无法看远端)时,凭登记保留
    待恢复状态,不当作全新发布。写入当前布局(完整身份哈希文件名,
    review5-01/SP-14):碰撞对先后 partial 各写各的文件、共存互不
    覆盖。索引补齐后由 clear_pending_index 清除。返回错误说明即
    登记**未生效**(未配置缓存目录,或写入失败/SP-10)——调用侧
    据此如实披露退化模式,不把已发生的远端结果包装成异常(R4 同一
    纪律)。"""

    path = pending_index_file(repo, cache_dir, identity, result_markdown)
    if path is None:
        return "未配置缓存目录(--cache-dir),本地待补索引登记不可用"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            **pending_identity(repo, identity, result_markdown),
            "status": "已发布未补索引",
            "comment_id": comment.get("id"), "ref": ref,
            "created_at": _dt.datetime.now().astimezone().isoformat(
                timespec="seconds"),
            "cause": str(cause),
            "note": ("部分成功的本地身份登记:读前收养查询失败时保留"
                     "待恢复状态(不当作全新发布);远端恢复后重试同一"
                     "请求只收养既有评论并补齐索引"),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        return f"{type(exc).__name__}: {exc}"
    return None


def load_pending_index(repo: dict, cache_dir: Path | str | None, identity: str,
                       result_markdown: str) -> dict | None:
    """读取待补索引登记。文件存在但不可读/损坏时返回带 "corrupt" 键的
    哨兵——「登记存在」本身就是前次已确认发布的证据,身份可读与否不
    改变「不当作全新发布」的判定(结果未知 ≠ 确认不存在,S2 语义
    家族);无登记返回 None(首试语义)。

    身份核验(审查修复票 review4-01/SP-11):文件名摘要可碰撞,登记
    归属以文件内的完整身份为准——①形态不完整(缺 op/args/repo 任一
    身份字段或空身份)无法归属任何请求,按登记损坏披露(corrupt
    语义沿既有非法 JSON 行为);②身份完整但与当前请求不一致,说明
    这份登记属于**另一请求**(碰撞同目录),按无登记处理:不冒认
    他人已发布身份,也不动他人登记。

    回执核验(审查修复票 review5-01/SP-14 复审观察项):身份匹配但
    登记缺 comment_id/ref 回执字段(无法确认已发布评论身份)按登记
    损坏披露(口径沿既有:待恢复、不重发、提示人工核对),不再静默
    返回缺失发布身份仍称已确认发布。

    布局兼容(review5-01/SP-14):当前布局为短摘要目录下的完整身份
    哈希文件(不同完整身份共存);修复前的平铺短摘要文件名
    (legacy_pending_index_file)只读兼容——先查当前布局,未命中再查
    旧布局,两处同一身份核验语义。经核验属于当前请求的健康登记若仍在
    旧布局,读入时按当前布局重写迁移并移除旧文件(尽力而为,失败沉默:
    不影响本次读入返回,下次读入再试;清除时两布局一并处理,迁移
    中途失败也不会「清除后自旧文件复活」)。"""

    path = pending_index_file(repo, cache_dir, identity, result_markdown)
    if path is None:
        return None
    if not path.exists():
        legacy = legacy_pending_index_file(repo, cache_dir, identity,
                                           result_markdown)
        if legacy is None or not legacy.exists():
            return None
        path = legacy
    try:
        pending = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"corrupt": f"{type(exc).__name__}: {exc}", "path": str(path)}
    if not isinstance(pending, dict):
        return {"corrupt": "登记内容不是对象", "path": str(path)}
    op, args, repo_value = (pending.get("op"), pending.get("args"),
                            pending.get("repo"))
    args = args if isinstance(args, dict) else {}
    complete = (isinstance(op, str) and bool(op)
                and isinstance(args.get("identity"), str)
                and bool(args.get("identity"))
                and isinstance(args.get("result_markdown"), str)
                and isinstance(repo_value, str) and bool(repo_value))
    if not complete:
        return {"corrupt": ("登记身份不完整(缺 op/args(identity,"
                            "result_markdown)/repo 之一或为空,无法"
                            "归属任何请求)"),
                "path": str(path)}
    if {"op": op, "args": args, "repo": repo_value} != \
            pending_identity(repo, identity, result_markdown):
        return None
    ref = pending.get("ref")
    if pending.get("comment_id") is None \
            or not isinstance(ref, str) or not ref:
        return {"corrupt": ("登记回执不完整(缺 comment_id/ref 之一"
                            "或为空,无法确认已发布评论身份)"),
                "path": str(path)}
    if path == legacy_pending_index_file(repo, cache_dir, identity,
                                         result_markdown):
        # 旧布局健康登记:按当前布局重写迁移,移除旧文件(尽力而为)
        try:
            current = pending_index_file(repo, cache_dir, identity,
                                         result_markdown)
            current.parent.mkdir(parents=True, exist_ok=True)
            current.write_text(json.dumps(pending, ensure_ascii=False,
                                          indent=2), encoding="utf-8")
            path.unlink(missing_ok=True)
        except OSError:
            pass
    return pending


def clear_pending_index(repo: dict, cache_dir: Path | str | None, identity: str,
                        result_markdown: str) -> None:
    """结果索引补齐后清除登记。**每个待删除文件分别通过自身完整身份
    核验**(审查修复票 review6-01/SP-17):读该文件自己的登记 JSON,
    {op,args,repo} 逐键等于当前请求 pending_identity() 的对应值且回执
    字段(comment_id/ref)完整才 unlink——清除路径的核验粒度与读入
    路径(load_pending_index)一致。此前只凭一次读入核验(优先当前
    布局)就对当前与旧(平铺)两路径无条件 unlink,会误删旧平铺路径
    上**另一完整身份**的健康登记(自然升级序列:旧版本给 B 留平铺
    登记 → 升级后碰撞对 A 写新布局登记 → A 补齐清理误删 B 的登记 →
    B 重试读前失败失去登记被当作全新发布而重复)。不匹配(他人登记,
    SP-11 不误删)/不可读/JSON 无效/形态不完整(含回执不完整,
    review5-01)一律保守保留;若一布局损坏而另一布局是同身份健康
    登记,按各自内容独立判定(健康侧清除、损坏侧保持原位由人工按
    哨兵处置)。

    同身份双布局残留(迁移中途失败留下的旧副本)在逐路径核验下两处
    都属当前请求、都清除——「已清除的登记不因迁移残留复活」语义保持
    (review5-01)。残留与清除失败(极端 I/O 故障)都保持沉默:只会
    让后续读前查询失败的重试多保持一次待恢复或一次损坏披露(保守
    方向,不会重复发布),远端可读时按远端权威修正。"""

    for path in (pending_index_file(repo, cache_dir, identity, result_markdown),
                 legacy_pending_index_file(repo, cache_dir, identity,
                                           result_markdown)):
        if path is None:
            continue
        try:
            pending = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # 不可读/JSON 无效:保守保留
        if not _receipt_matches_request(repo, pending, identity,
                                        result_markdown):
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def pending_recovery_result(number: int, pending: dict, failure: str,
                            attempts: list) -> dict:
    """读前收养查询失败时的待恢复返回(review3-01/SP-7):凭本地登记
    保留前次已确认发布的操作身份,保持部分成功(partial)语义——
    「已发布未完索引」与「结果未知」(uncertain)是两种事实,分别表达;
    本次不发布也不动索引(远端不可读时不做任何写),彻底恢复后重试
    经读前收养只补索引。"""

    attempts = attempts + [{"step": "pending-index", "outcome": "kept"}]
    if pending.get("corrupt"):
        return {"published": True, "partial": True, "comment_id": None,
                "ref": None, "issue_number": number, "index_updated": False,
                "attempts": attempts,
                "note": ("待恢复:前次调用已确认发布该结果评论(本地"
                         "待补索引登记存在),本次读前收养查询失败"
                         f"({failure})且登记不可读({pending['corrupt']};"
                         f"登记文件 {pending.get('path')});已保留待恢复"
                         "状态、不当作全新发布;请人工核对远端评论与登记"
                         "文件后重试(远端可读时重试同一请求即经读前"
                         "收养补齐索引)")}
    return {"published": True, "partial": True,
            "comment_id": pending.get("comment_id"),
            "ref": pending.get("ref"), "issue_number": number,
            "index_updated": False, "attempts": attempts,
            "note": ("待恢复:前次调用已确认发布该结果评论(本地待补索引"
                     f"登记:{pending.get('ref')}),本次读前收养查询失败"
                     f"({failure})无法核对远端;已保留已发布操作身份、"
                     "不当作全新发布(本次不发布也不动索引);彻底恢复后"
                     "重试同一请求只收养既有评论并补齐索引")}


# ---------- 完整结果追加生命周期 ----------

class ResultPublication:
    """一次结果追加的完整发布恢复职责(公开接缝)。

    协作者(由 GitHub 适配器按其写接缝注入,本 module 不复制其实现):
    - ``authorize``:写授权核对(无授权直接抛出记录错误);
    - ``load_issue(identity)`` → (issue 或 None(缓存态), 解析后任务, 载荷);
    - ``save_draft(op, args, cause)``:远端不可用时保存未发布草稿;
    - ``read_back(identity)``:索引补齐后回读任务(评论与索引一致)。
    远端动作只经 ``transport`` 与 ``repo_path`` 拼接,传输故障经
    ``TransportError`` 区分 offline/timeout/bad_response,不用通用自动
    重试覆盖所有写操作。
    """

    def __init__(self, *, repo: dict, transport, cache_dir: Path | str | None,
                 authorize, load_issue, save_draft, read_back) -> None:
        self.repo = repo
        self.transport = transport
        self.cache_dir = cache_dir
        self._authorize = authorize
        self._load_issue = load_issue
        self._save_draft = save_draft
        self._read_back = read_back

    def append(self, identity: str, result_markdown: str) -> dict:
        """追加结果:发布评论(带任务身份前缀)并把评论登记进正文结果索引。

        防重复与部分成功语义:
        - 发布前先按评论正文回读,已存在同文评论即**收养**(不发第二条);
          「评论已发布而索引未完成」的请求重试时因此只补索引,不重复发布
          (与 create_task 的读前收养同一纪律);
        - 读前回读失败时先核对本地**待补索引登记**(审查修复票
          review3-01/SP-7):前次调用已确认发布的操作身份在部分成功时登记
          于本地缓存目录,读前查询失败(无法看远端)时凭登记保留**待恢复
          状态**,不当作全新发布;登记以文件内的完整内容身份核验归属
          (review4-01/SP-11),身份不一致(短摘要文件名碰撞)按无登记
          处理,不冒认他人已发布身份;无登记则本次尚未发布任何内容,按
          首试语义继续尝试发布(未配置缓存目录时登记不可用,属能力边界,
          部分成功结果中如实披露退化,SP-10);
        - 评论请求超时先回读,区分「回读确认不存在」(才允许重试一次)与
          「回读失败」——后者保留不确定状态并停止重发,不存草稿(审查修复
          票 01/S2);
        - 评论已真实发布而结果索引更新失败:如实回报**部分成功**——携带
          已发布评论身份与索引未完成状态,不整体报错(审查修复票
          review2-02/SP-2;runtime 合同:已写入待表达,不把已发生的远端
          结果包装成未执行的失败)。
        """

        self._authorize()
        draft_args = {"identity": identity, "result_markdown": result_markdown}
        try:
            issue, parsed, _payload = self._load_issue(identity)
        except TransportError as exc:
            return self._save_draft("append_result", draft_args, str(exc))
        if issue is None:
            return self._save_draft("append_result", draft_args,
                                    "离线缓存态无法发布评论")
        number = parsed["issue_number"]
        comment_body = f"任务:{identity}\n\n{result_markdown}"
        attempts: list[dict] = []
        # 读前回读:同文评论已存在即收养(重试只补索引,不重复发布)。
        # 读前回读本身失败时先核对本地待补索引登记(SP-7):有登记说明
        # 前次调用已确认发布——保留待恢复状态,不当作全新发布;无登记则
        # 本次尚未发布任何内容,按首试语义继续尝试发布。「回读失败停止
        # 重发」(S2)针对的是发布超时之后的结果不确定,两者不混同。
        comment, read_first_failed = self._read_first(number, comment_body,
                                                      attempts)
        if read_first_failed is not None:
            pending = load_pending_index(self.repo, self.cache_dir, identity,
                                         result_markdown)
            if pending is not None:
                return pending_recovery_result(
                    number, pending, read_first_failed, attempts)
        if comment is None:
            comment, terminal = self._publish_comment(
                number, comment_body, draft_args, attempts)
            if terminal is not None:
                return terminal
        if comment is None:
            raise GithubRecordsError(
                f"结果评论两次尝试均未确认发布(attempts {attempts});不虚报成功")
        return self._finish(issue, number, identity, result_markdown, comment,
                            comment_body, attempts)

    def _read_first(self, number: int, comment_body: str,
                    attempts: list) -> tuple[dict | None, str | None]:
        """发布前回读:返回 (收养到的同文评论或 None, 读前失败说明或 None)。"""

        try:
            status, comments = self._list_comments(number)
        except TransportError as exc:
            attempts.append({"step": "read-first", "outcome": exc.kind,
                             "detail": str(exc)})
            return None, str(exc)
        if status == 200 and isinstance(comments, list):
            hit = next((c for c in comments
                        if c.get("body") == comment_body), None)
            if hit is not None:
                attempts.append({"step": "read-first", "outcome": "exists"})
            return hit, None
        attempts.append({"step": "read-first", "outcome": "bad_response",
                         "detail": f"list comments HTTP {status}"})
        return None, f"list comments HTTP {status}"

    def _publish_comment(self, number: int, comment_body: str, draft_args: dict,
                         attempts: list) -> tuple[dict | None, dict | None]:
        """发布评论(超时先回读,未落地才重试一次)。

        返回 (已确认发布的评论或 None, 终止结果或 None):终止结果为未发布
        草稿(离线)或结果未知(uncertain,回读失败停止重发);None 表示按
        重试继续。区分「回读确认不存在」(才允许重试)与「回读失败」——
        后者保留不确定状态并停止重发,不存草稿(审查修复票 01/S2)。
        """

        for index in range(2):
            try:
                status, created = self._create_comment(number, comment_body)
                if status not in (200, 201):
                    raise TransportError("bad_response", f"comment HTTP {status}")
                attempts.append({"step": f"comment-{index + 1}",
                                 "outcome": "created"})
                return created, None
            except TransportError as exc:
                attempts.append({"step": f"comment-{index + 1}",
                                 "outcome": exc.kind, "detail": str(exc)})
                if exc.kind == "offline":
                    return None, self._save_draft("append_result", draft_args,
                                                  str(exc))
                comment, readback_failed = self._readback_comment(
                    number, comment_body, attempts)
                if comment is not None:
                    return comment, None
                if readback_failed:
                    return None, {
                        "published": None, "uncertain": True,
                        "issue_number": number, "attempts": attempts,
                        "note": ("结果不确定:结果评论请求超时(可能已落地),"
                                 "回读失败无法确认;已停止重发(避免重复评论),"
                                 "也未保存草稿(重放会造成重复);请在远端可用后"
                                 "先回读评论确认,再决定是否重发"),
                    }
        return None, None

    def _readback_comment(self, number: int, comment_body: str,
                          attempts: list) -> tuple[dict | None, bool]:
        """发布超时后的回读:返回 (同文评论或 None, 回读是否失败)。"""

        try:
            status, comments = self._list_comments(number)
            if status == 200 and isinstance(comments, list):
                hit = next((c for c in comments
                            if c.get("body") == comment_body), None)
                if hit is not None:
                    attempts.append({"step": "readback", "outcome": "exists"})
                    return hit, False
                attempts.append({"step": "readback", "outcome": "absent"})
                return None, False
            attempts.append({"step": "readback", "outcome": "bad_response",
                             "detail": f"list comments HTTP {status}"})
            return None, True
        except TransportError as exc:
            attempts.append({"step": "readback", "outcome": "uncertain",
                             "detail": str(exc)})
            return None, True

    def _finish(self, issue: dict, number: int, identity: str,
                result_markdown: str, comment: dict, comment_body: str,
                attempts: list) -> dict:
        """评论已确认发布:补齐结果索引;失败时如实回报部分成功并登记。"""

        ref = f"#issuecomment-{comment.get('id')}"
        excerpt = (comment_body.strip().splitlines()[2][:60]
                   if len(comment_body.strip().splitlines()) > 2 else "结果")
        body = issue.get("body") or ""
        index_lines = [line for line in _section_lines(body, "结果索引")
                       if line.strip() != "(暂无)"]
        already_indexed = any(ref in line for line in index_lines)
        if not already_indexed:
            index_lines.append(f"- {ref}:{excerpt}")
        new_body = _edit_body(
            body, index_lines=index_lines,
            append_change=None if already_indexed
            else f"{_today()} 追加结果评论 {ref}")
        try:
            status, _updated = self._patch_body(number, new_body)
            if status != 200:
                raise TransportError("bad_response", f"update HTTP {status}")
        except TransportError as exc:
            # SP-2:评论已真实发布,结果索引更新失败 ≠ 整体失败。如实回报
            # 部分成功:携带已发布评论身份与索引未完成状态;恢复后重试同一
            # 请求经「读前收养」只补索引,不再重复发布评论。
            attempts.append({"step": "index-patch", "outcome": exc.kind,
                             "detail": str(exc)})
            return self._partial_result(number, identity, result_markdown,
                                        comment, ref, exc, attempts)
        # 索引已补齐:清除待补索引登记(若前次部分成功留下;SP-7)
        clear_pending_index(self.repo, self.cache_dir, identity, result_markdown)
        readback = self._read_back(identity)
        return {"published": True, "comment_id": comment.get("id"),
                "ref": ref, "issue_number": number, "readback": readback,
                "attempts": attempts, "index_updated": True}

    def _partial_result(self, number: int, identity: str, result_markdown: str,
                        comment: dict, ref: str, exc: TransportError,
                        attempts: list) -> dict:
        # SP-7:把已发布身份登记到本地——重试的读前收养查询失败(无法看
        # 远端)时凭登记保留待恢复状态,不当作全新发布。登记写入失败不把
        # 已发生的远端结果包装成异常(R4 同一纪律)。SP-10:登记**实际
        # 落盘**才支撑「不会重复发布」承诺;未配置缓存目录或写入失败
        # (登记未生效)时如实披露退化。
        record_error = record_pending_index(
            self.repo, self.cache_dir, identity, result_markdown, comment, ref, exc)
        if record_error is None:
            note = ("部分成功:结果评论已发布("
                    f"{ref}),但正文结果索引更新未完成({exc});"
                    "重试同一请求只会收养既有评论并补齐索引,"
                    "不会重复发布")
        else:
            note = ("部分成功:结果评论已发布("
                    f"{ref}),但正文结果索引更新未完成({exc});"
                    f"警告:本地待补索引登记未生效({record_error})"
                    "——本结果无跨调用身份保留,远端可读时重试同一"
                    "请求经读前收养只补索引,但若重试时读前收养查询"
                    "失败,会当作全新发布而可能重复发布同文评论;"
                    "建议配置缓存目录(--cache-dir)启用登记")
        return {"published": True, "partial": True,
                "comment_id": comment.get("id"), "ref": ref,
                "issue_number": number, "index_updated": False,
                "attempts": attempts, "note": note}

    # ----- 远端动作(经传输层;路径只在此拼接) -----

    def _list_comments(self, number: int) -> tuple[int, object]:
        return self.transport.request(
            "GET", f"{repo_path(self.repo)}/issues/{number}"
                   "/comments?per_page=100")

    def _create_comment(self, number: int,
                        comment_body: str) -> tuple[int, object]:
        return self.transport.request(
            "POST", f"{repo_path(self.repo)}/issues/{number}/comments",
            {"body": comment_body})

    def _patch_body(self, number: int, body: str) -> tuple[int, object]:
        return self.transport.request(
            "PATCH", f"{repo_path(self.repo)}/issues/{number}", {"body": body})
