#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO_URL="https://github.com/simpleedits121-ui/Jarvis-sandbox-.git"
BRANCH="main"

cd "$ROOT"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: This folder has no Git history. Extract/overlay these files into your existing JarvisSandbox clone first."
  exit 2
fi

git config --global --add safe.directory "$ROOT" 2>/dev/null || true
if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

VERSION="$(sed -n 's/.*versionName = \"\([^\"]*\)\".*/\1/p' app/build.gradle.kts | head -n1)"
if [[ "$VERSION" != "0.5.0" ]]; then
  echo "ERROR: Refusing to push stale/wrong app version. Found versionName='$VERSION'; expected 0.5.0."
  exit 3
fi
if ! grep -q 'fun ForgeViewport' app/src/main/java/com/jarvis/sandbox/SpatialForge.kt; then
  echo "ERROR: 3D viewport source is missing. Refusing to push."
  exit 4
fi

if ! git config user.name >/dev/null; then
  read -r -p "Git commit name: " GIT_NAME
  git config user.name "$GIT_NAME"
fi
if ! git config user.email >/dev/null; then
  read -r -p "Git commit email (GitHub noreply email is fine): " GIT_EMAIL
  git config user.email "$GIT_EMAIL"
fi

# Commit local changes first, then replay them on the latest remote main.
git add -A
if git diff --cached --quiet; then
  echo "No local changes detected. The v0.5.0 files may not have been copied into this repository."
  echo "Current commit: $(git log -1 --oneline)"
  exit 5
fi

git commit -m "Build JARVIS Spatial Forge v0.5.0 3D viewport"
git fetch origin "$BRANCH"
git pull --rebase origin "$BRANCH"
git push -u origin "$BRANCH"

LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_SHA="$(git ls-remote origin "refs/heads/$BRANCH" | awk '{print $1}')"
if [[ "$LOCAL_SHA" != "$REMOTE_SHA" ]]; then
  echo "ERROR: Push verification failed. Local=$LOCAL_SHA Remote=$REMOTE_SHA"
  exit 6
fi

echo
echo "SUCCESS: v$VERSION pushed to origin/$BRANCH ($LOCAL_SHA)"
echo "GitHub Actions should start automatically because the workflow listens to pushes on main."
echo "Check: https://github.com/simpleedits121-ui/Jarvis-sandbox-/actions"
