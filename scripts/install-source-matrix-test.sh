#!/usr/bin/env bash
# Verify same-name source switching and independent project scopes in temporary consumers.
#
#   scripts/install-source-matrix-test.sh [repository-path]
#
# All installations stay under a new temporary directory; this script never uses --global.

set -euo pipefail

REPO="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
REPO="$(cd "$REPO" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/mgs-source-install.XXXXXX")"
FORK_COMMIT='f3c726f275fa1ac59fef33732e527dded6d62479'
FORK_SPEC="LC-86/mattpocockskills#$FORK_COMMIT@writing-for-agents"
FORK_HASH='a4db59f7773be1facc7dbfb223c6c9aeec7932dcc2515f331f9a41de82e6dced'
LOCAL_SKILL="$REPO/skills/writing-for-agents"

# shellcheck source=resolve-skills-cli.sh
. "$SCRIPT_DIR/resolve-skills-cli.sh"
resolve_skills_cli "${SKILLS_CLI_VERSION:-1.7.0}"

run_install() {
  local consumer="$1" label="$2"
  shift 2
  mkdir -p "$consumer"
  if ! (cd "$consumer" && "${SKILLS_CLI_CMD[@]}" add "$@" --agent universal --copy -y) \
      >"$WORK/$label.log" 2>&1; then
    printf '%s\n' "FAIL $label; CLI output:" >&2
    tail -40 "$WORK/$label.log" >&2
    return 1
  fi
}

target_for() { printf '%s/.agents/skills/writing-for-agents' "$1"; }
hash_file() { shasum -a 256 "$1" | cut -d ' ' -f 1; }

assert_source() {
  local lock="$1" expected_source="$2" expected_ref="$3"
  python3.12 - "$lock" "$expected_source" "$expected_ref" <<'PY'
import json, sys
from pathlib import Path
lock = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
record = lock["skills"]["writing-for-agents"]
actual_source = record["source"]
if not sys.argv[3]:
    path = Path(actual_source)
    if not path.is_absolute():
        path = Path(sys.argv[1]).parent / path
    actual_source = str(path.resolve())
    expected_source = str(Path(sys.argv[2]).resolve())
else:
    expected_source = sys.argv[2]
assert actual_source == expected_source, record
assert record.get("ref", "") == sys.argv[3], record
assert record["computedHash"], record
print(f"lock source={record['source']} ref={record.get('ref', '')} hash={record['computedHash']}")
PY
}

assert_single_target() {
  local consumer="$1" target
  target="$(target_for "$consumer")"
  [ -f "$target/SKILL.md" ] || { printf 'missing target: %s\n' "$target" >&2; return 1; }
  [ "$(find "$consumer/.agents/skills" -mindepth 1 -maxdepth 1 -type d -name writing-for-agents | wc -l | tr -d ' ')" = "1" ]
}

printf 'Temporary consumers: %s\n' "$WORK"

game_scope="$WORK/game-project"
generic_scope="$WORK/generic-project"
run_install "$game_scope" game-local "$REPO" --skill writing-for-agents
run_install "$generic_scope" generic-fork "$FORK_SPEC"
assert_single_target "$game_scope"
assert_single_target "$generic_scope"
game_hash="$(hash_file "$(target_for "$game_scope")/SKILL.md")"
generic_hash="$(hash_file "$(target_for "$generic_scope")/SKILL.md")"
[ "$game_hash" = "$(hash_file "$LOCAL_SKILL/SKILL.md")" ]
[ "$generic_hash" != "$game_hash" ]
python3.12 - "$generic_scope/skills-lock.json" "$FORK_HASH" <<'PY'
import json, sys
from pathlib import Path
lock = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
record = lock["skills"]["writing-for-agents"]
assert record["computedHash"] == sys.argv[2], record
PY
assert_source "$game_scope/skills-lock.json" "$REPO" ""
assert_source "$generic_scope/skills-lock.json" "LC-86/mattpocockskills" "$FORK_COMMIT"
python3.12 "$SCRIPT_DIR/verify-writing-for-agents-install.py" \
  --installed-dir "$(target_for "$game_scope")" --lock-file "$game_scope/skills-lock.json" \
  --reference-dir "$LOCAL_SKILL" >/dev/null
