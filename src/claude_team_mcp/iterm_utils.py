"""
iTerm2 Utilities for Claude Team MCP

Low-level primitives for iTerm2 terminal control, extracted and adapted
from the original primitives.py for use in the MCP server.
"""

from typing import Optional, Callable
from pathlib import Path


# =============================================================================
# Key Codes
# =============================================================================

# Key codes for iTerm2 async_send_text()
# IMPORTANT: Use \x0d (Ctrl+M/carriage return) for Enter, NOT \n
KEYS = {
    "enter": "\x0d",  # Carriage return - the actual Enter key
    "return": "\x0d",
    "newline": "\n",  # Line feed - creates newline in text, doesn't submit
    "escape": "\x1b",
    "tab": "\t",
    "backspace": "\x7f",
    "delete": "\x1b[3~",
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "home": "\x1b[H",
    "end": "\x1b[F",
    "ctrl-c": "\x03",  # Interrupt
    "ctrl-d": "\x04",  # EOF
    "ctrl-u": "\x15",  # Clear line
    "ctrl-l": "\x0c",  # Clear screen
    "ctrl-z": "\x1a",  # Suspend
}


# =============================================================================
# Terminal Control
# =============================================================================

async def send_text(session: "iterm2.Session", text: str) -> None:
    """
    Send raw text to an iTerm2 session.

    Note: This sends characters as-is. Use send_key() for special keys.
    """
    await session.async_send_text(text)


async def send_key(session: "iterm2.Session", key: str) -> None:
    """
    Send a special key to an iTerm2 session.

    Args:
        session: iTerm2 session object
        key: Key name (enter, escape, tab, backspace, up, down, left, right,
             ctrl-c, ctrl-u, ctrl-d, etc.)

    Raises:
        ValueError: If key name is not recognized
    """
    key_code = KEYS.get(key.lower())
    if key_code is None:
        raise ValueError(f"Unknown key: {key}. Available: {list(KEYS.keys())}")
    await session.async_send_text(key_code)


async def send_prompt(session: "iterm2.Session", text: str, submit: bool = True) -> None:
    """
    Send a prompt to an iTerm2 session, optionally submitting it.

    IMPORTANT: Uses \\x0d (Ctrl+M) for Enter, not \\n.
    iTerm2 interprets \\x0d as the actual Enter keypress.

    Args:
        session: iTerm2 session object
        text: The text to send
        submit: If True, press Enter after sending text
    """
    await session.async_send_text(text)
    if submit:
        await session.async_send_text(KEYS["enter"])


async def read_screen(session: "iterm2.Session") -> list[str]:
    """
    Read all lines from an iTerm2 session's screen.

    Args:
        session: iTerm2 session object

    Returns:
        List of strings, one per line
    """
    screen = await session.async_get_screen_contents()
    return [screen.line(i).string for i in range(screen.number_of_lines)]


async def read_screen_text(session: "iterm2.Session") -> str:
    """
    Read screen content as a single string.

    Args:
        session: iTerm2 session object

    Returns:
        Screen content as newline-separated string
    """
    lines = await read_screen(session)
    return "\n".join(lines)


# =============================================================================
# Window Management
# =============================================================================

async def create_window(connection: "iterm2.Connection") -> "iterm2.Window":
    """
    Create a new iTerm2 window.

    Args:
        connection: iTerm2 connection object

    Returns:
        New window object
    """
    import iterm2
    return await iterm2.Window.async_create(connection)


async def create_tab(window: "iterm2.Window") -> "iterm2.Tab":
    """
    Create a new tab in an existing window.

    Args:
        window: iTerm2 window object

    Returns:
        New tab object
    """
    return await window.async_create_tab()


async def split_pane(
    session: "iterm2.Session",
    vertical: bool = True,
    before: bool = False,
) -> "iterm2.Session":
    """
    Split an iTerm2 session into two panes.

    Args:
        session: The session to split
        vertical: If True, split vertically (side by side). If False, horizontal (stacked).
        before: If True, new pane appears before/above. If False, after/below.

    Returns:
        The new session created in the split pane.
    """
    return await session.async_split_pane(vertical=vertical, before=before)


# =============================================================================
# Claude Session Control
# =============================================================================

async def start_claude_in_session(
    session: "iterm2.Session",
    project_path: str,
    resume_session: Optional[str] = None,
    wait_seconds: float = 3.0,
) -> None:
    """
    Start Claude Code in an existing iTerm2 session.

    Changes to the project directory and launches Claude Code.

    Args:
        session: iTerm2 session to use
        project_path: Directory to run Claude in
        resume_session: Optional session ID to resume
        wait_seconds: Time to wait for Claude to initialize
    """
    import asyncio

    # Change to project directory
    await send_prompt(session, f"cd {project_path}")
    await asyncio.sleep(0.3)

    # Build and run claude command
    cmd = "claude"
    if resume_session:
        cmd += f" --resume {resume_session}"
    await send_prompt(session, cmd)

    # Wait for Claude to initialize
    await asyncio.sleep(wait_seconds)


async def find_claude_session(
    app: "iterm2.App",
    project_path: str,
    match_fn: Optional[Callable[[str], bool]] = None,
) -> Optional["iterm2.Session"]:
    """
    Find an iTerm2 session that appears to be running Claude Code.

    Searches all windows/tabs for sessions whose screen contains
    indicators of Claude Code (e.g., project path, "Opus", prompt char).

    Args:
        app: iTerm2 app object
        project_path: Expected project path
        match_fn: Optional custom matcher function(screen_text) -> bool

    Returns:
        iTerm2 session if found, None otherwise
    """
    # Default matcher looks for Claude indicators
    if match_fn is None:
        project_name = Path(project_path).name

        def match_fn(text: str) -> bool:
            return (
                project_name in text
                and ("Opus" in text or "Sonnet" in text or "Haiku" in text)
                and ">" in text
            )

    for window in app.terminal_windows:
        for tab in window.tabs:
            for session in tab.sessions:
                try:
                    text = await read_screen_text(session)
                    if match_fn(text):
                        return session
                except Exception:
                    continue

    return None
