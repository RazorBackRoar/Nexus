#!/usr/bin/env python3
"""Automatic version increment script for Nexus
Updates version in README.md and setup.py automatically."""

import re
import subprocess
from pathlib import Path


def get_current_version():
    """Get current version from README.md."""
    readme = Path("README.md")
    if not readme.exists():
        raise FileNotFoundError("README.md not found")
    
    content = readme.read_text()
    match = re.search(r'\*\*Safari Bookmark & URL Manager\*\* - v([0-9.]+)', content)
    if not match:
        raise ValueError("Version not found in README.md")
    
    return match.group(1)


def increment_version(version):
    """Increment patch version with rollover logic.
    - x.y.z -> x.y.(z+1)
    - x.y.10 -> x.(y+1).0
    - x.10.0 -> (x+1).0.0
    """
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    
    patch += 1
    
    # Rollover logic
    if patch == 10:
        patch = 0
        minor += 1
    
    if minor == 10:
        minor = 0
        major += 1
    
    return f"{major}.{minor}.{patch}"


def update_readme(new_version):
    """Update version in README.md."""
    readme = Path("README.md")
    content = readme.read_text()
    content = re.sub(
        r'\*\*Safari Bookmark & URL Manager\*\* - v[0-9.]+',
        f'**Safari Bookmark & URL Manager** - v{new_version}',
        content
    )
    readme.write_text(content)


def update_setup_py(new_version):
    """Update version in setup.py."""
    setup_py = Path("setup.py")
    if not setup_py.exists():
        print("⚠️  setup.py not found, skipping")
        return
    
    content = setup_py.read_text()
    content = re.sub(
        r'version=["\']([^"\']+)["\']',
        f'version="{new_version}"',
        content
    )
    setup_py.write_text(content)


def git_commit_version_change(old_version, new_version):
    """Commit version changes to git."""
    try:
        subprocess.run(["git", "add", "README.md", "setup.py"], check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"v{new_version}: Version bump"],
            check=True,
            capture_output=True,
        )
        print(f"✅ Git commit created: v{old_version} -> v{new_version}")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git commit failed: {e}")


def main():
    """Main function to increment version."""
    try:
        old_version = get_current_version()
        new_version = increment_version(old_version)
        
        print(f"🔄 Incrementing version: v{old_version} -> v{new_version}")
        
        update_readme(new_version)
        update_setup_py(new_version)
        
        print(f'✅ Updated README.md: v{new_version}')
        print(f'✅ Updated setup.py: version="{new_version}"')
        
        # Auto-commit if git repo
        if Path(".git").exists():
            git_commit_version_change(old_version, new_version)
        
        return new_version
    
    except Exception as e:
        print(f"❌ Error incrementing version: {e}")
        return None


if __name__ == "__main__":
    main()
