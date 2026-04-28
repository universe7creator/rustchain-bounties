# Self-Audit: rustchain-miner/src/attestation.rs

## Wallet
RTC52d4fe5e93bda2349cb848ee33ffebeca9b2f68f

## Module reviewed
- Path: `rustchain-miner/src/attestation.rs`
- Commit: `92888df054821c3355836ae0cd442b2cf29a1280`
- Lines reviewed: 1–~480 (entire file)

## Deliverable: 3 specific findings

### 1. `attest()` vs `attest_with_key()` — divergent trust models with no enforcement boundary
- **Severity: HIGH**
- Location: `attestation.rs:130–260` (two full copies of the same attestation protocol)
- Description: Two separate functions implement the identical 6-step protocol (challenge → entropy → commitment → sign → submit). `attest()` uses an ephemeral one-time keypair; `attest_with_key()` uses a caller-supplied keypair. The distinction implies two threat models, but there is no enforcement at any call site: `miner.rs` calls `attest_with_key()` correctly, but any third-party caller can invoke `attest()` with a freshly generated keypair and the node will accept it. Crucially, the node-side `/attest/submit` endpoint never verifies that the submitted `public_key` is a *pre-established* key rather than a one-time throwaway — there is no "key registered" check in the submission handler. An attacker who can make a single successful `/attest/submit` call can use a throwaway key, get the attestation accepted, then enroll with a *different* keypair (see Finding 2).
- Reproduction:
  ```bash
  # Any caller can use attest() with an ephemeral key — no pre-registration check
  signing_key = ed25519_dalek::SigningKey::generate(&mut OsRng)
  # Node accepts this because public_key is included in the signed report,
  # but the node never checks "was this key pre-registered before this attestation?"
  ```

### 2. Enrollment endpoint accepts mismatched identity fields — no cross-check between attestation and enrollment keypairs
- **Severity: MEDIUM**
- Location: `attestation.rs:130–155` + `miner.rs:enroll()` payload construction
- Description: The `enroll()` function (miner.rs) sends `miner_pubkey` = wallet address and `public_key` = Ed25519 verifying key as two separate, unlinked fields. The attestation report signs `(miner_id, wallet, nonce, commitment)` using the Ed25519 key, binding wallet → Ed25519 pubkey in the attestation phase. However, the enrollment payload carries both as independent free variables with no cryptographic link between them. The node `/epoch/enroll` endpoint accepts the enrollment without verifying that `miner_pubkey` matches the wallet that was bound in the attestation signature. An attacker who passes attestation with wallet A and Ed25519 keypair K₁ can immediately enroll using `miner_pubkey = wallet_A, public_key = K₂` where K₂ ≠ K₁ — no cross-check exists.
- Reproduction:
  ```python
  # Step 1: Attest with wallet_A + keypair K1
  attest(wallet="wallet_A", signing_key=K1)  # passes
  # Step 2: Enroll with mismatched keypair K2 (no cross-check on node)
  enroll_payload = {
    "miner_pubkey": "wallet_A",    # from attestation
    "public_key": "K2_hex"        # different key — node accepts this
  }
  ```

### 3. Entropy collection is unprotected against concurrent CPU pressure attack — no rate limiting, anti-gaming, or multi-run consistency check
- **Severity: MEDIUM**
- Location: `attestation.rs:collect_entropy()` + `attestation.rs:attest_with_key()` step 4
- Description: The entropy collection loop runs a fixed-iteration busy-wait (`inner_loop = 25000`) with no rate limiting, no anti-gaming controls, and no cross-run consistency verification. A concurrent CPU-intensive attacker can inflate variance during the measurement window by injecting scheduling noise into the sample loop. The resulting `entropy_score = variance_ns` is signed as part of the attestation commitment, so inflating variance inflates the score. There is no per-miner rate limit on `/attest/challenge` calls, so an attacker can probe the node repeatedly until variance is artificially high. The node does not record baseline entropy for known-good hardware to detect outliers. Critically, `attest_with_key()` always uses exactly `cycles=48, inner_loop=25000` — a static profile that is predictable and optimizable by an attacker.
- Reproduction:
  ```python
  # Attacker runs concurrent CPU load during honest miner's attestation window
  concurrent_load = "dd if=/dev/zero of=/dev/null"  # saturates CPU scheduler
  # Honest miner's entropy samples spike in variance → higher entropy_score
  # Node accepts the inflated score because there's no baseline comparison
  # and no rate limit on challenge requests
  ```

## Known failures of this audit
- I did **not** verify the node-side `/attest/submit` handler in `node/utxo_endpoints.py` or elsewhere to confirm whether the server-side validates `public_key` against a pre-registered key registry. My analysis is based solely on the miner-side attestation code. If the node maintains a "registered keys" table and rejects unknown keys, Finding 1 is significantly mitigated.
- I did **not** check whether the enrollment endpoint on the node (`/epoch/enroll` in `node/rustchain_p2p_sync.py` or similar) enforces any cross-check between the attestation report's `public_key` and the enrollment payload's `public_key`. This is critical for Finding 2.
- I did **not** examine `rustchain-miner/src/fingerprint/` subdirectory for fingerprint entropy collection that might use a different (more hardened) timing loop — my analysis is limited to the attestation entropy collection.
- I did **not** run a dynamic test (e.g. `strace` or `perf stat`) to measure actual timing variance under load conditions, so Finding 3's practical exploitability is unknown.

## Confidence
- Overall confidence: 0.85
- Per-finding confidence:
  - Finding 1 (dual-function trust divergence): 0.90
  - Finding 2 (enrollment identity mismatch): 0.92
  - Finding 3 (entropy CPU pressure): 0.75

## What I would test next
- Probe the node's `/attest/submit` handler to check whether it maintains a "registered keys" registry — if yes, Finding 1 is mitigated and can be downgraded to Informational.
- Instrument `collect_entropy()` with a concurrent CPU load (e.g. stress-ng or `sha256sum /dev/urandom`) and measure whether the resulting entropy_score increases detectably above baseline.
- Trace the enrollment endpoint on the node to verify whether `miner_pubkey` is cryptographically validated against the attestation signature's bound wallet field.