printf 'PASS installed-copy inspector binds a local source record to its checkout\n'
# Model the CLI 1.7.0 lock shape for a GitHub default-branch install. The current
# Issue #87 changes are not published, so the check uses the equivalent package
# installed locally plus the verified origin checkout as its clean reference.
python3.12 - "$game_scope/skills-lock.json" <<'PY'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
record = data["skills"]["writing-for-agents"]
record["source"] = "LC-86/MyGameStudio"
record["sourceType"] = "github"
record["skillPath"] = "skills/writing-for-agents/SKILL.md"
record.pop("ref", None)
path.write_text(json.dumps(data), encoding="utf-8")
PY
python3.12 "$SCRIPT_DIR/verify-writing-for-agents-install.py" \
  --installed-dir "$(target_for "$game_scope")" --lock-file "$game_scope/skills-lock.json" \
  --reference-dir "$LOCAL_SKILL" >/dev/null
printf 'PASS installed-copy inspector accepts the verified GitHub default-branch lock shape\n'
printf 'PASS separate project scopes keep the GameStudio and fork copies\n'

local_then_fork="$WORK/switch-local-to-fork"
run_install "$local_then_fork" switch-local-first "$REPO" --skill writing-for-agents
python3.12 "$SCRIPT_DIR/verify-writing-for-agents-install.py" \
  --installed-dir "$(target_for "$local_then_fork")" \
  --lock-file "$local_then_fork/skills-lock.json" --reference-dir "$LOCAL_SKILL" >/dev/null
printf 'PASS local copy checked before switching to the fork source\n'
run_install "$local_then_fork" switch-fork-second "$FORK_SPEC"
assert_single_target "$local_then_fork"
[ "$(hash_file "$(target_for "$local_then_fork")/SKILL.md")" = "$generic_hash" ]
assert_source "$local_then_fork/skills-lock.json" "LC-86/mattpocockskills" "$FORK_COMMIT"
printf 'PASS same-scope local-to-fork switch replaces one target and updates the lock\n'

fork_then_local="$WORK/switch-fork-to-local"
run_install "$fork_then_local" switch-fork-first "$FORK_SPEC"
python3.12 "$SCRIPT_DIR/verify-writing-for-agents-install.py" \
  --installed-dir "$(target_for "$fork_then_local")" \
  --lock-file "$fork_then_local/skills-lock.json" \
  --reference-dir "$(target_for "$generic_scope")" >/dev/null
printf 'PASS fork copy checked before switching to the local source\n'
run_install "$fork_then_local" switch-local-second "$REPO" --skill writing-for-agents
assert_single_target "$fork_then_local"
[ "$(hash_file "$(target_for "$fork_then_local")/SKILL.md")" = "$game_hash" ]
assert_source "$fork_then_local/skills-lock.json" "$REPO" ""
printf 'PASS same-scope fork-to-local switch replaces one target and updates the lock\n'

installed_edit_scope="$WORK/installed-local-edit"
run_install "$installed_edit_scope" installed-edit-fork "$FORK_SPEC"
installed_target="$(target_for "$installed_edit_scope")"
printf '\nLocal consumer test edit.\n' >> "$installed_target/SKILL.md"
if python3.12 "$SCRIPT_DIR/verify-writing-for-agents-install.py" \
    --installed-dir "$installed_target" --lock-file "$installed_edit_scope/skills-lock.json" \
    --reference-dir "$(target_for "$generic_scope")" --show-diff \
    >"$WORK/installed-edit-guard.log" 2>&1; then
  printf 'FAIL installed-copy inspector missed a local edit\n' >&2
  exit 1
fi
grep -q 'source=' "$WORK/installed-edit-guard.log"
grep -q 'modified: SKILL.md' "$WORK/installed-edit-guard.log"
grep -q '+Local consumer test edit.' "$WORK/installed-edit-guard.log"
grep -q 'Local consumer test edit.' "$installed_target/SKILL.md"
printf 'PASS installed-copy inspector identifies the source, prints the local diff, and preserves the change\n'

guard_root="$WORK/local-edit-guard"
mkdir -p "$guard_root/skills" "$guard_root/scripts"
cp -R "$LOCAL_SKILL" "$guard_root/skills/writing-for-agents"
cp "$SCRIPT_DIR/sync-writing-for-agents.py" "$guard_root/scripts/sync-writing-for-agents.py"
printf '\nLocal test-only edit.\n' >> "$guard_root/skills/writing-for-agents/SKILL.md"
if python3.12 "$guard_root/scripts/sync-writing-for-agents.py" --write --repo-root "$guard_root" \
    >"$WORK/local-edit-guard.log" 2>&1; then
  printf 'FAIL generator overwrote a modified package without --force\n' >&2
  exit 1
fi
grep -q 'inspect and preserve local changes' "$WORK/local-edit-guard.log"
grep -q 'Local test-only edit.' "$guard_root/skills/writing-for-agents/SKILL.md"
printf 'PASS generator reports and preserves a locally modified distribution copy\n'

printf 'PASS source matrix complete; temporary evidence remains at %s\n' "$WORK"
