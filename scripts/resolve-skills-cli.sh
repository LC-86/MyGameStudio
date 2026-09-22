# shellcheck shell=bash
# 解析官方 skills CLI 的可执行入口。
#
#   source scripts/resolve-skills-cli.sh
#   resolve_skills_cli 1.7.0 || exit 1
#   "${SKILLS_CLI_CMD[@]}" --version
#
# 取数顺序：显式 SKILLS_CLI 路径 -> USE_NPX=1 时用 npx -> 在 npx 缓存里找版本匹配的入口
# -> 回落到 npx。缓存目录名是内容哈希，随机器与安装历史变化，因此绝不绑定某个固定哈希。
# 每一步失败都给出原因，不吞掉原始错误。

resolve_skills_cli() {
  local want="${1:?需要 CLI 版本}"
  SKILLS_CLI_CMD=()

  if [ -n "${SKILLS_CLI:-}" ]; then
    if [ ! -f "$SKILLS_CLI" ]; then
      printf 'SKILLS_CLI 指向不存在的文件：%s\n' "$SKILLS_CLI" >&2
      return 2
    fi
    SKILLS_CLI_CMD=(node "$SKILLS_CLI")
    return 0
  fi

  if [ "${USE_NPX:-}" = "1" ]; then
    if ! command -v npx >/dev/null 2>&1; then
      printf 'USE_NPX=1，但 PATH 中没有 npx（需要 Node.js 与 npm）\n' >&2
      return 3
    fi
    SKILLS_CLI_CMD=(npx --yes "skills@$want")
    return 0
  fi

  if command -v node >/dev/null 2>&1; then
    local pkg v
    for pkg in "$HOME"/.npm/_npx/*/node_modules/skills/package.json; do
      [ -f "$pkg" ] || continue
      v="$(node -e 'process.stdout.write(String(require(process.argv[1]).version ?? ""))' \
             "$pkg" 2>/dev/null)"
      if [ "$v" = "$want" ] && [ -f "${pkg%/package.json}/bin/cli.mjs" ]; then
        SKILLS_CLI_CMD=(node "${pkg%/package.json}/bin/cli.mjs")
        return 0
      fi
    done
    printf 'npx 缓存中没有 skills@%s 的入口，改用 npx 获取\n' "$want" >&2
  else
    printf 'PATH 中没有 node，改用 npx 获取 skills@%s\n' "$want" >&2
  fi

  if command -v npx >/dev/null 2>&1; then
    SKILLS_CLI_CMD=(npx --yes "skills@$want")
    return 0
  fi
  printf '无法取得 skills CLI：既没有匹配的 npx 缓存，也没有 npx 可用。\n' \
         '安装 Node.js，或设 SKILLS_CLI=<cli.mjs 路径> 指向已缓存的入口。\n' >&2
  return 4
}
