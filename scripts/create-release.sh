#!/bin/bash
#
# create-release.sh - Create a tagged release and trigger CD pipeline
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

NEW_VERSION="${1:-}"

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.11.0"
    exit 1
fi

if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format X.Y.Z (e.g., 0.11.0)"
    exit 1
fi

TAG_NAME="v$NEW_VERSION"

echo "Creating release v$NEW_VERSION..."

cd "$ROOT_DIR"

git fetch --tags 2>/dev/null || true

if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "Error: Tag $TAG_NAME already exists"
    exit 1
fi

"${SCRIPT_DIR}/prepare-release.sh" "$NEW_VERSION"

git add -A
git commit -m "Release $TAG_NAME"
git tag "$TAG_NAME"

echo ""
echo "Release $TAG_NAME created and committed"
echo "Pushing to remote..."
git push origin master
git push origin "$TAG_NAME"

echo ""
echo "CD pipeline triggered. Monitor at:"
echo "  https://github.com/$(
    git remote geturl origin 2>/dev/null | sed 's/.*github.com[/:]//' | sed 's/\.git$//'
    )/actions"