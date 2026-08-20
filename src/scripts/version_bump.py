#!/usr/bin/env python3
"""Comprehensive version synchronization script for Nexus.

Updates version in README.md, setup.py, src/Main.py, and build.sh automatically.
"""

import os
import re
import subprocess
from pathlib import Path


def get_current_version():
    """Get current version from README.md."""
    readme = Path("README.md")
    if not readme.exists():
        raise FileNotFoundError("README.md not found")

    content = readme.read_text(encoding="utf-8")
    match = re.search(r"\*\*Safari Bookmark & URL Manager\*\* - v([0-9.]+)", content)
    if not match:
        raise ValueError("Version not found in README.md")

    return match.group(1)


def increment_version(version):
    """Increment minor version, keep patch at 0.

    - x.y.0 -> x.(y+1).0
    - x.9.0 -> (x+1).0.0.
    """
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    # Always increment minor, keep patch at 0
    minor += 1
    patch = 0

    # Rollover logic when minor hits 10
    if minor == 10:
        minor = 0
        major += 1

    return f"{major}.{minor}.{patch}"


def update_readme(new_version):
    """Update version in README.md."""
    readme = Path("README.md")
    if not readme.exists():
        print("⚠️  README.md not found, skipping")
        return

    content = readme.read_text(encoding="utf-8")
    content = re.sub(
        r"\*\*Safari Bookmark & URL Manager\*\* - v[0-9.]+",
        f"**Safari Bookmark & URL Manager** - v{new_version}",
        content,
    )
    readme.write_text(content, encoding="utf-8")
    print(f"✅ Updated README.md: v{new_version}")


def update_setup_py(new_version):
    """Update version in setup.py."""
    setup_py = Path("setup.py")
    if not setup_py.exists():
        print("⚠️  setup.py not found, skipping")
        return

    content = setup_py.read_text(encoding="utf-8")
    # Update APP_VERSION variable
    content = re.sub(
        r'APP_VERSION = "[0-9.]+"', f'APP_VERSION = "{new_version}"', content
    )
    setup_py.write_text(content, encoding="utf-8")
    print(f'✅ Updated setup.py: APP_VERSION="{new_version}"')


def update_main_py(new_version):
    """Update version in src/Main.py."""
    main_py = Path("src/main.py")
    if not main_py.exists():
        print("⚠️  src/main.py not found, skipping")
        return

    content = main_py.read_text(encoding="utf-8")
    content = re.sub(
        r'APP_VERSION = "[0-9.]+"', f'APP_VERSION = "{new_version}"', content
    )
    main_py.write_text(content, encoding="utf-8")
    print(f'✅ Updated src/main.py: APP_VERSION="{new_version}"')


def update_build_sh(new_version):
    """Update version in build.sh."""
    build_sh = Path("build.sh")
    if not build_sh.exists():
        print("⚠️  build.sh not found, skipping")
        return

    content = build_sh.read_text(encoding="utf-8")
    # Update header
    content = re.sub(r"Nexus v[0-9.]+", f"Nexus v{new_version}", content)
    # Update variable
    content = re.sub(r'APP_VERSION="[0-9.]+"', f'APP_VERSION="{new_version}"', content)
    build_sh.write_text(content, encoding="utf-8")
    print(f"✅ Updated build.sh: v{new_version}")


def git_commit_version_change(old_version, new_version):
    """Commit version changes to git."""
    try:
        subprocess.run(
            ["git", "add", "README.md", "setup.py", "src/main.py", "build.sh"],
            check=True,
            capture_output=True,
        )
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
        update_main_py(new_version)
        update_build_sh(new_version)

        if Path(".git").exists():
            if os.environ.get("RAZORCORE_ALLOW_GIT_MUTATION") == "1":
                git_commit_version_change(old_version, new_version)
            else:
                print(
                    "ℹ️  Skipping git commit. Set RAZORCORE_ALLOW_GIT_MUTATION=1 "
                    "only when a commit was explicitly requested."
                )

        return new_version

    except Exception as e:
        print(f"❌ Error incrementing version: {e}")
        return None


if __name__ == "__main__":
    main()
