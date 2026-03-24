# Ergo Anchor Chain Proof Verifier

A standalone tool to verify RustChain miner attestation commitments anchored to the Ergo blockchain.

## Bounty

- **Issue:** #2278
- **Reward:** 100 RTC
- **Difficulty:** HARD
- **Repository:** Scottcjn/rustchain-bounties

## Features

- ✅ Reads local `ergo_anchors` table from `rustchain_v2.db`
- ✅ Fetches actual Ergo transactions from node API
- ✅ Extracts R4 register (Blake2b256 commitment hash)
- ✅ Recomputes commitment from `miner_attest_recent` data
- ✅ Compares: stored == on-chain == recomputed
- ✅ Reports discrepancies with specific details
- ✅ Works offline against DB dumps (for CI testing)
- ✅ Python 3.9+, no exotic dependencies

## Installation

```bash
# Clone the repository
git clone https://github.com/universe7creator/rustchain-bounties.git
cd rustchain-bounties

# No additional dependencies needed - uses only Python standard library
```

## Usage

### Basic Verification

```bash
python verify_anchors.py --db rustchain_v2.db
```

### With Custom Ergo Node

```bash
python verify_anchors.py --db rustchain_v2.db --ergo-api http://localhost:9053
```

### Export Results to JSON

```bash
python verify_anchors.py --db rustchain_v2.db --output results.json
```

### Offline Mode (Recompute Only)

```bash
python verify_anchors.py --db rustchain_v2.db --offline
```

## Output Format

```
Anchor #1: TX 731d5d87... | Commitment MATCH ✓ | 10 miners | Epoch 424
Anchor #2: TX a8f3c912... | Commitment MISMATCH ✗ | Expected: abc123... Got: def456...
...

============================================================
SUMMARY: 47/50 anchors verified successfully
  ✓ Matches: 47
  ✗ Mismatches: 3
  ? Missing TXs: 0
  ~ Unconfirmed: 0
  ! Errors: 0
============================================================
```

## Testing

```bash
python -m pytest test_verify_anchors.py -v
```

## Requirements

- Python 3.9+
- Access to RustChain SQLite database
- Access to Ergo node API (default: localhost:9053)

## Architecture

The verifier performs three-way validation:

1. **Stored Commitment**: From `ergo_anchors` table in SQLite
2. **On-Chain Commitment**: Extracted from R4 register of Ergo transaction
3. **Recomputed Commitment**: Calculated from `miner_attest_recent` data using Blake2b256

All three must match for verification to pass.

## License

MIT - Created for RustChain Bounty Program
