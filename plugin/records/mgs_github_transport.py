#!/usr/bin/env python3
"""GitHub Issues 后端的远端传输接缝与错误身份(票 18)。

集中 GitHub 适配器 ``mgs_github`` 与发布恢复 module ``mgs_result_publication``
共同依赖的最底层接缝:GitHub 记录错误与传输故障的身份、真实 HTTP 传输
(stdlib urllib)、API 端点与令牌解析,以及仓库坐标的路径形态。它们不属于
任何单一业务操作,单独成层后发布恢复不必反向依赖业务适配器即可处理
「把评论写到哪里、请求怎么发、故障怎么分」。

依赖纪律(与第一、四阶段设计一致):
- 只依赖标准库与共同记录错误身份 ``mgs_record_model.RecordsError``;
- 不导入 ``mgs_github``(业务操作适配器)或 ``mgs_result_publication``
  (发布恢复),二者正向依赖本模块,避免循环导入与职责回指;
- ``GithubRecordsError``/``TransportError`` 的唯一定义在此,``mgs_github``
  重导出这两个名字,现有 ``mgs_github.GithubRecordsError`` /
  ``mgs_github.TransportError`` 捕获分支与身份保持不变。
"""

from __future__ import annotations

import http.client
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_model import RecordsError  # noqa: E402

TOKEN_ENVS = ("MGS_GITHUB_TOKEN", "GH_TOKEN")
# 测试接缝:覆盖 API 端点(默认按 host 推导);验收与本地替身使用
API_BASE_ENV = "MGS_GH_API_BASE"
DEFAULT_TIMEOUT = 10.0


class GithubRecordsError(RecordsError):
    """GitHub 后端配置缺失、坐标无效、未授权或远端操作失败。"""


class TransportError(Exception):
    """传输层故障。kind: offline(连不上)/ timeout(超时,结果不确定)/
    bad_response(应答不可解析)。"""

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


# ---------- 端点与令牌(公开接缝) ----------

def default_api_base(host: str) -> str:
    """host → REST API 端点:github.com 用 api.github.com,
    其他 host(GitHub Enterprise 约定)用 https://<host>/api/v3。"""

    if host == "github.com":
        return "https://api.github.com"
    return f"https://{host}/api/v3"


def api_base_for(config: dict, override: str | None = None) -> str:
    """API 端点:override/环境变量优先,否则按 host 推导。

    无仓库坐标的配置(如本地后端项目做交接可达检查)退回 github.com
    端点——可达检查访问的是绝对引用 URL,端点仅作兜底。
    """

    base = (override or os.environ.get(API_BASE_ENV, "")).strip()
    if base:
        return base
    host = ((config.get("repo") or {}).get("host")) or "github.com"
    return default_api_base(host)


def token_from_env() -> str | None:
    for name in TOKEN_ENVS:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def repo_path(repo: dict) -> str:
    return f"/repos/{repo['owner']}/{repo['repo']}"


def repo_str(repo: dict) -> str:
    """仓库坐标的人读形态(host/owner/repo;草稿、来源、迁移清单共用)。"""

    return f"{repo['host']}/{repo['owner']}/{repo['repo']}"


# ---------- 传输层 ----------

class UrllibTransport:
    """真实 HTTP 传输(stdlib urllib)。供可信调度/CLI/替身验收使用。"""

    def __init__(self, api_base: str, token: str | None,
                 timeout: float = DEFAULT_TIMEOUT) -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.timeout = timeout

    def request(self, method: str, path: str, body: dict | None = None,
                *, auth: bool = True) -> tuple[int, object]:
        """执行一次 API 请求。auth=False 时不携带凭据(交接可达检查访问
        CONFIG 引用指向的第三方地址,凭据只属于 API 端点,不得外发)。"""

        # 绝对 URL(交接可达检查的引用地址)直接访问,不拼接 api_base
        url = (path if path.startswith(("http://", "https://"))
               else f"{self.api_base}{path}")
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/vnd.github+json",
                   "X-Requested-With": "mgs-records"}
        if self.token and auth:
            headers["Authorization"] = f"Bearer {self.token}"
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                status = resp.status
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace") if exc.fp else ""
            return exc.code, _safe_json(raw)
        except (http.client.RemoteDisconnected, ConnectionResetError,
                BrokenPipeError) as exc:
            # 连接在应答前被断开:请求可能已生效,结果不确定 → 按超时路径
            # 先回读再重试(避免重复创建)
            raise TransportError("timeout", f"connection dropped: {exc}") from exc
        except URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                raise TransportError("timeout", str(reason)) from exc
            raise TransportError("offline", str(reason)) from exc
        except TimeoutError as exc:
            raise TransportError("timeout", str(exc)) from exc
        return status, _safe_json(raw)


def _safe_json(raw: str) -> object:
    try:
        return json.loads(raw) if raw else None
    except ValueError:
        return raw
