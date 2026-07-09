#!/usr/bin/env bash
set -euo pipefail

REMOTE_URL="${1:-}"
COMMIT_MSG="${2:-feat: initial Miori Core v1.1.0 release}"

if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "ERROR: Not inside a git repository."
    exit 1
fi

# 1. Pre-flight: .env should not be tracked
if git ls-files --error-unmatch .env > /dev/null 2>&1; then
    echo "ERROR: .env is already tracked by git."
    echo "Remove it with this exact command before proceeding:"
    echo "  git rm --cached .env"
    echo "Then commit again so the ignore rule takes effect."
    exit 1
fi

# 2. Confirm pnpm-lock.yaml exists in the repo root
if [[ ! -f "pnpm-lock.yaml" ]]; then
    echo "ERROR: pnpm-lock.yaml is missing from the repo root."
    exit 1
fi

if git check-ignore -q pnpm-lock.yaml 2>/dev/null; then
    echo "WARNING: pnpm-lock.yaml is ignored by .gitignore — this will break reproducible installs."
    exit 1
fi

# 3. Optionally link remote origin
if [[ -n "$REMOTE_URL" ]]; then
    if git remote | grep -q '^origin$'; then
        echo "Remote 'origin' already set."
    else
        git remote add origin "$REMOTE_URL"
        echo "Added remote origin: $REMOTE_URL"
    fi
else
    echo "No remote URL supplied (skipping remote setup)."
fi

echo "Configured remotes:"
git remote -v

# 4. Stage everything (.gitignore protects secrets and junk)
git add -A

# 5. Commit only if there are staged changes
if ! git diff --cached --quiet; then
    git commit -m "$COMMIT_MSG"
    echo "Committed: $COMMIT_MSG"
else
    echo "Nothing new to commit."
fi

# 6. Push to main if origin exists
if git remote | grep -q '^origin$'; then
    git branch -M main
    git push -u origin main
    echo "Pushed to origin/main."
else
    echo "No 'origin' remote configured — nothing to push."
    echo "To finish later, run:"
    echo "  $0 <remote-url> \"${COMMIT_MSG}\""
    exit 0
fi
