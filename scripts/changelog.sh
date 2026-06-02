#!/bin/bash
#
# changelog.sh - Generate changelog from git commits
#
# Usage:
#   ./changelog.sh [since_tag] [to_tag]
#   ./changelog.sh v0.9.0 v0.10.0
#   ./changelog.sh  # compares latest tag to HEAD
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SINCE="${1:-}"
TO="${2:-HEAD}"

cd "$ROOT_DIR"

if [ -z "$SINCE" ]; then
    PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
    if [ -n "$PREV_TAG" ]; then
        SINCE="$PREV_TAG"
    else
        SINCE=$(git rev-list --max-parents=0 HEAD 2>/dev/null | tail -1)
    fi
fi

echo "## Changes since $SINCE"
echo ""

COMMITS=$(git log "$SINCE..$TO" --oneline --format='%s' 2>/dev/null | sed 's/^/  /')

if [ -z "$COMMITS" ]; then
    echo "(no commits found)"
else
    echo "$COMMITS"
fi

echo ""
echo "Full commit history:"
echo ""
git log "$SINCE..$TO" --oneline 2>/dev/null | sed 's/^/   /' || echo "(no commits)"