#!/usr/bin/env python3
"""后端选项对象(issue #73):transport/api_base/cache_dir/config_rel 参数簇的
唯一定义。

这组参数此前逐个铺在 mgs_records、mgs_snapshot、mgs_safe_switch 与
mgs_github_material_migration 的公共签名与内部私有助手上;本模块把该簇
收拢为不可变的 ``BackendOptions``,并集中「由已解析配置构造 GitHub
adapter」的唯一定义 ``github_backend_for``。公开入口的既有 keyword 参数
(``transport=`` / ``api_base=`` / ``cache_dir=`` / ``config_rel=``)保持
不变:入口组装选项对象后逐层透传,外部行为不变。
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mgs_record_model import RecordsError  # noqa: E402
from mgs_record_source import DEFAULT_CONFIG_REL  # noqa: E402


@dataclass(frozen=True)
class BackendOptions:
    """一次公共调用透传给后端构造的选项簇。

    ``transport`` 是注入的传输替身(测试与受控运行用);``api_base`` 与
    ``cache_dir`` 只在未注入 transport 时参与默认传输构造;``config_rel``
    指向现行协作配置。入口组装后不再改写。
    """

    config_rel: str = DEFAULT_CONFIG_REL
    transport: Any = None
    api_base: str | None = None
    cache_dir: Path | str | None = None


def github_backend_for(config: dict, options: BackendOptions):
    """由本次已解析配置与选项簇构造 GitHub adapter(唯一定义)。

    后端不是 github-issues 时按既有文案拒绝;transport 缺省时按配置解析
    api_base 并从环境取令牌构造默认传输。延迟导入避免与 mgs_github 的
    循环依赖。
    """

    import mgs_github  # noqa: PLC0415 - 延迟导入避免循环依赖

    if config["backend"] != "github-issues":
        raise RecordsError(f"当前后端为 {config['backend']},不是 github-issues")
    transport = options.transport
    if transport is None:
        transport = mgs_github.UrllibTransport(
            api_base=mgs_github.api_base_for(config, options.api_base),
            token=mgs_github.token_from_env())
    return mgs_github.GithubBackend(config, transport, options.cache_dir)
