#!/usr/bin/env python3
"""
fixer.py — repair the GeminiClient / OryvexClient source tree so that
`gradle setupCIWorkspace build` succeeds under ForgeGradle 2.1.

Root cause of the CI failure
----------------------------
    AsyncResourcePackGui.java:24: error: availableResourcePacks
        has private access in GuiScreenResourcePacks

In the 1.8.9 MCP mappings (stable_22) used by this project,
`GuiScreenResourcePacks.availableResourcePacks` is `private`, so the
subclass `com.oryvex.asyncload.gui.AsyncResourcePackGui` cannot call
`.clear()` on it. That single error aborts `:compileJava` and therefore
the entire `build` task.

The project already ships a complete, reflection-based implementation of
the same feature in the `com.example.asyncmenus` package. The
`com.oryvex.asyncload` package is a half-finished duplicate whose only
useful piece (per its own comments) is a TODO. Removing it is the
correct, minimal fix.

What this script does
---------------------
1. Backs up the repository (a timestamped .zip next to the repo root).
2. Deletes the broken duplicate package: `src/main/java/com/oryvex/`.
3. Rewrites `.github/workflows/build.yml` so the uploaded artifact is
   named `AsyncMenus-jar` and points at the correct output path
   (build/libs/*.jar, excluding -sources / -dev jars).
4. Validates that no other source file still references `com.oryvex`.
5. Prints a summary.

Usage
-----
    python fixer.py                  # operate on the script's directory
    python fixer.py --repo PATH      # operate on a specific repo
    python fixer.py --no-backup      # skip the zip backup
    python fixer.py --dry-run        # show what would change, do nothing
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BROKEN_PACKAGE_REL = Path("src") / "main" / "java" / "com" / "oryvex"
WORKFLOW_REL = Path(".github") / "workflows" / "build.yml"

# JAR artifact / workflow expectations
ARTIFACT_NAME = "AsyncMenus-jar"
ARTIFACT_PATH = "build/libs/*.jar"
ARTIFACT_EXCLUDE = "!build/libs/*-sources.jar"

# Text patterns that must not survive the cleanup
STALE_IMPORT_PATTERNS = [
    re.compile(r"^\s*import\s+com\.oryvex\.", re.MULTILINE),
    re.compile(r"\bcom\.oryvex\.asyncload\b"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log(msg: str) -> None:
    print(f"[fixer] {msg}")


def warn(msg: str) -> None:
    print(f"[fixer] WARNING: {msg}", file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    print(f"[fixer] ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def is_repo_root(path: Path) -> bool:
    """Heuristic: a Gradle/Forge mod repo has a build.gradle."""
    return (path / "build.gradle").is_file()


def find_repo_root(start: Path) -> Path:
    """Walk up from *start* until we find a directory containing build.gradle."""
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if is_repo_root(candidate):
            return candidate
    die(f"could not locate a repository (no build.gradle) above {start}")
    raise SystemExit(1)  # unreachable, keeps type checkers happy


def backup_repo(repo: Path) -> Path:
    """Create a timestamped .zip snapshot of the repo next to its parent."""
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = repo.parent / f"{repo.name}-backup-{stamp}.zip"
    log(f"creating backup -> {out}")
    skip_dirs = {".git", "build", "run", ".gradle", ".idea", "out", "bin"}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                p = Path(root) / name
                # Never archive the backup of a backup
                if p.resolve() == out.resolve():
                    continue
                zf.write(p, p.relative_to(repo))
    log(f"backup written ({out.stat().st_size // 1024} KiB)")
    return out


def remove_broken_package(repo: Path, dry_run: bool) -> bool:
    """Delete src/main/java/com/oryvex/. Returns True if anything was removed."""
    target = repo / BROKEN_PACKAGE_REL
    if not target.exists():
        log(f"already clean: {BROKEN_PACKAGE_REL} does not exist")
        return False
    log(f"removing broken duplicate package: {BROKEN_PACKAGE_REL}")
    if dry_run:
        return True
    shutil.rmtree(target)
    # Prune the now-empty com/ directory if it holds nothing else.
    com_dir = target.parent
    try:
        if com_dir.is_dir() and not any(com_dir.iterdir()):
            com_dir.rmdir()
            log(f"pruned empty directory: {com_dir.relative_to(repo)}")
    except OSError:
        pass
    return True


def validate_no_stale_refs(repo: Path) -> list[Path]:
    """Return a list of Java/Kotlin files that still import com.oryvex."""
    offenders: list[Path] = []
    src = repo / "src"
    if not src.is_dir():
        return offenders
    for path in src.rglob("*"):
        if path.suffix.lower() not in {".java", ".kt", ".groovy", ".scala"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(p.search(text) for p in STALE_IMPORT_PATTERNS):
            offenders.append(path)
    return offenders


def rewrite_workflow(repo: Path, dry_run: bool) -> bool:
    """
    Normalise the artifact upload block in .github/workflows/build.yml.

    Returns True if the file was (or would be) changed.
    """
    wf = repo / WORKFLOW_REL
    if not wf.is_file():
        warn(f"workflow not found: {WORKFLOW_REL} (skipping)")
        return False

    original = wf.read_text(encoding="utf-8")

    # Replace the "Upload jar" step's `with:` block wholesale.
    # We match from the step name down to the end of the `with:` block
    # (the block's indentation is 12 spaces for `name:`/`path:` etc.).
    step_re = re.compile(
        r"(?P<indent>[ \t]*)-[ \t]*name:[ \t]*Upload jar[ \t]*\r?\n"
        r"(?P<body>(?:[ \t]+[^\n]*\r?\n)+)",
        re.MULTILINE,
    )

    desired_step = (
        "        - name: Upload jar\n"
        "          uses: actions/upload-artifact@v4\n"
        "          with:\n"
        f"            name: {ARTIFACT_NAME}\n"
        "            path: |\n"
        f"              {ARTIFACT_PATH}\n"
        f"              {ARTIFACT_EXCLUDE}\n"
        "            if-no-files-found: error\n"
    )

    m = step_re.search(original)
    if not m:
        warn("could not locate the 'Upload jar' step; workflow left untouched")
        return False

    new_text = original[: m.start()] + desired_step + original[m.end():]

    if new_text == original:
        log("workflow already correct")
        return False

    log(f"rewriting {WORKFLOW_REL}")
    if not dry_run:
        wf.write_text(new_text, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fix the Oryvex/GeminiClient repo so `gradle build` succeeds.",
    )
    p.add_argument("--repo", type=Path, default=None,
                   help="repository root (default: script's directory, or nearest parent with build.gradle)")
    p.add_argument("--no-backup", action="store_true",
                   help="skip creating a .zip backup of the repo")
    p.add_argument("--dry-run", action="store_true",
                   help="report actions without modifying anything")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    start = args.repo if args.repo else Path(__file__).resolve().parent
    repo = find_repo_root(start) if args.repo is None else start.resolve()
    if not is_repo_root(repo):
        die(f"{repo} does not look like a repository (no build.gradle)")

    log(f"repository: {repo}")
    if args.dry_run:
        log("DRY RUN — nothing will be written")

    # 1) Backup
    if not args.no_backup and not args.dry_run:
        backup_repo(repo)
    elif args.no_backup:
        log("backup disabled (--no-backup)")

    # 2) Remove the broken duplicate mod
    removed = remove_broken_package(repo, args.dry_run)

    # 3) Rewrite the workflow to match the surviving mod
    wf_changed = rewrite_workflow(repo, args.dry_run)

    # 4) Sanity check: nothing should reference com.oryvex anymore
    offenders = validate_no_stale_refs(repo)
    if offenders:
        warn("the following files still reference 'com.oryvex':")
        for p in offenders:
            print(f"    {p.relative_to(repo)}", file=sys.stderr)
        warn("the build will likely still fail on :compileJava")
    else:
        log("no stale 'com.oryvex' references remain")

    # 5) Summary
    print()
    log("summary")
    log(f"  broken package removed : {removed}")
    log(f"  workflow rewritten     : {wf_changed}")
    log(f"  stale references       : {len(offenders)}")

    if args.dry_run:
        log("re-run without --dry-run to apply the changes")

    return 0 if not offenders else 2


if __name__ == "__main__":
    sys.exit(main())