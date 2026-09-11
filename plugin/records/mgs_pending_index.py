#!/usr/bin/env python3
"""待补索引登记:存储与完整请求归属(票 19)。

把「追加结果部分成功后,评论已确认发布、正文结果索引未完成」这一操作
身份的本地登记(写入/读取/迁移/清除)连同其**归属与有效性核验**收敛
为一个恢复职责,供发布恢复 module ``mgs_result_publication`` 在自己的
真实追加路径上使用。此前登记的有效性、完整请求归属与回执要求分别实现
在读入与清除两条路径里(读入内联形态/身份/回执判定,清除另用布尔助手);
现统一到 ``PendingIndex._classify`` 的唯一核验粒度,两条路径共用。

登记事实(与第一、三、四阶段设计及既有审查修复票契约一致,只集中不
改变):
- **完整内容身份** = 操作 + 参数 + **目标仓库**(review4-01/SP-11),
  登记文件内容保留该全量身份,归属以文件内完整身份核对为准;
- **文件名** = 完整身份全长哈希(当前布局,review5-01/SP-14),因此短
  标识确定性碰撞的两个请求同目录不同文件、登记**共存**互不覆盖;修复前
  的平铺短摘要文件名只读兼容并在读入时迁移;
- **逐请求清除**(review6-01/SP-17):每个待删文件分别通过自身完整身份
  与回执核验,不冒认、不误删他人登记,同身份双布局残留两处都清除;
- **保守披露**:不可读/损坏/形态不完整按登记损坏哨兵披露(待恢复、不
  重发、提示人工核对),身份完整但不属于当前请求按无登记处理。

本模块只做文件语义,不发起任何远端调用;依赖纪律:只依赖最底层传输/
错误接缝 ``mgs_github_transport``(取其仓库坐标形态),不导入发布恢复
``mgs_result_publication``、业务适配器 ``mgs_github`` 或查询组织
``mgs_records``。
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_github_transport import repo_str  # noqa: E402


class PendingIndex:
    """一次追加请求的待补索引登记句柄。

    承载原本逐函数重复传递的四元组 (repo, cache_dir, identity,
    result_markdown):完整请求身份由 (repo, identity, result_markdown)
    决定,cache_dir 决定落盘位置(未配置时登记能力不可用,由调用侧如实
    披露退化)。读取(load)、写入(record)与清除(clear)都以本句柄的
    完整身份作为归属核验基准;current_path/legacy_path 只负责寻址。
    """

    def __init__(self, repo: dict, cache_dir: Path | str | None,
                 identity: str, result_markdown: str) -> None:
        self.repo = repo
        self.cache_dir = cache_dir
        self.identity = identity
        self.result_markdown = result_markdown

    # ----- 完整内容身份与寻址 -----

    def content_identity(self) -> dict:
        """登记的**完整内容身份**:操作+参数+**目标仓库**(SP-11,与草稿
        身份及登记文件名的摘要构造同一形态)。"""

        return {"op": "append_result",
                "args": {"identity": self.identity,
                         "result_markdown": self.result_markdown},
                "repo": repo_str(self.repo)}

    def digest(self) -> str:
        """完整内容身份的 SHA-256 **全长**摘要;前 8 hex 与草稿身份及旧
        布局登记文件名的短摘要逐字节一致(review5-01 抽出共用)。"""

        return hashlib.sha256(json.dumps(
            self.content_identity(), ensure_ascii=False, sort_keys=True)
            .encode("utf-8")).hexdigest()

    def _safe(self) -> str:
        return re.sub(r"[^A-Za-z0-9._-]", "-", self.identity)

    def current_path(self) -> Path | None:
        """当前布局路径:pending-index/append-result-{safe}-{短摘要 8 hex}/
        {完整身份全长哈希}.json。短摘要仍带仓库身份纪律(review2-02/SP-3)
        但只作**目录**名;文件名用完整身份哈希,碰撞对同目录不同文件共存
        (review5-01/SP-14)。未配置缓存目录时不可用(能力边界)。"""

        if self.cache_dir is None:
            return None
        digest = self.digest()
        return (Path(self.cache_dir) / "pending-index"
                / f"append-result-{self._safe()}-{digest[:8]}" / f"{digest}.json")

    def legacy_path(self) -> Path | None:
        """修复前布局路径:平铺的 append-result-{safe}-{短摘要}.json。
        只读兼容——读入/清除与当前布局走同一身份核验语义;经核验属于当前
        请求的健康登记在读入时迁移到当前布局。与当前布局同名不同型(一个
        带 .json 后缀的文件、一个是目录),互不冲突。"""

        if self.cache_dir is None:
            return None
        digest = self.digest()
        return (Path(self.cache_dir) / "pending-index"
                / f"append-result-{self._safe()}-{digest[:8]}.json")

    # ----- 唯一归属核验(读取与清除共用) -----

    def _classify(self, pending: object) -> tuple[str, str]:
        """单份登记内容相对本请求的归属判定(读取与清除的唯一核验粒度)。

        返回 (verdict, detail):
        - ``not_object``:内容不是对象;
        - ``incomplete``:身份或回执形态不完整(detail 为披露说明);
        - ``foreign``:身份完整但不属于本请求(他人登记);
        - ``owned``:逐键等于本请求完整身份且回执(comment_id/ref)完整。

        逐键相等蕴含身份字段形态完整;回执字段完整(comment_id 非 None、
        ref 为非空字符串)是「可确认已发布评论身份」的必要条件。
        """

        if not isinstance(pending, dict):
            return "not_object", "登记内容不是对象"
        op, args, repo_value = (pending.get("op"), pending.get("args"),
                                pending.get("repo"))
        args = args if isinstance(args, dict) else {}
        complete = (isinstance(op, str) and bool(op)
                    and isinstance(args.get("identity"), str)
                    and bool(args.get("identity"))
                    and isinstance(args.get("result_markdown"), str)
                    and isinstance(repo_value, str) and bool(repo_value))
        if not complete:
            return "incomplete", ("登记身份不完整(缺 op/args(identity,"
                                  "result_markdown)/repo 之一或为空,无法"
                                  "归属任何请求)")
        if {"op": op, "args": args, "repo": repo_value} \
                != self.content_identity():
            return "foreign", ""
        ref = pending.get("ref")
        if pending.get("comment_id") is None \
                or not isinstance(ref, str) or not ref:
            return "incomplete", ("登记回执不完整(缺 comment_id/ref 之一"
                                  "或为空,无法确认已发布评论身份)")
        return "owned", ""

    # ----- 写入 / 读取 / 清除 -----

    def record(self, comment: dict, ref: str, cause: object) -> str | None:
        """登记已发布评论身份:部分成功发生时把「已确认发布、索引未完成」
        的操作身份(含完整内容身份)留在本地——重试的读前收养查询失败时
        凭登记保留待恢复状态,不当作全新发布。写入当前布局(完整身份哈希
        文件名):碰撞对先后 partial 各写各的文件、共存互不覆盖。

        返回错误说明即登记**未生效**(未配置缓存目录或写入失败);调用侧
        据此如实披露退化模式,不把已发生的远端结果包装成异常。
        """

        path = self.current_path()
        if path is None:
            return "未配置缓存目录(--cache-dir),本地待补索引登记不可用"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({
                **self.content_identity(),
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

    def load(self) -> dict | None:
        """读取待补索引登记(完整请求归属 + 回执核验 + 旧布局迁移)。

        无登记(两布局皆无)返回 None(首试语义);文件存在但不可读/损坏
        /形态不完整返回带 "corrupt" 键的哨兵——「登记存在」本身就是前次
        已确认发布的证据,身份可读与否不改变「不当作全新发布」的判定
        (结果未知 ≠ 确认不存在);身份完整但不属于本请求(短摘要碰撞同
        目录)按无登记处理:不冒认他人已发布身份,也不动他人登记。

        旧布局健康登记读入时按当前布局重写迁移并移除旧文件(尽力而为,
        失败沉默:不影响本次读入返回,下次读入再试;清除时两布局一并
        处理,迁移中途失败也不会「清除后自旧文件复活」)。"""

        path = self.current_path()
        if path is None:
            return None
        if not path.exists():
            legacy = self.legacy_path()
            if legacy is None or not legacy.exists():
                return None
            path = legacy
        try:
            pending = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"corrupt": f"{type(exc).__name__}: {exc}", "path": str(path)}
        verdict, detail = self._classify(pending)
        if verdict in ("not_object", "incomplete"):
            return {"corrupt": detail, "path": str(path)}
        if verdict == "foreign":
            return None
        if path == self.legacy_path():
            self._migrate(pending, path)
        return pending

    def _migrate(self, pending: dict, legacy: Path) -> None:
        """把经核验属于本请求的旧布局健康登记按当前布局重写并移除旧文件
        (尽力而为,失败沉默)。"""

        try:
            current = self.current_path()
            current.parent.mkdir(parents=True, exist_ok=True)
            current.write_text(json.dumps(pending, ensure_ascii=False, indent=2),
                               encoding="utf-8")
            legacy.unlink(missing_ok=True)
        except OSError:
            pass

    def clear(self) -> None:
        """结果索引补齐后清除登记:**每个待删除文件分别通过自身完整身份
        与回执核验**(与 load 同一 `_classify` 粒度):``owned`` 才 unlink。
        不匹配(他人登记)/不可读/JSON 无效/形态不完整一律保守保留;若一
        布局损坏而另一布局是同身份健康登记,按各自内容独立判定(健康侧
        清除、损坏侧保持原位由人工按哨兵处置)。

        同身份双布局残留(迁移中途失败留下的旧副本)在逐路径核验下两处都
        属当前请求、都清除——「已清除的登记不因迁移残留复活」。残留与清除
        失败(极端 I/O 故障)都保持沉默:只会让后续读前查询失败的重试多
        保持一次待恢复或一次损坏披露(保守方向,不会重复发布),远端可读时
        按远端权威修正。"""

        for path in (self.current_path(), self.legacy_path()):
            if path is None:
                continue
            try:
                pending = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue  # 不可读/JSON 无效:保守保留
            if self._classify(pending)[0] != "owned":
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def pending_recovery_result(number: int, pending: dict, failure: str,
                            attempts: list) -> dict:
    """读前收养查询失败时的待恢复返回(review3-01/SP-7):凭本地登记保留
    前次已确认发布的操作身份,保持部分成功(partial)语义——「已发布未完
    索引」与「结果未知」(uncertain)是两种事实,分别表达;本次不发布也不
    动索引(远端不可读时不做任何写),彻底恢复后重试经读前收养只补索引。"""

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
