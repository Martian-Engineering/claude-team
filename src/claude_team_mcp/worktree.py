"""
Git worktree utilities for worker session isolation.

Provides functions to create, remove, and list git worktrees, enabling
each worker session to operate in its own isolated working directory
while sharing the same repository history.
"""

import subprocess
from pathlib import Path
from typing import Optional


class WorktreeError(Exception):
    """Raised when a git worktree operation fails."""

    pass


def create_worktree(
    repo_path: Path,
    worktree_name: str,
    branch: Optional[str] = None,
    base_dir: str = ".worktrees",
) -> Path:
    """
    Create a git worktree for a worker.

    Creates a new worktree in {repo_path}/{base_dir}/{worktree_name}.
    If a branch is specified and doesn't exist, it will be created from HEAD.
    If no branch is specified, creates a detached HEAD worktree.

    Args:
        repo_path: Path to the main repository
        worktree_name: Name for the worktree (used as directory name)
        branch: Branch to checkout (creates new branch from HEAD if doesn't exist)
        base_dir: Directory under repo_path where worktrees live

    Returns:
        Path to the created worktree

    Raises:
        WorktreeError: If the git worktree command fails

    Example:
        # Create a worktree for worker-1 on a new branch
        path = create_worktree(
            repo_path=Path("/path/to/repo"),
            worktree_name="worker-1",
            branch="worker-1-feature"
        )
        # Returns: Path("/path/to/repo/.worktrees/worker-1")
    """
    repo_path = Path(repo_path).resolve()
    worktree_path = repo_path / base_dir / worktree_name

    # Ensure base directory exists
    (repo_path / base_dir).mkdir(parents=True, exist_ok=True)

    # Check if worktree already exists
    if worktree_path.exists():
        raise WorktreeError(f"Worktree already exists at {worktree_path}")

    # Build the git worktree add command
    cmd = ["git", "-C", str(repo_path), "worktree", "add"]

    if branch:
        # Check if branch exists
        branch_check = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--verify", f"refs/heads/{branch}"],
            capture_output=True,
            text=True,
        )

        if branch_check.returncode == 0:
            # Branch exists, check it out
            cmd.extend([str(worktree_path), branch])
        else:
            # Branch doesn't exist, create it with -b
            cmd.extend(["-b", branch, str(worktree_path)])
    else:
        # No branch specified, create detached HEAD
        cmd.extend(["--detach", str(worktree_path)])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise WorktreeError(f"Failed to create worktree: {result.stderr.strip()}")

    return worktree_path


def remove_worktree(
    repo_path: Path,
    worktree_name: str,
    base_dir: str = ".worktrees",
    force: bool = True,
) -> bool:
    """
    Remove a worktree and clean up.

    Args:
        repo_path: Path to the main repository
        worktree_name: Name of the worktree to remove
        base_dir: Directory under repo_path where worktrees live
        force: If True, force removal even with uncommitted changes

    Returns:
        True if worktree was successfully removed

    Raises:
        WorktreeError: If the git worktree remove command fails

    Example:
        # Remove a worker's worktree
        success = remove_worktree(
            repo_path=Path("/path/to/repo"),
            worktree_name="worker-1"
        )
    """
    repo_path = Path(repo_path).resolve()
    worktree_path = repo_path / base_dir / worktree_name

    cmd = ["git", "-C", str(repo_path), "worktree", "remove"]

    if force:
        cmd.append("--force")

    cmd.append(str(worktree_path))

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Check if worktree doesn't exist (not an error)
        if "is not a working tree" in result.stderr or "No such file" in result.stderr:
            return True
        raise WorktreeError(f"Failed to remove worktree: {result.stderr.strip()}")

    # Also run prune to clean up stale worktree references
    subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "prune"],
        capture_output=True,
        text=True,
    )

    return True


def list_worktrees(repo_path: Path) -> list[dict]:
    """
    List all worktrees in a repository.

    Parses the porcelain output of git worktree list to provide
    structured information about each worktree.

    Args:
        repo_path: Path to the repository

    Returns:
        List of dicts, each containing:
            - path: Path to the worktree
            - branch: Branch name (or None if detached HEAD)
            - commit: Current HEAD commit hash
            - bare: True if this is the bare repository entry
            - detached: True if HEAD is detached

    Raises:
        WorktreeError: If the git worktree list command fails

    Example:
        worktrees = list_worktrees(Path("/path/to/repo"))
        for wt in worktrees:
            print(f"{wt['path']}: {wt['branch'] or 'detached'}")
    """
    repo_path = Path(repo_path).resolve()

    result = subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise WorktreeError(f"Failed to list worktrees: {result.stderr.strip()}")

    worktrees = []
    current_worktree: dict = {}

    for line in result.stdout.strip().split("\n"):
        if not line:
            # Empty line separates worktree entries
            if current_worktree:
                worktrees.append(current_worktree)
                current_worktree = {}
            continue

        if line.startswith("worktree "):
            current_worktree["path"] = Path(line[9:])
            current_worktree["branch"] = None
            current_worktree["commit"] = None
            current_worktree["bare"] = False
            current_worktree["detached"] = False
        elif line.startswith("HEAD "):
            current_worktree["commit"] = line[5:]
        elif line.startswith("branch "):
            # Branch is in format "refs/heads/branch-name"
            branch_ref = line[7:]
            if branch_ref.startswith("refs/heads/"):
                current_worktree["branch"] = branch_ref[11:]
            else:
                current_worktree["branch"] = branch_ref
        elif line == "bare":
            current_worktree["bare"] = True
        elif line == "detached":
            current_worktree["detached"] = True

    # Don't forget the last entry
    if current_worktree:
        worktrees.append(current_worktree)

    return worktrees


def get_worktree_path(
    repo_path: Path,
    worktree_name: str,
    base_dir: str = ".worktrees",
) -> Optional[Path]:
    """
    Get the path to a worktree if it exists.

    Convenience function to check if a worktree exists and get its path.

    Args:
        repo_path: Path to the main repository
        worktree_name: Name of the worktree
        base_dir: Directory under repo_path where worktrees live

    Returns:
        Path to the worktree if it exists, None otherwise
    """
    repo_path = Path(repo_path).resolve()
    worktree_path = repo_path / base_dir / worktree_name

    # Check if path exists and is in the worktree list
    worktrees = list_worktrees(repo_path)
    for wt in worktrees:
        if wt["path"] == worktree_path:
            return worktree_path

    return None
