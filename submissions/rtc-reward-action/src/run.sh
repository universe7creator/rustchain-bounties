#!/usr/bin/env bash
# RTC Reward Action — run.sh v2
# Auto-awards RTC tokens when a PR is merged
# Usage: Called automatically by action.yml — no direct invocation needed
set -euo pipefail

GITHUB_OUTPUT="${GITHUB_OUTPUT:-${GITHUB_OUTPUT_PATH:-/dev/null}}"

# ── Env Validation ──────────────────────────────────────────────────────────
for var in RTC_NODE_URL RTC_ADMIN_KEY GITHUB_TOKEN PR_AUTHOR PR_NUMBER REPO; do
  if [[ -z "${!var}" ]]; then
    echo "::error::Missing required env var: $var"
    exit 1
  fi
done

# ── Idempotency: Skip if reward comment already posted ────────────────────────
echo "::group::Check idempotency"
EXISTING=$(gh api "repos/$REPO/pulls/$PR_NUMBER/comments" \
  --jq '.[] | select(.body | contains("rtc-reward-action") or contains("RTC Reward")) | .id' 2>/dev/null | head -1 || true)
if [[ -n "$EXISTING" ]]; then
  echo "::notice::Reward comment already exists (id=$EXISTING) — skipping"
  echo "wallet_found=true" >> "$GITHUB_OUTPUT"
  echo "wallet_name=already_paid" >> "$GITHUB_OUTPUT"
  echo "amount=0" >> "$GITHUB_OUTPUT"
  echo "already_paid=true" >> "$GITHUB_OUTPUT"
  echo "::endgroup::"
  exit 0
fi
echo "::debug::No prior reward comment — proceeding"
echo "::endgroup::"

# ── Wallet Discovery ─────────────────────────────────────────────────────────
echo "::group::Discover contributor wallet"

WALLET_NAME=""

# 1) Check PR body for RTC address or wallet name
PR_BODY=$(gh api "repos/$REPO/pulls/$PR_NUMBER" --jq '.body // ""')

# Match RTC hex address (RTC + 40 hex chars)
WALLET_NAME=$(echo "$PR_BODY" | grep -iEo 'rtc[a-z0-9]{40}' | head -1 || true)

if [[ -z "$WALLET_NAME" ]]; then
  # Match "Wallet: <name>" or "rtc-wallet: <name>" lines
  WALLET_NAME=$(echo "$PR_BODY" | grep -iEo '(wallet|rtc[-_]?wallet)[\s:]+[a-zA-Z0-9_-]{3,50}' \
    | grep -v 'rtc[a-z0-9]' \
    | head -1 \
    | sed -E 's/.*[\s:]+([a-zA-Z0-9_-]+)/\1/' || true)
fi

if [[ -z "$WALLET_NAME" ]]; then
  # 2) Fetch .rtc-wallet file from contributor's fork head branch
  echo "::debug::No wallet in PR body, checking contributor's .rtc-wallet file"
  HEAD_REF=$(gh api "repos/$REPO/pulls/$PR_NUMBER" --jq '.head.ref')
  HEAD_REPO=$(gh api "repos/$REPO/pulls/$PR_NUMBER" --jq '.head.repo.full_name')

  WALLET_FILE=$(gh api "$HEAD_REPO/contents/.rtc-wallet" \
    --jq '.content' 2>/dev/null | tr -d '\n ' || true)
  if [[ -n "$WALLET_FILE" ]]; then
    # Decode base64 and extract wallet
    DECODED=$(echo "$WALLET_FILE" | base64 -d 2>/dev/null || true)
    WALLET_NAME=$(echo "$DECODED" | grep -iEo 'rtc[a-z0-9]{40}' | head -1 || \
                  echo "$DECODED" | tr -d '\n ' | grep -iEo '[a-zA-Z0-9_-]{3,50}' | head -1 || true)
  fi
fi

