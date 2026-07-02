#!/usr/bin/env python3
"""Miori Core — donor repo analyzer.

Scans the ``integrations/`` directory for cloned donor repositories and emits a
lightweight feature/stack inventory as Markdown. This is a *mechanical* first
pass to seed the human-written analyses in ``docs/repo-analysis/`` — it does not
attempt to understand the code, only to surface stack signals and entry points.

Usage:
    python scripts/analyze_repos.py
    python scripts/analyze_repos.py --root integrations --out docs/repo-analysis/_auto

Pure standard library — no dependencies, safe to run on low-end machines.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Signal files that hint at a repo's stack.
STACK_SIGNALS = {
    "package.json": "Node / JavaScript / TypeScript",
    "pnpm-lock.yaml": "pnpm workspace",
    "requirements.txt": "Python (pip)",
    "pyproject.toml": "Python (PEP 621)",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "pom.xml": "Java (Maven)",
    "Dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "tauri.conf.json": "Tauri desktop",
    "next.config.js": "Next.js",
    "vite.config.ts": "Vite",
}

CODE_EXTENSIONS = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".c": "C",
    ".cpp": "C++",
}

IGNORE_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__"}


def analyze_repo(repo: Path) -> dict:
    """Produce a small inventory dict for a single repo directory."""
    signals: list[str] = []
    lang_counts: dict[str, int] = {}
    readme: str | None = None

    for path in repo.rglob("*"):
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.is_dir():
            continue
        name = path.name
        if name in STACK_SIGNALS and STACK_SIGNALS[name] not in signals:
            signals.append(STACK_SIGNALS[name])
        if name.lower().startswith("readme") and readme is None:
            readme = str(path.relative_to(repo))
        ext = path.suffix.lower()
        if ext in CODE_EXTENSIONS:
            lang_counts[CODE_EXTENSIONS[ext]] = lang_counts.get(CODE_EXTENSIONS[ext], 0) + 1

    top_langs = sorted(lang_counts.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "name": repo.name,
        "stack_signals": signals,
        "languages": top_langs,
        "readme": readme,
    }


def to_markdown(info: dict) -> str:
    langs = ", ".join(f"{lang} ({n})" for lang, n in info["languages"][:6]) or "—"
    signals = ", ".join(info["stack_signals"]) or "—"
    readme = info["readme"] or "not found"
    return (
        f"## {info['name']}\n\n"
        f"- **Stack signals:** {signals}\n"
        f"- **Top languages:** {langs}\n"
        f"- **README:** {readme}\n\n"
        f"> _Auto-generated stub. Replace with a full analysis in "
        f"`docs/repo-analysis/{info['name']}.md`._\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory donor repos for Miori Core.")
    parser.add_argument("--root", default="integrations", help="Directory holding cloned donor repos.")
    parser.add_argument("--out", default="docs/repo-analysis/_auto", help="Output directory for stubs.")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"✗ root '{root}' does not exist. Clone donor repos into it first.")
        return 1

    repos = [p for p in sorted(root.iterdir()) if p.is_dir() and p.name not in IGNORE_DIRS]
    # Skip placeholder dirs that only contain a README/.gitkeep.
    repos = [p for p in repos if any(c.name not in {"README.md", ".gitkeep"} for c in p.iterdir())]

    if not repos:
        print(f"No cloned repos found under '{root}'. (Placeholders are ignored.)")
        print("Clone donor repos into integrations/<name>/ then re-run.")
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries = []
    for repo in repos:
        info = analyze_repo(repo)
        summaries.append(info)
        (out_dir / f"{repo.name}.md").write_text(to_markdown(info), encoding="utf-8")
        print(f"✓ {repo.name}: {', '.join(info['stack_signals']) or 'no stack signals'}")

    (out_dir / "inventory.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"\nWrote {len(summaries)} stub(s) + inventory.json to {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
