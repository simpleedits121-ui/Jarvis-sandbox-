#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_URL="https://github.com/simpleedits121-ui/Jarvis-sandbox-.git"

# Android shared storage can trigger Git's dubious-ownership protection.
git config --global --add safe.directory "$REPO_DIR" 2>/dev/null || true
cd "$REPO_DIR"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
fi

git branch -M main
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

if ! git config user.name >/dev/null; then
  read -r -p "Git commit name: " GIT_NAME
  git config user.name "$GIT_NAME"
fi
if ! git config user.email >/dev/null; then
  read -r -p "Git commit email (GitHub noreply email is fine): " GIT_EMAIL
  git config user.email "$GIT_EMAIL"
fi

git add -A
if git diff --cached --quiet; then
  echo "No new staged changes."
else
  git commit -m "Build JARVIS Sandbox v0.2 foundation"
fi

git push -u origin main
echo "Push complete. Check the GitHub Actions tab for the APK build."
