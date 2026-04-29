# rtc-reward-action

A reusable GitHub Action that **automatically awards RTC tokens** when a pull request is merged.

---

## Usage

### Step 1: Add to your repository

Create `.github/workflows/rtc-reward.yml`:

```yaml
name: RTC Reward on Merge

on:
  pull_request:
    types: [closed]

jobs:
  reward:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: Scottcjn/rtc-reward-action@v1
        with:
          node-url: https://50.28.86.131
          amount: 5
          admin-key: ${{ secrets.RTC_ADMIN_KEY }}
```

### Step 2: Add secrets

In your repo Settings → Secrets, add:
- `RTC_ADMIN_KEY` — Admin key for the payment wallet

### Step 3: Contributor wallet discovery

Contributors include their wallet in **one of two ways**:

**Option A — PR body** (e.g. `Wallet: my-wallet-name` or `RTC<hex>`)

**Option B — `.rtc-wallet` file** in their fork root:
```
echo "my-wallet-name" > .rtc-wallet
git add .rtc-wallet
git push origin my-branch
```

The action discovers the wallet in this order:
1. Look for `Wallet: <name>` in PR body
2. Look for `rtc<hex>` address in PR body
3. Fetch `.rtc-wallet` from the PR head branch

---

## Features

| Feature | Supported |
|---------|-----------|
| Configurable RTC amount | ✅ |
| Wallet from PR body | ✅ |
| Wallet from `.rtc-wallet` file | ✅ |
| Dry-run mode | ✅ |
| PR comment confirmation | ✅ |
| Idempotent (no double-pay) | ✅ |

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `node-url` | Yes | — | RustChain node URL |
| `amount` | No | `5` | RTC per merge |
| `wallet-from` | No | `founder_community` | Source wallet name |
| `admin-key` | Yes | — | Admin key for transfer |
| `dry-run` | No | `false` | Log-only mode |

---

## Example Workflows

### Basic
```yaml
- uses: Scottcjn/rtc-reward-action@v1
  with:
    node-url: https://50.28.86.131
    admin-key: ${{ secrets.RTC_ADMIN_KEY }}
```

### Tiered by repo size
```yaml
- uses: Scottcjn/rtc-reward-action@v1
  with:
    node-url: https://50.28.86.131
    amount: ${{ vars.RTC_AMOUNT_PER_MERGE }}
    admin-key: ${{ secrets.RTC_ADMIN_KEY }}
```

---

## Publishing to Marketplace

```bash
git tag v1.0.0
git push origin v1.0.0
# Then create a release on GitHub — marketplace listing auto-generated
```

---

## License

MIT — Elyan Labs / RustChain
