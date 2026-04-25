"""
Trust Anchor Engine — External Verification Layer

Implements deterministic cycle sealing and GitHub-anchored external notarization.

Purpose:
- Generate tamper-evident cycle seals (SHA256 hashes of immutable inputs)
- Anchor seals externally via GitHub private repo to create independent verification layer
- Enable third-party auditors to verify cycles without trusting GridLedger database

Architecture:
1. cycle_seal: SHA256(cycle_data) — locally computed, stored in Cycle table
2. GitHub anchor: CSV log of (cycle_number, mill_id, seal, timestamp)
   - Commits pushed to private GitHub repo
   - Immutable record that survives database compromise
   - URL and commit hash become auditor-verifiable references

External parties can verify:
- Seal is real: check GitHub commit history
- Seal is deterministic: recompute from raw data
- Seal chain is intact: previous_seal references form chain of custody
"""

import subprocess
import csv
import os
from datetime import datetime, timezone
from typing import Optional
import logging
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


def anonymise_mill_id(mill_id: str) -> str:
    """
    Return SHA256 hex digest of mill_id for public anchoring.
    
    This allows us to anchor seals to a public GitHub repo without exposing
    actual mill identities. Operator can verify their mill's seals using:
    
        anonymised = anonymise_mill_id("MILL_NABIWI_001")
        # Then search for this hash in the public seal_log.csv
    
    Args:
        mill_id: Original mill identifier
    
    Returns:
        str: SHA256 hex (64 chars) of mill_id
    """
    return hashlib.sha256(mill_id.encode()).hexdigest()