if [[ -z "$WALLET_NAME" ]]; then
  echo "::warning::No wallet found for contributor '$PR_AUTHOR' — skipping reward"
  echo "wallet_found=false" >> "$GITHUB_OUTPUT"
  echo "wallet_name=" >> "$GITHUB_OUTPUT"
  echo "amount=0" >> "$GITHUB_OUTPUT"
  echo "already_paid=false" >> "$GITHUB_OUTPUT"
  echo "::endgroup::"
  exit 0
fi

echo "::notice::Discovered wallet: $WALLET_NAME"
echo "wallet_found=true" >> "$GITHUB_OUTPUT"
echo "wallet_name=$WALLET_NAME" >> "$GITHUB_OUTPUT"
echo "already_paid=false" >> "$GITHUB_OUTPUT"
echo "::endgroup::"

# ── Dry-Run Mode ──────────────────────────────────────────────────────────────
AMOUNT="${RTC_AMOUNT:-5}"
if [[ "${RTC_DRY_RUN:-false}" == "true" ]]; then
  echo "::notice::DRY-RUN: would transfer ${AMOUNT} RTC from ${RTC_WALLET_FROM:-founder_community} → $WALLET_NAME"
  echo "amount=0" >> "$GITHUB_OUTPUT"
  exit 0
fi

# ── Transfer via RustChain Node Wallet API ───────────────────────────────────
echo "::group::Transfer ${AMOUNT} RTC"

TX_HASH="pending"
ERROR_MSG="unknown"

TRANSFER_RESP=$(curl -s --max-time 30 -X POST "${RTC_NODE_URL}/wallet/transfer" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${RTC_ADMIN_KEY}" \
  -d "$(jq -n \
    --arg from "${RTC_WALLET_FROM:-founder_community}" \
    --arg to "$WALLET_NAME" \
    --argjson amount "$AMOUNT" \
    --arg memo "PR #$PR_NUMBER merged — rtc-reward-action v2" \
    '{from: $from, to: $to, amount: $amount, memo: $memo}')" 2>&1) || true

echo "::debug::Transfer response: $TRANSFER_RESP"

if echo "$TRANSFER_RESP" | grep -q '"ok":\s*true'; then
  TX_HASH=$(echo "$TRANSFER_RESP" | grep -oE '"tx_hash":"[^"]*"' | cut -d'"' -f4 || echo "pending")
  echo "::notice::✅ Transferred ${AMOUNT} RTC to $WALLET_NAME"
  echo "::notice::   tx_hash: $TX_HASH"
else
  ERROR_MSG=$(echo "$TRANSFER_RESP" | grep -oE '"error":"[^"]*"' | cut -d'"' -f4 || echo "$TRANSFER_RESP")
  echo "::error::Transfer failed: $ERROR_MSG"
  echo "amount=0" >> "$GITHUB_OUTPUT"
  echo "::endgroup::"
  exit 1
fi

echo "amount=${AMOUNT}" >> "$GITHUB_OUTPUT"
echo "tx_hash=$TX_HASH" >> "$GITHUB_OUTPUT"
echo "::endgroup::"

# ── Post PR Comment (idempotent) ────────────────────────────────────────────────
echo "::group::Post confirmation comment"

COMMENT_BODY="## 🎉 RTC Reward — PR #$PR_NUMBER Merged

| Field | Value |
|-------|-------|
| **Amount** | \`${AMOUNT} RTC\` |
| **Recipient** | \`$WALLET_NAME\` |
| **Tx Hash** | \`$TX_HASH\` |

> ⚡ This payment was automatically awarded by
> [rtc-reward-action](https://github.com/Scottcjn/rtc-reward-action)
> via the RustChain automated bounty system.

---
*Automated message — contact maintainers for payment issues.*"

gh pr comment "$PR_NUMBER" --repo "$REPO" --body "$COMMENT_BODY" 2>&1 || {
  echo "::warning::Failed to post PR comment (may already exist or no permissions)"
}

echo "::endgroup::"
echo "✅ RTC reward complete for $WALLET_NAME"
