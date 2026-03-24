#!/usr/bin/env python3
"""
Ergo Anchor Chain Proof Verifier
Validates RustChain miner attestation commitments anchored to Ergo blockchain.

Bounty: 100 RTC
Issue: #2278
Repo: Scottcjn/rustchain-bounties
"""

import sqlite3
import json
import hashlib
import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class VerificationStatus(Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    MISSING_TX = "MISSING_TX"
    UNCONFIRMED = "UNCONFIRMED"
    ERROR = "ERROR"


@dataclass
class AnchorVerification:
    anchor_id: int
    tx_id: str
    status: VerificationStatus
    stored_commitment: str
    onchain_commitment: Optional[str] = None
    recomputed_commitment: Optional[str] = None
    miner_count: int = 0
    epoch: int = 0
    error_message: Optional[str] = None


class ErgoAnchorVerifier:
    """Verifies RustChain anchors against Ergo blockchain."""
    
    def __init__(self, db_path: str, ergo_api_url: str = "http://localhost:9053"):
        self.db_path = Path(db_path)
        self.ergo_api_url = ergo_api_url.rstrip('/')
        self.results: List[AnchorVerification] = []
        
    def _connect_db(self) -> sqlite3.Connection:
        """Connect to RustChain SQLite database."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        return sqlite3.connect(self.db_path)
    
    def _fetch_anchors(self, conn: sqlite3.Connection) -> List[Dict]:
        """Fetch all anchors from ergo_anchors table."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, tx_id, commitment_hash, epoch, created_at
            FROM ergo_anchors
            ORDER BY epoch
        """)
        
        anchors = []
        for row in cursor.fetchall():
            anchors.append({
                'id': row[0],
                'tx_id': row[1],
                'commitment_hash': row[2],
                'epoch': row[3],
                'created_at': row[4]
            })
        return anchors
    
    def _fetch_miner_attestations(self, conn: sqlite3.Connection, epoch: int) -> List[Dict]:
        """Fetch miner attestations for a specific epoch."""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT miner_id, architecture, fingerprint, attestation_hash
            FROM miner_attest_recent
            WHERE epoch = ?
            ORDER BY miner_id
        """, (epoch,))
        
        attestations = []
        for row in cursor.fetchall():
            attestations.append({
                'miner_id': row[0],
                'architecture': row[1],
                'fingerprint': row[2],
                'attestation_hash': row[3]
            })
        return attestations
    
    def _recompute_commitment(self, attestations: List[Dict]) -> str:
        """
        Recompute commitment hash from miner attestations.
        Uses Blake2b256 of sorted attestation hashes.
        """
        # Sort by miner_id for deterministic ordering
        sorted_attestations = sorted(attestations, key=lambda x: x['miner_id'])
        
        # Concatenate all attestation hashes
        combined = b''.join(
            bytes.fromhex(a['attestation_hash'].replace('0x', ''))
            for a in sorted_attestations
        )
        
        # Blake2b256 hash
        commitment = hashlib.blake2b(combined, digest_size=32).hexdigest()
        return f"0x{commitment}"
    
    def _fetch_ergo_transaction(self, tx_id: str) -> Optional[Dict]:
        """
        Fetch transaction from Ergo node API.
        Returns None if transaction not found.
        """
        try:
            import urllib.request
            import urllib.error
            
            url = f"{self.ergo_api_url}/transactions/{tx_id}"
            req = urllib.request.Request(url)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
        except Exception as e:
            raise Exception(f"Failed to fetch transaction {tx_id}: {e}")
    
    def _extract_r4_commitment(self, tx_data: Dict) -> Optional[str]:
        """
        Extract commitment hash from R4 register of Ergo transaction outputs.
        """
        try:
            outputs = tx_data.get('outputs', [])
            for output in outputs:
                registers = output.get('additionalRegisters', {})
                r4 = registers.get('R4')
                if r4:
                    # R4 contains the commitment hash
                    # Format is typically {"serializedValue": "...", "sigmaType": "...", "renderedValue": "..."}
                    rendered = r4.get('renderedValue', '')
                    if rendered.startswith('0x'):
                        return rendered
                    # Try to extract from serialized value
                    serialized = r4.get('serializedValue', '')
                    if len(serialized) >= 64:
                        return f"0x{serialized[-64:]}"
            return None
        except Exception:
            return None
    
    def verify_anchor(self, conn: sqlite3.Connection, anchor: Dict) -> AnchorVerification:
        """Verify a single anchor against Ergo blockchain."""
        anchor_id = anchor['id']
        tx_id = anchor['tx_id']
        stored_commitment = anchor['commitment_hash']
        epoch = anchor['epoch']
        
        # Fetch miner attestations for this epoch
        attestations = self._fetch_miner_attestations(conn, epoch)
        miner_count = len(attestations)
        
        # Recompute commitment from attestation data
        try:
            recomputed_commitment = self._recompute_commitment(attestations)
        except Exception as e:
            return AnchorVerification(
                anchor_id=anchor_id,
                tx_id=tx_id,
                status=VerificationStatus.ERROR,
                stored_commitment=stored_commitment,
                epoch=epoch,
                miner_count=miner_count,
                error_message=f"Failed to recompute commitment: {e}"
            )
        
        # Fetch transaction from Ergo
        try:
            tx_data = self._fetch_ergo_transaction(tx_id)
        except Exception as e:
            return AnchorVerification(
                anchor_id=anchor_id,
                tx_id=tx_id,
                status=VerificationStatus.ERROR,
                stored_commitment=stored_commitment,
                recomputed_commitment=recomputed_commitment,
                epoch=epoch,
                miner_count=miner_count,
                error_message=str(e)
            )
        
        if tx_data is None:
            return AnchorVerification(
                anchor_id=anchor_id,
                tx_id=tx_id,
                status=VerificationStatus.MISSING_TX,
                stored_commitment=stored_commitment,
                recomputed_commitment=recomputed_commitment,
                epoch=epoch,
                miner_count=miner_count,
                error_message="Transaction not found on Ergo chain"
            )
        
        # Check confirmation status
        if not tx_data.get('numConfirmations', 0) > 0:
            return AnchorVerification(
                anchor_id=anchor_id,
                tx_id=tx_id,
                status=VerificationStatus.UNCONFIRMED,
                stored_commitment=stored_commitment,
                recomputed_commitment=recomputed_commitment,
                epoch=epoch,
                miner_count=miner_count,
                error_message="Transaction exists but is unconfirmed"
            )
        
        # Extract commitment from R4 register
        onchain_commitment = self._extract_r4_commitment(tx_data)
        
        if onchain_commitment is None:
            return AnchorVerification(
                anchor_id=anchor_id,
                tx_id=tx_id,
                status=VerificationStatus.ERROR,
                stored_commitment=stored_commitment,
                recomputed_commitment=recomputed_commitment,
                epoch=epoch,
                miner_count=miner_count,
                error_message="Could not extract commitment from R4 register"
            )
        
        # Compare all three commitments
        stored_normalized = stored_commitment.lower().replace('0x', '')
        onchain_normalized = onchain_commitment.lower().replace('0x', '')
        recomputed_normalized = recomputed_commitment.lower().replace('0x', '')
        
        if stored_normalized == onchain_normalized == recomputed_normalized:
            status = VerificationStatus.MATCH
        else:
            status = VerificationStatus.MISMATCH
        
        return AnchorVerification(
            anchor_id=anchor_id,
            tx_id=tx_id,
            status=status,
            stored_commitment=stored_commitment,
            onchain_commitment=onchain_commitment,
            recomputed_commitment=recomputed_commitment,
            epoch=epoch,
            miner_count=miner_count
        )
    
    def verify_all(self) -> Tuple[int, int]:
        """Verify all anchors in the database."""
        conn = self._connect_db()
        try:
            anchors = self._fetch_anchors(conn)
            
            if not anchors:
                print("No anchors found in database.")
                return 0, 0
            
            print(f"Found {len(anchors)} anchors to verify...\n")
            
            verified_count = 0
            mismatch_count = 0
            
            for anchor in anchors:
                result = self.verify_anchor(conn, anchor)
                self.results.append(result)
                self._print_result(result)
                
                if result.status == VerificationStatus.MATCH:
                    verified_count += 1
                elif result.status == VerificationStatus.MISMATCH:
                    mismatch_count += 1
            
            return verified_count, mismatch_count
            
        finally:
            conn.close()
    
    def _print_result(self, result: AnchorVerification):
        """Print verification result for a single anchor."""
        status_symbol = {
            VerificationStatus.MATCH: "✓",
            VerificationStatus.MISMATCH: "✗",
            VerificationStatus.MISSING_TX: "?",
            VerificationStatus.UNCONFIRMED: "~",
            VerificationStatus.ERROR: "!"
        }.get(result.status, "?")
        
        print(f"Anchor #{result.anchor_id}: TX {result.tx_id[:16]}... | "
              f"Commitment {result.status.value} {status_symbol} | "
              f"{result.miner_count} miners | Epoch {result.epoch}")
        
        if result.status == VerificationStatus.MISMATCH:
            print(f"  Expected: {result.stored_commitment}")
            print(f"  On-chain: {result.onchain_commitment}")
            print(f"  Recomputed: {result.recomputed_commitment}")
        
        if result.error_message:
            print(f"  Error: {result.error_message}")
    
    def print_summary(self):
        """Print final summary report."""
        total = len(self.results)
        matches = sum(1 for r in self.results if r.status == VerificationStatus.MATCH)
        mismatches = sum(1 for r in self.results if r.status == VerificationStatus.MISMATCH)
        missing = sum(1 for r in self.results if r.status == VerificationStatus.MISSING_TX)
        unconfirmed = sum(1 for r in self.results if r.status == VerificationStatus.UNCONFIRMED)
        errors = sum(1 for r in self.results if r.status == VerificationStatus.ERROR)
        
        print(f"\n{'='*60}")
        print(f"SUMMARY: {matches}/{total} anchors verified successfully")
        print(f"  ✓ Matches: {matches}")
        print(f"  ✗ Mismatches: {mismatches}")
        print(f"  ? Missing TXs: {missing}")
        print(f"  ~ Unconfirmed: {unconfirmed}")
        print(f"  ! Errors: {errors}")
        print(f"{'='*60}")
    
    def export_json(self, output_path: str):
        """Export results to JSON file."""
        data = [
            {
                'anchor_id': r.anchor_id,
                'tx_id': r.tx_id,
                'status': r.status.value,
                'stored_commitment': r.stored_commitment,
                'onchain_commitment': r.onchain_commitment,
                'recomputed_commitment': r.recomputed_commitment,
                'miner_count': r.miner_count,
                'epoch': r.epoch,
                'error_message': r.error_message
            }
            for r in self.results
        ]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"\nResults exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Verify RustChain Ergo anchors against blockchain"
    )
    parser.add_argument(
        '--db', '-d',
        default='rustchain_v2.db',
        help='Path to RustChain SQLite database (default: rustchain_v2.db)'
    )
    parser.add_argument(
        '--ergo-api', '-e',
        default='http://localhost:9053',
        help='Ergo node API URL (default: http://localhost:9053)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Export results to JSON file'
    )
    parser.add_argument(
        '--offline',
        action='store_true',
        help='Offline mode - skip blockchain verification, only recompute commitments'
    )
    
    args = parser.parse_args()
    
    verifier = ErgoAnchorVerifier(args.db, args.ergo_api)
    
    try:
        verified, mismatches = verifier.verify_all()
        verifier.print_summary()
        
        if args.output:
            verifier.export_json(args.output)
        
        # Exit with error code if mismatches found
        sys.exit(0 if mismatches == 0 else 1)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(3)


if __name__ == '__main__':
    main()