class TrustAnchor:
    """
    GitHub-based external anchor for cycle seals.
    
    Maintains a CSV log that is version-controlled and committed to a private GitHub repo.
    Each row: cycle_number, mill_id, cycle_seal, timestamp
    
    Configuration:
    - SEAL_LOG_PATH: local file path to CSV log (default: ./cycle_seals.csv)
    - GITHUB_REPO_PATH: local clone path of private repo
    - GITHUB_AUTO_PUSH: whether to auto-push after each commit (boolean)
    """
    
    def __init__(self, repo_path: str = "./gridledger-cycle-seals", csv_file: str = "seal_log.csv"):
        """
        Initialize Trust Anchor with repo paths.
        
        Args:
            repo_path: Local path to cloned GitHub private repo
            csv_file: Filename for seal CSV log within repo
        """
        self.repo_path = Path(repo_path)
        self.csv_path = self.repo_path / csv_file
        self.csv_file = csv_file
        
        # Ensure repo directory exists
        if not self.repo_path.exists():
            logger.warning(f"Trust anchor repo not found at {repo_path}. Create repo and clone first.")
    
    def append_seal(self, cycle_number: int, mill_id: str, previous_seal: str, cycle_seal: str) -> bool:
        """
        Append cycle seal to CSV log and commit to GitHub (non-blocking).
        
        This is the main entry point for anchoring cycles externally.
        
        Args:
            cycle_number: Sequential cycle identifier
            mill_id: Mill identifier (will be anonymised in public log)
            previous_seal: Previous cycle's seal (for chain verification)
            cycle_seal: SHA256 hex digest from generate_cycle_seal()
        
        Returns:
            bool: True if successfully committed and pushed, False otherwise
        
        Side effects:
        - Appends row to seal_log.csv (using anonymised mill_id)
        - Creates git commit with message "Seal cycle {cycle_number}"
        - Pushes to origin/main
        
        CSV Format (with anonymisation):
            cycle_number, anonymised_mill_id, previous_seal, cycle_seal, timestamp
            1, a1b2c3d4..., "", 9eb1c516..., 2026-04-24T10:30:00Z
            2, a1b2c3d4..., 9eb1c516..., 568922ab..., 2026-04-24T14:15:00Z
        
        Auditor can verify seal chain using previous_seal without knowing mill identity.
        """
        try:
            # Validate repo exists
            if not self.repo_path.exists():
                logger.error(f"Repo not found at {self.repo_path}")
                return False
            
            # Validate it's a git repo
            git_dir = self.repo_path / ".git"
            if not git_dir.exists():
                logger.error(f"Not a git repository: {self.repo_path}")
                return False
            
            # Anonymise mill ID
            anonymised_mill_id = anonymise_mill_id(mill_id)
            
            # Timestamp in canonical UTC format
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            
            # Append to CSV
            file_exists = self.csv_path.exists()
            with open(self.csv_path, "a", newline="") as f:
                writer = csv.writer(f)
                if not file_exists:
                    # Write header row if new file
                    writer.writerow(["cycle_number", "mill_id_hash", "previous_seal", "cycle_seal", "timestamp"])
                writer.writerow([cycle_number, anonymised_mill_id, previous_seal, cycle_seal, timestamp])
            
            logger.info(f"Appended seal to {self.csv_path}: cycle={cycle_number}, mill_hash={anonymised_mill_id[:16]}...")
            
            # Git add CSV file
            try:
                subprocess.run(
                    ["git", "add", self.csv_file],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True,
                    timeout=10
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"git add failed: {e.stderr.decode()}")
                return False
            
            # Git commit
            commit_msg = f"Seal cycle {cycle_number}"
            try:
                result = subprocess.run(
                    ["git", "commit", "-m", commit_msg],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                commit_output = result.stdout.decode()
                logger.info(f"Git commit: {commit_output.strip()}")
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode()
                # "nothing to commit" is not an error - just means file didn't change
                if "nothing to commit" in stderr:
                    logger.debug(f"No changes to commit: {stderr.strip()}")
                    return True
                logger.error(f"git commit failed: {stderr}")
                return False
            
            # Git push
            try:
                result = subprocess.run(
                    ["git", "push", "-u", "origin", "main"],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                push_output = result.stdout.decode()
                logger.info(f"Git push: {push_output.strip()}")
                
                # Get commit hash for auditor reference
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(self.repo_path),
                    check=True,
                    capture_output=True,
                    timeout=10
                )
                commit_hash = hash_result.stdout.decode().strip()
                logger.info(f"Cycle seal anchored: commit={commit_hash}")
                
                return True
            except subprocess.CalledProcessError as e:
                stderr = e.stderr.decode()
                logger.error(f"git push failed: {stderr}")
                # Even if push fails, local commit succeeded - log warning
                return False
        
        except Exception as e:
            logger.error(f"Exception in append_seal: {e}", exc_info=True)
            return False
    
    def get_commit_hash(self) -> Optional[str]:
        """
        Get the current HEAD commit hash (for auditor reference).
        
        Returns:
            str: Commit hash (40-char hex), or None if failed
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.repo_path),
                check=True,
                capture_output=True,
                timeout=10
            )
            return result.stdout.decode().strip()
        except Exception as e:
            logger.error(f"Failed to get commit hash: {e}")
            return None
    
    def verify_seal_exists(self, cycle_number: int, mill_id: str, cycle_seal: str) -> bool:
        """
        Verify that a seal exists in the CSV log.
        
        This is for local verification only (doesn't check GitHub).
        For full auditor verification, check GitHub repo directly.
        
        Args:
            cycle_number: Cycle identifier
            mill_id: Mill identifier
            cycle_seal: Expected seal hash
        
        Returns:
            bool: True if seal is in local CSV
        """
        try:
            if not self.csv_path.exists():
                return False
            
            with open(self.csv_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if (row.get("cycle_number") == str(cycle_number) and
                        row.get("mill_id") == mill_id and
                        row.get("cycle_seal") == cycle_seal):
                        return True
            return False
        except Exception as e:
            logger.error(f"Failed to verify seal: {e}")
            return False


# Module-level convenience functions for integration

def anchor_seal(
    cycle_number: int,
    mill_id: str,
    previous_seal: str,
    cycle_seal: str,
    repo_path: str = "./gridledger-cycle-seals",
    csv_file: str = "seal_log.csv"
) -> bool:
    """
    Convenience function: append cycle seal to GitHub trust log.
    
    This should be called during cycle reconciliation (after generate_cycle_seal).
    Non-blocking: meant to be called from a background queue.
    
    Args:
        cycle_number: Sequential cycle identifier
        mill_id: Mill identifier
        previous_seal: Previous cycle's seal (for chain)
        cycle_seal: SHA256 seal from generate_cycle_seal()
        repo_path: Path to cloned GitHub repo
        csv_file: CSV filename within repo
    
    Returns:
        bool: True if successfully anchored, False otherwise
    """
    try:
        anchor = TrustAnchor(repo_path=repo_path, csv_file=csv_file)
        return anchor.append_seal(cycle_number, mill_id, previous_seal, cycle_seal)
    except Exception as e:
        logger.error(f"Failed to anchor seal: {e}", exc_info=True)
        return False


def setup_trust_anchor_repo(
    repo_path: str = "./gridledger-cycle-seals",
    github_url: str = None
) -> bool:
    """
    Initialize GitHub private repo for trust anchor (one-time setup).
    
    This should be run once to clone the private repo locally.
    
    Args:
        repo_path: Where to clone repo
        github_url: Full URL to private GitHub repo
                   e.g., https://github.com/gridledger/gridledger-cycle-seals.git
    
    Returns:
        bool: True if successfully cloned, False otherwise
    
    Prerequisites:
    - Create private repo on GitHub
    - Generate personal access token with repo access
    - Export as GITHUB_TOKEN environment variable or provide in URL
    - Protect main branch (no force-push)
    """
    if not github_url:
        logger.error("github_url required for setup_trust_anchor_repo")
        return False
    
    try:
        repo_path = Path(repo_path)
        
        # Clone repo if not exists
        if not repo_path.exists():
            logger.info(f"Cloning trust anchor repo to {repo_path}...")
            subprocess.run(
                ["git", "clone", github_url, str(repo_path)],
                check=True,
                capture_output=True,
                timeout=30
            )
            logger.info(f"Successfully cloned repo")
        
        # Verify it's a git repo
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            logger.error(f"Not a valid git repo: {repo_path}")
            return False
        
        logger.info(f"Trust anchor repo ready at {repo_path}")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone failed: {e.stderr.decode()}")
        return False
    except Exception as e:
        logger.error(f"Setup failed: {e}", exc_info=True)
        return False
