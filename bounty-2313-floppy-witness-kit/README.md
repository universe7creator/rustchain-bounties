# RustChain Witness Kit

A compact epoch witness format for storing RustChain blockchain proofs on vintage media — 1.44MB floppies, ZIP disks, even cassette tapes.

> "It feels less like a backup and more like a portable relic of the chain."

## Features

- ✅ **Compact format**: <100KB per epoch witness
- ✅ **Vintage media support**: Floppy disks, ZIP disks, cassette tapes
- ✅ **QR code export**: For ultra-portable witnesses
- ✅ **Cryptographic verification**: SHA-256 hashes, Merkle proofs
- ✅ **ASCII art labels**: Beautiful disk labels for museum displays
- ✅ **1.44MB floppy capacity**: ~14,000 epoch witnesses per disk

## Installation

```bash
cargo build --release
```

The binary will be at `target/release/rustchain-witness`.

## Usage

### Write a Witness

```bash
# Write epoch 500 to a file
rustchain-witness write --epoch 500 --device ./witness_500.bin

# Write to an actual floppy device (Linux)
rustchain-witness write --epoch 500 --device /dev/fd0
```

### Read a Witness

```bash
# Read from file
rustchain-witness read --device ./witness_500.bin

# Read and save as JSON
rustchain-witness read --device ./witness_500.bin --output witness.json
```

### Verify a Witness

```bash
rustchain-witness verify ./witness_500.bin

# Verify against specific node
rustchain-witness verify ./witness_500.bin --node http://localhost:8545
```

### Generate QR Code

```bash
rustchain-witness qr ./witness_500.bin
```

### Create Floppy Disk Image

```bash
# Create image with multiple witnesses
rustchain-witness create-image --output witnesses.img witness_500.bin witness_501.bin witness_502.bin
```

### List Witnesses on Device

```bash
rustchain-witness list --device witnesses.img
```

## Witness Format

Each witness contains:

| Field | Description |
|-------|-------------|
| `epoch` | Epoch number |
| `timestamp` | UTC timestamp of epoch |
| `miners` | Array of miner IDs + architectures |
| `settlement_hash` | Block settlement hash |
| `ergo_anchor_tx` | Ergo blockchain anchor TX ID |
| `commitment_hash` | Epoch commitment hash |
| `merkle_proof` | Minimal Merkle inclusion proof |
| `disk_label` | ASCII art disk label |

## Example Output

```
📝 Creating epoch 500 witness...
✅ Witness written to: ./witness_500.bin
   Size: 847 bytes
   Hash: a3f5c8d2e1b4...
   Miners: 3
   💾 Fits on 1.44MB floppy: ~1700 witnesses
```

## Why This Matters

- **Air-gapped verification**: Verify chain state without network access
- **Museum exhibits**: Display real blockchain data on period-correct hardware
- **Disaster recovery**: Physical backups immune to digital attacks
- **It's beautiful**: Blockchain history on vintage media

## Architecture Support

The witness format supports all RustChain architectures:

- 68K (deepest layer)
- PowerPC G3/G4/G5
- SPARC
- MIPS
- POWER8
- Apple Silicon
- Modern x86_64

## License

MIT - See LICENSE file

## Bounty

This tool was created for RustChain Bounty #2313 (60 RTC).

Wallet for RTC payment: `9hGFnZ4yE2d3c4b5a6f7e8d9c0b1a2f3e4d5c6b7a8f9e0d1c2b3a4f5e6d7c8`
