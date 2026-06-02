#!/bin/bash
#
# prepare-release.sh - Prepare a release by updating VERSION and changelog
#
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CURRENT_VERSION=$(cat "$ROOT_DIR/VERSION" 2>/dev/null || echo "0.0.0")

NEW_VERSION="${1:-}"

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <version>"
    echo "Current version: $CURRENT_VERSION"
    echo "Example: $0 0.11.0"
    exit 1
fi

if [[ ! "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Version must be in format X.Y.Z (e.g., 0.11.0)"
    exit 1
fi

echo "Preparing release v$NEW_VERSION..."

echo "$NEW_VERSION" > "$ROOT_DIR/VERSION"
echo "Updated VERSION to $NEW_VERSION"

CHANGELOG="$ROOT_DIR/docs/CHANGELOG.md"
if [ -f "$CHANGELOG" ]; then
    if grep -q "## \[Unreleased\]" "$CHANGELOG"; then
        sed -i "s/## \[Unreleased\]/## [Unreleased]\n\n## [v$NEW_VERSION] - $(date +%Y-%m-%d)/" "$CHANGELOG"
        echo "Updated CHANGELOG.md with v$NEW_VERSION"
    fi
fi

echo ""
echo "Release v$NEW_VERSION prepared. Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Commit: git add -A && git commit -m 'Release v$NEW_VERSION'"
echo "  3. Tag: git tag v$NEW_VERSION"
echo "  4. Push: git push && git push --tags"
echo ""
echo "Or use 'make release VERSION=$NEW_VERSION' to do all at once"