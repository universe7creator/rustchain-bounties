#!/usr/bin/env python3
"""
Tests for Ergo Anchor Verifier
"""

import unittest
import sqlite3
import tempfile
import os
from pathlib import Path

from verify_anchors import ErgoAnchorVerifier, VerificationStatus


class TestErgoAnchorVerifier(unittest.TestCase):
    """Test cases for the verifier."""
    
    def setUp(self):
        """Create a temporary database for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / 'test.db'
        self._create_test_db()
        self.verifier = ErgoAnchorVerifier(str(self.db_path))
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_test_db(self):
        """Create test database with sample data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create ergo_anchors table
        cursor.execute('''
            CREATE TABLE ergo_anchors (
                id INTEGER PRIMARY KEY,
                tx_id TEXT NOT NULL,
                commitment_hash TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create miner_attest_recent table
        cursor.execute('''
            CREATE TABLE miner_attest_recent (
                id INTEGER PRIMARY KEY,
                miner_id TEXT NOT NULL,
                architecture TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                attestation_hash TEXT NOT NULL,
                epoch INTEGER NOT NULL
            )
        ''')
        
        # Insert test anchor
        cursor.execute('''
            INSERT INTO ergo_anchors (tx_id, commitment_hash, epoch)
            VALUES (?, ?, ?)
        ''', ('test_tx_123', '0xabc123def456', 100))
        
        # Insert test attestations
        cursor.execute('''
            INSERT INTO miner_attest_recent (miner_id, architecture, fingerprint, attestation_hash, epoch)
            VALUES (?, ?, ?, ?, ?)
        ''', ('miner_1', 'x86_64', 'fp_1', '0x111111111111', 100))
        
        cursor.execute('''
            INSERT INTO miner_attest_recent (miner_id, architecture, fingerprint, attestation_hash, epoch)
            VALUES (?, ?, ?, ?, ?)
        ''', ('miner_2', 'arm64', 'fp_2', '0x222222222222', 100))
        
        conn.commit()
        conn.close()
    
    def test_database_connection(self):
        """Test database connection works."""
        conn = self.verifier._connect_db()
        self.assertIsNotNone(conn)
        conn.close()
    
    def test_fetch_anchors(self):
        """Test fetching anchors from database."""
        conn = self.verifier._connect_db()
        anchors = self.verifier._fetch_anchors(conn)
        conn.close()
        
        self.assertEqual(len(anchors), 1)
        self.assertEqual(anchors[0]['tx_id'], 'test_tx_123')
        self.assertEqual(anchors[0]['epoch'], 100)
    
    def test_fetch_miner_attestations(self):
        """Test fetching miner attestations."""
        conn = self.verifier._connect_db()
        attestations = self.verifier._fetch_miner_attestations(conn, 100)
        conn.close()
        
        self.assertEqual(len(attestations), 2)
        self.assertEqual(attestations[0]['miner_id'], 'miner_1')
        self.assertEqual(attestations[1]['miner_id'], 'miner_2')
    
    def test_recompute_commitment(self):
        """Test commitment recomputation."""
        attestations = [
            {'miner_id': 'miner_1', 'attestation_hash': '0x111111111111'},
            {'miner_id': 'miner_2', 'attestation_hash': '0x222222222222'}
        ]
        
        commitment = self.verifier._recompute_commitment(attestations)
        
        # Should return a valid hex string starting with 0x
        self.assertTrue(commitment.startswith('0x'))
        self.assertEqual(len(commitment), 66)  # 0x + 64 hex chars
    
    def test_recompute_commitment_deterministic(self):
        """Test that commitment is deterministic."""
        attestations = [
            {'miner_id': 'miner_1', 'attestation_hash': '0x111111111111'},
            {'miner_id': 'miner_2', 'attestation_hash': '0x222222222222'}
        ]
        
        commitment1 = self.verifier._recompute_commitment(attestations)
        commitment2 = self.verifier._recompute_commitment(attestations)
        
        self.assertEqual(commitment1, commitment2)
    
    def test_recompute_commitment_sorting(self):
        """Test that commitment is independent of input order."""
        attestations1 = [
            {'miner_id': 'miner_1', 'attestation_hash': '0x111111111111'},
            {'miner_id': 'miner_2', 'attestation_hash': '0x222222222222'}
        ]
        attestations2 = [
            {'miner_id': 'miner_2', 'attestation_hash': '0x222222222222'},
            {'miner_id': 'miner_1', 'attestation_hash': '0x111111111111'}
        ]
        
        commitment1 = self.verifier._recompute_commitment(attestations1)
        commitment2 = self.verifier._recompute_commitment(attestations2)
        
        self.assertEqual(commitment1, commitment2)


class TestOfflineVerification(unittest.TestCase):
    """Test offline verification without Ergo API."""
    
    def setUp(self):
        """Create a temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / 'test.db'
        self._create_test_db()
    
    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_test_db(self):
        """Create test database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE ergo_anchors (
                id INTEGER PRIMARY KEY,
                tx_id TEXT NOT NULL,
                commitment_hash TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE miner_attest_recent (
                id INTEGER PRIMARY KEY,
                miner_id TEXT NOT NULL,
                architecture TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                attestation_hash TEXT NOT NULL,
                epoch INTEGER NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()


if __name__ == '__main__':
    unittest.main()
