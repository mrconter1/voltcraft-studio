#!/usr/bin/env python
"""Release script for Voltcraft Studio

Usage:
    python release.py <version>
    
Example:
    python release.py 1.3.0
    
This script will:
1. Update version.txt
2. Commit the change
3. Create a git tag
4. Push the commit and tag (which triggers the build process)
"""
import sys
import subprocess
from pathlib import Path


def validate_version(version: str) -> bool:
    """Validate version format (X.Y.Z)"""
    parts = version.split(".")
    if len(parts) != 3:
        return False
    try:
        for part in parts:
            int(part)
        return True
    except ValueError:
        return False


def run_command(cmd: list, description: str) -> bool:
    """Run a git command and handle errors"""
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ {description}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description}")
        print(f"  Error: {e.stderr}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python release.py <version>")
        print("Example: python release.py 1.3.0")
        sys.exit(1)
    
    version = sys.argv[1].lstrip("v")  # Remove 'v' prefix if present
    
    # Validate version format
    if not validate_version(version):
        print(f"❌ Invalid version format: {version}")
        print("   Expected format: X.Y.Z (e.g., 1.3.0)")
        sys.exit(1)
    
    print(f"\n📦 Releasing version {version}\n")
    
    # Update version.txt
    try:
        version_file = Path("version.txt")
        version_file.write_text(version + "\n")
        print(f"✓ Updated version.txt to {version}")
    except Exception as e:
        print(f"✗ Failed to write version.txt: {e}")
        sys.exit(1)
    
    # Git operations
    if not run_command(["git", "add", "version.txt"], "Staged version.txt"):
        sys.exit(1)
    
    if not run_command(
        ["git", "commit", "-m", f"Release version {version}"],
        "Committed version change"
    ):
        sys.exit(1)
    
    tag_name = f"v{version}"
    if not run_command(
        ["git", "tag", tag_name, "-a", "-m", f"Release {version}"],
        f"Created git tag {tag_name}"
    ):
        sys.exit(1)
    
    if not run_command(["git", "push", "origin", "main"], "Pushed commits"):
        sys.exit(1)
    
    if not run_command(
        ["git", "push", "origin", tag_name],
        f"Pushed tag {tag_name} (triggering build)"
    ):
        sys.exit(1)
    
    print(f"\n✅ Release {version} complete!")
    print(f"   Build process should be starting now...")


if __name__ == "__main__":
    main()
