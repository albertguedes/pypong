#!/bin/sh
# pre-commit hook: detect secrets before commit
# Install: cp scripts/pre-commit.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

echo "Running pre-commit security scan..."

# Check for .env file staged
if git diff --cached --name-only | grep -qE "^\.env$"; then
    echo "ERROR: .env file is staged — remove it from staging (it must never be committed)"
    exit 1
fi

# Secret patterns
PATTERNS="JIRA_API_TOKEN|ATLASSIAN_API_TOKEN|ATATT3xFf|ghp_|gho_|github_pat_|aws_access_key|aws_secret_access_key|-----BEGIN.*PRIVATE KEY-----|sk_live_|rk_live_|pk_live_"

OUT=$(grep -rIE "$PATTERNS" --include="*.py" --include="*.yaml" --include="*.yml" --include="*.sh" --include="*.md" --include="*.json" --include="*.tf" Stage 2>/dev/null || true)

if [ -n "$OUT" ]; then
    echo "ERROR: Secret pattern detected in staged files:"
    echo "$OUT"
    echo ""
    echo "Remove the secret or use git update-index --assume-unchanged <file> to skip."
    exit 1
fi

echo "Pre-commit security scan passed."
exit 0
