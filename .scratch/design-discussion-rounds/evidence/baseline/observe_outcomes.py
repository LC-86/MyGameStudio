#!/usr/bin/env python3
"""对照场景约定回读项目终态,供 measure_module_run 的 observed_outcomes 使用。"""

import hashlib
import json
import sys
from pathlib import Path


def sha_map(root: Path) -> dict[str, str]:
    out = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if ".git" in path.parts:
            continue
        rel = "./" + path.relative_to(root).as_posix()
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def changed_paths(baseline: Path, final_root: Path) -> list[str]:
    before = {}
    for line in baseline.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        before[rel] = digest
    after = sha_map(final_root)
    changed = []
    for rel, digest in after.items():
        if before.get(rel) != digest:
            changed.append(rel[2:] if rel.startswith("./") else rel)
    return sorted(changed)


def contains(root: Path, rel: str, *needles: str) -> bool:
    path = root / rel
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return all(needle in text for needle in needles)


def main() -> int:
    kind, project, baseline, out = sys.argv[1:5]
    root = Path(project)
    written = changed_paths(Path(baseline), root)
    notes = []
    if kind == "new-design":
        gd = contains(root, "docs/mygamestudio/GAME_DESIGN.md", "每日", "步数")
        dec = any("records/decision-" in path and "map" not in path for path in written)
        project_changed = "docs/mygamestudio/PROJECT.md" in written
        semantics = bool(gd and dec and not project_changed)
        if not dec:
            notes.append("缺少决定记录")
        if not gd:
            notes.append("GAME_DESIGN 未纳入每日挑战可执行要点")
        if project_changed:
            notes.append("PROJECT 被设计入口改写,超出本场景授权")
    elif kind == "existing-change":
        gd = contains(root, "docs/mygamestudio/GAME_DESIGN.md", "海鸥", "连击")
        dec = any("records/decision-" in path and "map" not in path for path in written)
        project_changed = "docs/mygamestudio/PROJECT.md" in written
        tech_changed = "docs/mygamestudio/TECH_DESIGN.md" in written
        semantics = bool(gd and dec and not project_changed and not tech_changed)
        if not dec:
            notes.append("缺少决定记录")
        if not gd:
            notes.append("GAME_DESIGN 未同步海鸥与连击关系")
        if project_changed:
            notes.append("PROJECT 被改写")
        if tech_changed:
            notes.append("TECH_DESIGN 被改写")
    else:
        raise SystemExit(f"未知场景 {kind}")
    payload = {
        "written_paths": written,
        "semantics_matched": semantics,
        "notes": "; ".join(notes),
    }
    Path(out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
