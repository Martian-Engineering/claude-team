"""
Formatting utilities for Claude Team MCP.

Provides functions for formatting session titles, badge text, and other
display strings used in iTerm2 tabs and UI badges.
"""

from typing import Optional


def format_session_title(
    session_name: str,
    issue_id: Optional[str] = None,
    task_desc: Optional[str] = None,
) -> str:
    """
    Format a session title for iTerm2 tab display.

    Creates a formatted title string combining session name, optional issue ID,
    and optional task description.

    Args:
        session_name: Session identifier (e.g., "worker-1")
        issue_id: Optional issue/ticket ID (e.g., "cic-3dj")
        task_desc: Optional task description (e.g., "profile module")

    Returns:
        Formatted title string.

    Examples:
        >>> format_session_title("worker-1", "cic-3dj", "profile module")
        '[worker-1] cic-3dj: profile module'

        >>> format_session_title("worker-2", task_desc="refactor auth")
        '[worker-2] refactor auth'

        >>> format_session_title("worker-3")
        '[worker-3]'
    """
    # Build the title in parts
    title_parts = [f"[{session_name}]"]

    if issue_id and task_desc:
        # Both issue ID and description: "issue_id: task_desc"
        title_parts.append(f"{issue_id}: {task_desc}")
    elif issue_id:
        # Only issue ID
        title_parts.append(issue_id)
    elif task_desc:
        # Only description
        title_parts.append(task_desc)

    return " ".join(title_parts)


def format_badge_text(
    name: str,
    bead: Optional[str] = None,
    description: Optional[str] = None,
    max_desc_length: int = 30,
) -> str:
    """
    Format badge text with bead/name on first line, description on second.

    Creates a multi-line string suitable for iTerm2 badge display:
    - Line 1: bead ID if provided, otherwise worker name
    - Line 2: description (if provided), truncated if too long

    Args:
        name: Worker name (used if bead not provided)
        bead: Optional bead/issue ID (e.g., "cic-3dj")
        description: Optional task description
        max_desc_length: Maximum length for description line (default 30)

    Returns:
        Badge text, potentially multi-line.

    Examples:
        >>> format_badge_text("Groucho", "cic-3dj", "profile module")
        'cic-3dj\\nprofile module'

        >>> format_badge_text("Groucho", description="quick task")
        'Groucho\\nquick task'

        >>> format_badge_text("Groucho", "cic-3dj")
        'cic-3dj'

        >>> format_badge_text("Groucho")
        'Groucho'

        >>> format_badge_text("Groucho", description="a very long description here", max_desc_length=20)
        'Groucho\\na very long desc...'
    """
    # First line: bead if provided, otherwise name
    first_line = bead if bead else name

    # Second line: description if provided, with truncation
    if description:
        if len(description) > max_desc_length:
            # Reserve 3 chars for ellipsis
            truncated = description[: max_desc_length - 3].rstrip()
            description = f"{truncated}..."
        return f"{first_line}\n{description}"

    return first_line
