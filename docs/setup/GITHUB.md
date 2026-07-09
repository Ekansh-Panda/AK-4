# Publishing Miori Core to GitHub

This guide walks you through pushing the Miori Core repository to GitHub safely, with no secrets or junk files leaked.

---

## 1. Pre-flight checks

First, confirm your local repo state is clean and no secret files are staged.

```bash
# 1. Confirm there are no unexpected changes
git status

# 2. Make sure .env is ignored (it should not appear in tracked files)
git ls-files | grep -E '\.env$|miori\.db' && echo "PROBLEM: secrets are tracked!" || echo "OK: no tracked .env or .db files"
```

If the second command prints "PROBLEM", a `.env` or `*.db` file has already been staged or committed. Remove it from git before continuing:

```bash
git rm --cached .env
# or for a database file:
git rm --cached miori.db
# then add a .gitignore entry if missing, and commit
```

**Why it matters:**  
- `services/core-api/.env.example` and `.env.example` at the root are committed and safe.  
- The real `.env`, `miori.db`, `node_modules/`, `.venv/`, and `data/` are all ignored by the existing `.gitignore`.

---

## 2. Create (or reuse) a GitHub repository

### Option A — Create a new repo on GitHub

1. Go to https://github.com/new  
2. Repository name: `miori-core` (or your preferred name)  
3. **Do NOT** initialize with a README, .gitignore, or License — we already have these locally.  
4. Click **Create repository**.  
5. Copy the HTTPS or SSH URL (e.g. `git@github.com:your-org/miori-core.git` or `https://github.com/your-org/miori-core.git`).

### Option B — Use an existing repo

If a repository already exists on GitHub (possibly with an empty README), skip to step 3.

---

## 3. Link the remote

```bash
# Replace <url> with your repo URL from step 2
git remote add origin <url>

# Verify
git remote -v
```

Expected output:

```
origin  <url> (fetch)
origin  <url> (push)
```

If `origin` already exists and points to the wrong place, fix it:

```bash
git remote set-url origin <url>
```

---

## 4. Stage files

Because `.gitignore` is solid, `git add .` (or `git add -A`) is safe here. It will include:

- `pnpm-lock.yaml` (required for reproducible installs)  
- `.env.example` files (safe, they have no real secrets)  
- `docs/`, `scripts/`, `packages/`, `apps/`, `services/`  
- `.gitattributes`  
- Everything else except ignored files listed in `.gitignore`

```bash
git add .

# Double-check what is staged
git status
```

**Important:** `node_modules/`, `.env`, `*.db`, `data/`, `.venv/`, `target/`, and `.cache/` should **not** appear in `git status` staged changes. If they do, your `.gitignore` is not matching — fix it before committing.

---

## 5. Commit

Use a clear conventional commit message:

```bash
git commit -m "feat: initial Miori Core v1.1.0 release"
```

If you already have earlier commits in the repo (e.g. from a previous push attempt), this will simply make a new commit on top of them.

---

## 6. Push to GitHub

```bash
# Ensure your local branch is named main
git branch -M main

# Push and set upstream
git push -u origin main
```

---

## 7. Verify on GitHub

After the push completes, open your repository in a browser and verify the following do **NOT** appear:

- `.env` (root or in any subdirectory)  
- `miori.db` or any `*.db` / `*.sqlite` / `*.sqlite3` files  
- `node_modules/`  
- `.venv/` or any Python cache directories  
- `data/` directories  
- `target/` directories  

You can also run this locally before pushing to double-check history:

```bash
git log --all --name-only | grep -E '\.env$|\.db$' && echo "Leak found in history!" || echo "History looks clean"
```

---

## 8. Helper script (optional but recommended)

There is also an idempotent helper script at `scripts/github-push.sh` that automates the repetitive checks and push steps above. It is safe to re-run; it will not force-push or destroy history.

```bash
bash scripts/github-push.sh "git@github.com:your-org/miori-core.git" "feat: initial Miori Core v1.1.0 release"
```

If your remote URL contains the `ghp_` token prefix or other sensitive material, do **not** share the command line publicly — use an SSH URL or GitHub CLI instead.

---

## Troubleshooting

### "Large file rejected"

GitHub rejects files over ~100 MB. If you accidentally staged a large artifact:

```bash
# Remove from the index (keeps it on disk)
git rm --cached path/to/large-file

# Amend the last commit (if you haven't pushed yet)
git commit --amend -m "feat: initial Miori Core v1.1.0 release"

# Force-push only if you are certain nobody else has pulled the bad commit
git push --force-with-lease
```

### "Already has a git history" / non-empty repository

If the GitHub repo already contains commits (e.g. a README added via the web UI), you can either:

- Rebase safely:
  ```bash
  git pull --rebase origin main
  git push -u origin main
  ```
- Or merge:
  ```bash
  git merge origin/main --allow-unrelated-histories
  git push -u origin main
  ```

### "Authentication failed"

You must authenticate with GitHub. Recommended methods:

1. **GitHub CLI** (easiest):
   ```bash
   gh auth login
   ```
   Then use the remote URL it suggests (usually `git@github.com:...`).

2. **SSH key**: Ensure `~/.ssh/id_ed25519` (or similar) is added to your GitHub account, then use the SSH remote URL.

3. **Classic token** (HTTPS): Use a **fine-grained personal access token** with `repo` scope. Never embed the token in scripts.

```bash
git remote set-url origin https://github.com/your-org/miori-core.git
git push -u origin main
# Git will prompt for username (your GH username) and password (paste the token)
```

### "Permission denied (publickey)" or "Could not read from remote repository"

Your SSH key is not set up or not added to GitHub. Run `ssh -T git@github.com` to test. Follow GitHub's guide to add a new SSH key.

---

## Summary

```bash
git status
git ls-files | grep -E '\.env$|miori\.db' && echo "PROBLEM" || echo "OK"
git remote add origin git@github.com:your-org/miori-core.git
git remote -v
git add .
git status
git commit -m "feat: initial Miori Core v1.1.0 release"
git branch -M main
git push -u origin main
```

After pushing, confirm on GitHub that `.env`, `*.db`, `node_modules`, `.venv`, `data/`, and `target/` are absent.
