#!/usr/bin/env python3
"""MyGameStudio 工作结果发布的完整生命周期(票 18;登记存储拆出见票 19)。

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

待补索引登记的**存储与归属**(完整内容身份、碰撞共存、损坏披露、旧
布局迁移、逐请求清除)自票 19 起收敛在 ``mgs_pending_index.PendingIndex``
的唯一恢复职责里;本 module 只在自己的真实追加路径上使用它,不再分别
实现身份与回执核验。

依赖纪律:只依赖共同正文规则 ``mgs_record_model``、传输/错误接缝
``mgs_github_transport`` 与登记存储 ``mgs_pending_index``,不反向导入
``mgs_github``;远端动作经注入的协作者(``authorize``/``load_issue``/
``save_draft``/``read_back``)完成,不在本 module 复制适配器的读取与
草稿实现。同一状态不会被在线调用与草稿重放解释成不同结果——两条路径
都经 ``execute_op`` → 本 module 的 ``append``。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_model import (  # noqa: E402
    edit_body, section_lines, today)
from mgs_github_transport import (  # noqa: E402
    GithubRecordsError, TransportError, repo_path)
from mgs_pending_index import (  # noqa: E402
    PendingIndex, pending_recovery_result)


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
          状态**,不当作全新发布;登记以完整内容身份核验归属
          (review4-01/SP-11,由 ``PendingIndex`` 承担),身份不一致(短摘要
          文件名碰撞)按无登记处理,不冒认他人已发布身份;无登记则本次尚未
          发布任何内容,按首试语义继续尝试发布(未配置缓存目录时登记不可
          用,属能力边界,部分成功结果中如实披露退化,SP-10);
        - 评论请求超时先回读,区分「回读确认不存在」(才允许重试一次)与
          「回读失败」——后者保留不确定状态并停止重发,不存草稿(审查修复
          票 01/S2);
        - 评论已真实发布而结果索引更新失败:如实回报**部分成功**——携带
          已发布评论身份与索引未完成状态,不整体报错(审查修复票
          review2-02/SP-2;runtime 合同:已写入待表达,不把已发生的远端
          结果包装成未执行的失败)。
        """

        self._authorize()
        registration = PendingIndex(self.repo, self.cache_dir, identity,
                                    result_markdown)
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
            pending = registration.load()
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
        return self._finish(issue, number, registration, comment, comment_body,
                            attempts)

    def _find_comment(self, number: int, comment_body: str,
                      ) -> tuple[dict | None, str, str | None, str | None]:
        """列出 Issue 评论并匹配同文评论(读前收养与超时回读共用的核心)。

        返回 (命中评论或 None, 类别, 说明, 传输故障 kind);调用方据此各自
        决定 attempts 记录与后续动作,本助手不做重试、不写 attempts:
        - ``exists``:命中同文评论(命中评论在首位,说明与 kind 为 None);
        - ``absent``:HTTP 200 且评论列表可读但无同文评论;
        - ``bad_response``:状态非 200 或评论不是列表,说明为 HTTP 状态;
        - ``error``:传输故障,说明为异常文本,kind 为故障类别(offline/
          timeout/bad_response)。
        """

        try:
            status, comments = self._list_comments(number)
        except TransportError as exc:
            return None, "error", str(exc), exc.kind
        if status == 200 and isinstance(comments, list):
            hit = next((c for c in comments
                        if c.get("body") == comment_body), None)
            return hit, ("exists" if hit is not None else "absent"), None, None
        detail = f"list comments HTTP {status}"
        return None, "bad_response", detail, None

    def _read_first(self, number: int, comment_body: str,
                    attempts: list) -> tuple[dict | None, str | None]:
        """发布前回读:返回 (收养到的同文评论或 None, 读前失败说明或 None)。

        「列评论 + 匹配 body」的核心见 ``_find_comment``;本方法只把结果
        映射为读前语义:命中即收养(记 exists),读前失败转失败说明,
        确认不存在不记任何 attempts(与首试语义一致)。
        """

        hit, category, detail, kind = self._find_comment(number, comment_body)
        if category == "error":
            attempts.append({"step": "read-first", "outcome": kind,
                             "detail": detail})
            return None, detail
        if category == "bad_response":
            attempts.append({"step": "read-first", "outcome": "bad_response",
                             "detail": detail})
            return None, detail
        if category == "exists":
            attempts.append({"step": "read-first", "outcome": "exists"})
        return hit, None

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
        """发布超时后的回读:返回 (同文评论或 None, 回读是否失败)。

        「列评论 + 匹配 body」的核心见 ``_find_comment``;本方法只映射为
        回读语义:命中即收养,确认不存在判未落地(允许重试),坏应答或
        传输故障判回读失败(结果不确定,停止重发)。
        """

        hit, category, detail, _kind = self._find_comment(number, comment_body)
        if category == "exists":
            attempts.append({"step": "readback", "outcome": "exists"})
            return hit, False
        if category == "absent":
            attempts.append({"step": "readback", "outcome": "absent"})
            return None, False
        if category == "bad_response":
            attempts.append({"step": "readback", "outcome": "bad_response",
                             "detail": detail})
            return None, True
        attempts.append({"step": "readback", "outcome": "uncertain",
                         "detail": detail})
        return None, True

    def _finish(self, issue: dict, number: int, registration: PendingIndex,
                comment: dict, comment_body: str, attempts: list) -> dict:
        """评论已确认发布:补齐结果索引;失败时如实回报部分成功并登记。"""

        ref = f"#issuecomment-{comment.get('id')}"
        excerpt = (comment_body.strip().splitlines()[2][:60]
                   if len(comment_body.strip().splitlines()) > 2 else "结果")
        body = issue.get("body") or ""
        index_lines = [line for line in section_lines(body, "结果索引")
                       if line.strip() != "(暂无)"]
        already_indexed = any(ref in line for line in index_lines)
        if not already_indexed:
            index_lines.append(f"- {ref}:{excerpt}")
        new_body = edit_body(
            body, index_lines=index_lines,
            append_change=None if already_indexed
            else f"{today()} 追加结果评论 {ref}")
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
            return self._partial_result(number, registration, comment, ref, exc,
                                        attempts)
        # 索引已补齐:清除待补索引登记(若前次部分成功留下;SP-7)
        registration.clear()
        readback = self._read_back(registration.identity)
        return {"published": True, "comment_id": comment.get("id"),
                "ref": ref, "issue_number": number, "readback": readback,
                "attempts": attempts, "index_updated": True}

    def _partial_result(self, number: int, registration: PendingIndex,
                        comment: dict, ref: str, exc: TransportError,
                        attempts: list) -> dict:
        # SP-7:把已发布身份登记到本地——重试的读前收养查询失败(无法看
        # 远端)时凭登记保留待恢复状态,不当作全新发布。登记写入失败不把
        # 已发生的远端结果包装成异常(R4 同一纪律)。SP-10:登记**实际
        # 落盘**才支撑「不会重复发布」承诺;未配置缓存目录或写入失败
        # (登记未生效)时如实披露退化。
        record_error = registration.record(comment, ref, exc)
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
