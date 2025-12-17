"""
iTerm2 Profile Management for Claude Team MCP

Handles creation and customization of iTerm2 profiles for managed Claude sessions.
Includes automatic dark/light mode detection and consistent visual styling.

Profile Creation Strategy:
- Uses iTerm2's Dynamic Profiles feature for persistent profile creation
- Creates a JSON file in ~/Library/Application Support/iTerm2/DynamicProfiles/
- Falls back to session-level customizations if profile creation fails
"""

from typing import Optional
import json
import logging
import os
from pathlib import Path

from .subprocess_cache import cached_system_profiler

logger = logging.getLogger("claude-team-mcp.profile")


# =============================================================================
# Profile Cache
# =============================================================================

# Cache to track whether we've already ensured the profile exists this session.
# This avoids redundant filesystem checks on every spawn_team call.
_profile_ensured: bool = False
_profile_creation_failed: bool = False


# =============================================================================
# iTerm2 Advanced Settings
# =============================================================================

# Cache to track whether we've configured iTerm2 advanced settings this session.
_advanced_settings_configured: bool = False


def _configure_iterm2_advanced_settings() -> bool:
    """
    Configure iTerm2 advanced settings required for claude-team sessions.

    Sets app-level preferences that cannot be configured via Dynamic Profiles.
    Currently configures:
    - PreventEscapeSequenceFromClearingHistory: Set to NO to allow control
      sequences to clear scrollback without showing a warning dialog.

    This uses macOS `defaults` command since these are NSUserDefaults settings,
    not profile-level settings.

    Returns:
        True if settings were configured successfully, False otherwise
    """
    global _advanced_settings_configured

    if _advanced_settings_configured:
        return True

    try:
        import subprocess

        # Allow control sequences to clear scrollback history without warning.
        # This is an app-level advanced setting, not a profile setting.
        # Value: NO = allow clearing (don't show warning), YES = prevent clearing
        result = subprocess.run(
            [
                "defaults",
                "write",
                "com.googlecode.iterm2",
                "PreventEscapeSequenceFromClearingHistory",
                "-bool",
                "NO",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            logger.info(
                "Configured iTerm2 to allow control sequences to clear scrollback"
            )
            _advanced_settings_configured = True
            return True
        else:
            logger.warning(
                f"Failed to configure iTerm2 advanced settings: {result.stderr}"
            )
            return False

    except subprocess.TimeoutExpired:
        logger.warning("Timeout configuring iTerm2 advanced settings")
        return False
    except Exception as e:
        logger.warning(f"Error configuring iTerm2 advanced settings: {e}")
        return False


# =============================================================================
# Constants
# =============================================================================

# Profile identifier - used to find or create our managed profile
PROFILE_NAME = "claude-team"

# Font configuration - Source Code Pro preferred, Menlo as fallback
FONT_PRIMARY = "Source Code Pro"
FONT_FALLBACK = "Menlo"
FONT_SIZE = 12

# Tab title format template: [session-name] issue-id: description
TAB_TITLE_FORMAT = "[{session_name}] {issue_id}: {description}"

# iTerm2 Dynamic Profiles directory path
DYNAMIC_PROFILES_DIR = Path.home() / "Library/Application Support/iTerm2/DynamicProfiles"

# Our dynamic profile filename
DYNAMIC_PROFILE_FILENAME = "claude-team-profile.json"


# =============================================================================
# Color Schemes
# =============================================================================

# Pre-defined tab colors for visual distinction between sessions.
# Colors are tuples of (red, green, blue) in 0-255 range.
# These are chosen to be visually distinct and work well in both light/dark modes.
TAB_COLORS = [
    (66, 133, 244),   # Blue
    (52, 168, 83),    # Green
    (251, 188, 4),    # Yellow
    (234, 67, 53),    # Red
    (154, 160, 166),  # Gray
    (255, 112, 67),   # Orange
    (171, 71, 188),   # Purple
    (0, 172, 193),    # Cyan
]


# Light mode color scheme - optimized for readability
COLORS_LIGHT = {
    "foreground": (30, 30, 30),         # Near-black text
    "background": (255, 255, 255),       # White background
    "cursor": (0, 122, 255),             # Blue cursor
    "selection": (179, 215, 255),        # Light blue selection
    "bold": (0, 0, 0),                   # Black for bold text
    # ANSI colors (normal)
    "ansi_black": (0, 0, 0),
    "ansi_red": (194, 54, 33),
    "ansi_green": (37, 137, 58),
    "ansi_yellow": (173, 124, 36),
    "ansi_blue": (66, 133, 244),
    "ansi_magenta": (162, 73, 162),
    "ansi_cyan": (23, 162, 184),
    "ansi_white": (255, 255, 255),
}

# Dark mode color scheme - optimized for low-light environments
COLORS_DARK = {
    "foreground": (229, 229, 229),       # Light gray text
    "background": (30, 30, 30),          # Near-black background
    "cursor": (66, 133, 244),            # Blue cursor
    "selection": (62, 68, 81),           # Dark gray selection
    "bold": (255, 255, 255),             # White for bold text
    # ANSI colors (normal)
    "ansi_black": (0, 0, 0),
    "ansi_red": (255, 85, 85),
    "ansi_green": (80, 200, 120),
    "ansi_yellow": (255, 204, 0),
    "ansi_blue": (100, 149, 237),
    "ansi_magenta": (218, 112, 214),
    "ansi_cyan": (0, 206, 209),
    "ansi_white": (255, 255, 255),
}


# =============================================================================
# Screen Dimension Calculation
# =============================================================================


def calculate_screen_dimensions() -> tuple[int, int]:
    """
    Calculate terminal columns/rows to fill the screen.

    Uses system_profiler (with caching) to get screen resolution and calculates
    appropriate terminal dimensions based on Menlo 12pt font cell size.

    Returns:
        Tuple of (columns, rows) for a screen-filling terminal window
    """
    import re

    try:
        # Use cached system_profiler to avoid repeated slow calls
        stdout = cached_system_profiler("SPDisplaysDataType")
        if stdout is None:
            logger.warning("system_profiler failed, using default dimensions")
            return (200, 60)

        # Parse resolution from output like "Resolution: 3024 x 1964"
        match = re.search(r"Resolution: (\d+) x (\d+)", stdout)
        if not match:
            logger.warning("Could not parse screen resolution, using defaults")
            return (200, 60)

        screen_w, screen_h = int(match.group(1)), int(match.group(2))

        # Detect Retina display (2x scale factor)
        scale = 2 if "Retina" in stdout else 1
        logical_w = screen_w // scale
        logical_h = screen_h // scale

        # Subtract margins for window chrome:
        # - ~20px for window borders
        # - ~100px for menu bar + dock + title bar
        usable_w = logical_w - 20
        usable_h = logical_h - 100

        # Menlo 12pt cell size (approximately)
        cell_w, cell_h = 7.2, 14.0

        cols = int(usable_w / cell_w)
        rows = int(usable_h / cell_h)

        logger.debug(
            f"Screen {screen_w}x{screen_h} (scale {scale}) -> "
            f"terminal {cols}x{rows}"
        )
        return (cols, rows)

    except Exception as e:
        logger.warning(f"Failed to calculate screen dimensions: {e}")
        return (200, 60)


# =============================================================================
# Dynamic Profile Creation
# =============================================================================


def _rgb_to_iterm_color(rgb: tuple[int, int, int]) -> dict:
    """
    Convert an RGB tuple to iTerm2's dynamic profile color format.

    iTerm2 dynamic profiles expect colors as dictionaries with "Red", "Green",
    "Blue" keys and float values in 0.0-1.0 range.

    Args:
        rgb: Tuple of (red, green, blue) values in 0-255 range

    Returns:
        Dictionary with iTerm2 color format
    """
    return {
        "Red Component": rgb[0] / 255.0,
        "Green Component": rgb[1] / 255.0,
        "Blue Component": rgb[2] / 255.0,
    }


def _check_font_available(font_name: str) -> bool:
    """
    Check if a font is available on the system.

    Uses system_profiler (with caching) to check font availability.

    Args:
        font_name: Name of the font to check

    Returns:
        True if font is available, False otherwise
    """
    try:
        # Use cached system_profiler to avoid repeated slow calls
        stdout = cached_system_profiler("SPFontsDataType")
        if stdout is None:
            # If we can't check, assume font is not available
            return False
        return font_name in stdout
    except Exception:
        # If we can't check, assume font is not available
        return False


def _build_dynamic_profile_dict() -> dict:
    """
    Build the dynamic profile dictionary for iTerm2.

    Creates a profile configuration with:
    - Name: claude-team
    - Font: Source Code Pro 12pt (fallback to Menlo if unavailable)
    - Window style: Normal with calculated screen-filling dimensions
    - Dark mode colors (default)

    Returns:
        Dictionary suitable for writing to a dynamic profile JSON file
    """
    # Check which font to use
    font_name = FONT_PRIMARY
    if not _check_font_available(FONT_PRIMARY):
        logger.info(
            f"Font '{FONT_PRIMARY}' not available, using fallback '{FONT_FALLBACK}'"
        )
        font_name = FONT_FALLBACK

    # Use dark mode colors as default (most common for terminal use)
    colors = COLORS_DARK

    # Calculate screen-filling dimensions
    cols, rows = calculate_screen_dimensions()

    # Build the profile configuration.
    # iTerm2 dynamic profiles use specific key names - see:
    # https://iterm2.com/documentation-dynamic-profiles.html
    profile = {
        "Name": PROFILE_NAME,
        "Guid": f"{PROFILE_NAME}-guid",
        # Font: format is "FontName Size" for Normal Font
        "Normal Font": f"{font_name} {FONT_SIZE}",
        # Window style: 0 = Normal (avoids creating new macOS Space like Maximized does)
        # We use calculated Columns/Rows to fill the screen instead
        "Initial Window Type": 0,
        # Screen-filling dimensions calculated from display resolution
        "Columns": cols,
        "Rows": rows,
        # Tab color enabled
        "Use Tab Color": True,
        # Smart cursor color
        "Smart Cursor Color": True,
        # Terminal colors
        "Foreground Color": _rgb_to_iterm_color(colors["foreground"]),
        "Background Color": _rgb_to_iterm_color(colors["background"]),
        "Cursor Color": _rgb_to_iterm_color(colors["cursor"]),
        "Selection Color": _rgb_to_iterm_color(colors["selection"]),
        "Bold Color": _rgb_to_iterm_color(colors["bold"]),
        # ANSI colors
        "Ansi 0 Color": _rgb_to_iterm_color(colors["ansi_black"]),
        "Ansi 1 Color": _rgb_to_iterm_color(colors["ansi_red"]),
        "Ansi 2 Color": _rgb_to_iterm_color(colors["ansi_green"]),
        "Ansi 3 Color": _rgb_to_iterm_color(colors["ansi_yellow"]),
        "Ansi 4 Color": _rgb_to_iterm_color(colors["ansi_blue"]),
        "Ansi 5 Color": _rgb_to_iterm_color(colors["ansi_magenta"]),
        "Ansi 6 Color": _rgb_to_iterm_color(colors["ansi_cyan"]),
        "Ansi 7 Color": _rgb_to_iterm_color(colors["ansi_white"]),
        # Bright ANSI colors (same as normal for this profile)
        "Ansi 8 Color": _rgb_to_iterm_color(colors["ansi_black"]),
        "Ansi 9 Color": _rgb_to_iterm_color(colors["ansi_red"]),
        "Ansi 10 Color": _rgb_to_iterm_color(colors["ansi_green"]),
        "Ansi 11 Color": _rgb_to_iterm_color(colors["ansi_yellow"]),
        "Ansi 12 Color": _rgb_to_iterm_color(colors["ansi_blue"]),
        "Ansi 13 Color": _rgb_to_iterm_color(colors["ansi_magenta"]),
        "Ansi 14 Color": _rgb_to_iterm_color(colors["ansi_cyan"]),
        "Ansi 15 Color": _rgb_to_iterm_color(colors["ansi_white"]),
    }

    return profile


def _create_dynamic_profile_file() -> bool:
    """
    Create the dynamic profile JSON file for iTerm2.

    Creates the DynamicProfiles directory if needed and writes the profile JSON.
    iTerm2 automatically detects and loads profiles from this directory.

    Returns:
        True if profile was created successfully, False otherwise
    """
    global _profile_creation_failed

    try:
        # Ensure the DynamicProfiles directory exists
        DYNAMIC_PROFILES_DIR.mkdir(parents=True, exist_ok=True)

        profile_path = DYNAMIC_PROFILES_DIR / DYNAMIC_PROFILE_FILENAME

        # Build the profile
        profile = _build_dynamic_profile_dict()

        # Dynamic profiles file format: {"Profiles": [profile1, profile2, ...]}
        profile_data = {"Profiles": [profile]}

        # Write the profile file
        with open(profile_path, "w") as f:
            json.dump(profile_data, f, indent=2)

        logger.info(f"Created dynamic profile '{PROFILE_NAME}' at {profile_path}")
        return True

    except PermissionError as e:
        logger.warning(f"Permission denied creating dynamic profile: {e}")
        _profile_creation_failed = True
        return False
    except Exception as e:
        logger.warning(f"Failed to create dynamic profile: {e}")
        _profile_creation_failed = True
        return False


def _dynamic_profile_exists() -> bool:
    """
    Check if our dynamic profile file already exists.

    Returns:
        True if the profile file exists, False otherwise
    """
    profile_path = DYNAMIC_PROFILES_DIR / DYNAMIC_PROFILE_FILENAME
    return profile_path.exists()


async def profile_exists_in_iterm(connection: "iterm2.Connection") -> bool:
    """
    Check if the claude-team profile exists in iTerm2.

    Queries iTerm2's profile list via the Python API to check if our
    profile has been loaded (either from dynamic profiles or manually created).

    Args:
        connection: Active iTerm2 connection

    Returns:
        True if profile exists, False otherwise
    """
    try:
        import iterm2

        all_profiles = await iterm2.PartialProfile.async_query(connection)
        profile_names = [p.name for p in all_profiles if p.name]
        return PROFILE_NAME in profile_names
    except Exception as e:
        logger.warning(f"Could not query iTerm2 profiles: {e}")
        return False


async def ensure_profile_exists(connection: "iterm2.Connection") -> str:
    """
    Ensure the claude-team profile exists, creating it if necessary.

    This is the main entry point for profile auto-creation. It:
    1. Configures iTerm2 advanced settings (app-level preferences)
    2. Checks the cache to avoid redundant work
    3. Checks if profile already exists in iTerm2
    4. If not, creates a dynamic profile JSON file
    5. Falls back gracefully if creation fails

    The result is cached for the session lifetime to avoid repeated checks.

    Args:
        connection: Active iTerm2 connection

    Returns:
        The profile name to use (PROFILE_NAME if successful, None if failed
        and caller should use default profile with customizations)
    """
    global _profile_ensured, _profile_creation_failed

    # Configure iTerm2 advanced settings (app-level, not profile-level).
    # This is done before profile checks to ensure settings are always applied.
    _configure_iterm2_advanced_settings()

    # Fast path: already ensured this session
    if _profile_ensured:
        if _profile_creation_failed:
            return None  # Signal to use fallback
        return PROFILE_NAME

    # Check if profile already exists in iTerm2
    if await profile_exists_in_iterm(connection):
        logger.debug(f"Profile '{PROFILE_NAME}' already exists in iTerm2")
        _profile_ensured = True
        return PROFILE_NAME

    # Check if our dynamic profile file exists (might not be loaded yet)
    if _dynamic_profile_exists():
        logger.debug(
            f"Dynamic profile file exists but not loaded in iTerm2. "
            f"iTerm2 may need to reload profiles or restart."
        )
        _profile_ensured = True
        return PROFILE_NAME

    # Create the dynamic profile
    logger.info(f"Profile '{PROFILE_NAME}' not found, creating dynamic profile...")
    if _create_dynamic_profile_file():
        _profile_ensured = True
        # Note: iTerm2 should auto-detect the new profile, but it may take a moment.
        # For immediate use, the caller can fall back to session customizations.
        return PROFILE_NAME

    # Creation failed - fallback mode
    logger.warning(
        f"Could not create profile '{PROFILE_NAME}'. "
        f"Using default profile with customizations."
    )
    _profile_ensured = True
    _profile_creation_failed = True
    return None


def reset_profile_cache() -> None:
    """
    Reset the profile cache and advanced settings cache.

    Useful for testing or if the profile needs to be re-checked.
    """
    global _profile_ensured, _profile_creation_failed, _advanced_settings_configured
    _profile_ensured = False
    _profile_creation_failed = False
    _advanced_settings_configured = False


# =============================================================================
# Appearance Mode Detection
# =============================================================================


async def detect_appearance_mode(connection: "iterm2.Connection") -> str:
    """
    Detect the current macOS appearance mode (light or dark).

    Uses iTerm2's effective theme to determine the system appearance.
    Falls back to 'dark' if detection fails.

    Args:
        connection: Active iTerm2 connection

    Returns:
        'light' or 'dark' based on system appearance
    """
    try:
        import iterm2

        # Get the app object to query effective theme
        app = await iterm2.async_get_app(connection)

        # iTerm2's effective_theme returns a list of theme components
        # Common values include 'dark', 'light', 'automatic'
        theme = await app.async_get_variable("effectiveTheme")

        if theme and isinstance(theme, str):
            # effectiveTheme is a string like "dark" or "light"
            theme_lower = theme.lower()
            if "light" in theme_lower:
                return "light"
            elif "dark" in theme_lower:
                return "dark"

        # If theme is a list (some iTerm2 versions), check for dark indicators
        if theme and isinstance(theme, list):
            for component in theme:
                if isinstance(component, str) and "dark" in component.lower():
                    return "dark"
            return "light"

        logger.warning(f"Could not parse theme '{theme}', defaulting to dark")
        return "dark"

    except Exception as e:
        logger.warning(f"Failed to detect appearance mode: {e}, defaulting to dark")
        return "dark"


def get_colors_for_mode(mode: str) -> dict:
    """
    Get the color scheme dictionary for the specified appearance mode.

    Args:
        mode: Either 'light' or 'dark'

    Returns:
        Dictionary of color names to RGB tuples
    """
    if mode == "light":
        return COLORS_LIGHT.copy()
    return COLORS_DARK.copy()


# =============================================================================
# Tab Color Generation
# =============================================================================


def generate_tab_color(index: int) -> tuple[int, int, int]:
    """
    Generate a tab color for the given session index.

    Uses a predefined palette of visually distinct colors, cycling through
    them for sessions beyond the palette size.

    Args:
        index: Zero-based session index

    Returns:
        RGB tuple (0-255 for each component)
    """
    return TAB_COLORS[index % len(TAB_COLORS)]


async def generate_iterm_tab_color(index: int) -> "iterm2.Color":
    """
    Generate an iterm2.Color object for the given session index.

    Args:
        index: Zero-based session index

    Returns:
        iterm2.Color object suitable for tab coloring
    """
    import iterm2

    r, g, b = generate_tab_color(index)
    return iterm2.Color(r, g, b)


# =============================================================================
# Profile Management
# =============================================================================


async def get_or_create_profile(connection: "iterm2.Connection") -> str:
    """
    Get or create the claude-team iTerm2 profile.

    Checks if a profile named 'claude-team' exists. If not, creates it
    with sensible defaults including font configuration and color scheme
    based on the current system appearance mode.

    Args:
        connection: Active iTerm2 connection

    Returns:
        The profile name (PROFILE_NAME constant)

    Note:
        This function creates a partial profile. The caller should
        use create_session_customizations() to apply per-session
        customizations like tab color and title.
    """
    import iterm2

    # Get all existing profiles
    all_profiles = await iterm2.PartialProfile.async_query(connection)
    profile_names = [p.name for p in all_profiles if p.name]

    # Check if our profile already exists
    if PROFILE_NAME in profile_names:
        logger.debug(f"Profile '{PROFILE_NAME}' already exists")
        return PROFILE_NAME

    logger.info(f"Creating new profile '{PROFILE_NAME}'")

    # Find a suitable source profile (prefer Default, then first available)
    source_profile = None
    for profile in all_profiles:
        if profile.name == "Default":
            source_profile = profile
            break

    if not source_profile and all_profiles:
        source_profile = all_profiles[0]

    if not source_profile:
        raise RuntimeError("No profiles found to use as template")

    # Create our profile as a copy of the source
    # First get the full profile to access all properties
    full_source = await source_profile.async_get_full_profile()

    # Create a new profile with our name
    # iTerm2 doesn't have a direct "create profile" API, so we use
    # LocalWriteOnlyProfile to define settings and create a session with it

    # Detect appearance mode for initial colors
    mode = await detect_appearance_mode(connection)
    colors = get_colors_for_mode(mode)

    # Create the profile settings
    profile = iterm2.LocalWriteOnlyProfile()
    profile.set_name(PROFILE_NAME)

    # Font configuration - use async_set methods for font
    # Try Source Code Pro first, fall back to Menlo
    try:
        profile.set_normal_font(f"{FONT_PRIMARY} {FONT_SIZE}")
    except Exception:
        logger.warning(f"Font '{FONT_PRIMARY}' not available, using '{FONT_FALLBACK}'")
        profile.set_normal_font(f"{FONT_FALLBACK} {FONT_SIZE}")

    # Apply color scheme
    _apply_colors_to_profile(profile, colors)

    # Window settings - use tabs, not fullscreen
    profile.set_use_tab_color(True)
    profile.set_smart_cursor_color(True)

    # The profile will be created implicitly when a session uses it.
    # For now, we need to ensure it exists by using create_profile_with_api
    # or by having a session use it.

    # Note: iTerm2's Python API doesn't have a direct "create profile from scratch" method.
    # The profile will be created when first used. For persistence, users should
    # save the profile via iTerm2's UI or use the JSON profile import feature.

    logger.info(
        f"Profile '{PROFILE_NAME}' configured with {FONT_PRIMARY} {FONT_SIZE}pt, "
        f"{mode} mode colors"
    )

    return PROFILE_NAME


def _apply_colors_to_profile(
    profile: "iterm2.LocalWriteOnlyProfile",
    colors: dict,
) -> None:
    """
    Apply a color scheme to a profile.

    Helper function that sets all color-related profile properties
    from a color scheme dictionary.

    Args:
        profile: The profile to modify
        colors: Dictionary of color names to RGB tuples
    """
    import iterm2

    def rgb_to_color(rgb: tuple[int, int, int]) -> "iterm2.Color":
        return iterm2.Color(rgb[0], rgb[1], rgb[2])

    # Basic colors
    if "foreground" in colors:
        profile.set_foreground_color(rgb_to_color(colors["foreground"]))
    if "background" in colors:
        profile.set_background_color(rgb_to_color(colors["background"]))
    if "cursor" in colors:
        profile.set_cursor_color(rgb_to_color(colors["cursor"]))
    if "selection" in colors:
        profile.set_selection_color(rgb_to_color(colors["selection"]))
    if "bold" in colors:
        profile.set_bold_color(rgb_to_color(colors["bold"]))

    # ANSI colors
    ansi_color_setters = [
        ("ansi_black", profile.set_ansi_0_color),
        ("ansi_red", profile.set_ansi_1_color),
        ("ansi_green", profile.set_ansi_2_color),
        ("ansi_yellow", profile.set_ansi_3_color),
        ("ansi_blue", profile.set_ansi_4_color),
        ("ansi_magenta", profile.set_ansi_5_color),
        ("ansi_cyan", profile.set_ansi_6_color),
        ("ansi_white", profile.set_ansi_7_color),
    ]

    for color_name, setter in ansi_color_setters:
        if color_name in colors:
            setter(rgb_to_color(colors[color_name]))


# =============================================================================
# Session Customization
# =============================================================================


def format_tab_title(
    session_name: str,
    issue_id: Optional[str] = None,
    description: Optional[str] = None,
    max_description_length: int = 40,
) -> str:
    """
    Format a tab title according to the standard format.

    Format: [session-name] issue-id: description
    Example: [worker-1] cic-3dj: profile module

    Args:
        session_name: The session identifier (e.g., 'worker-1', 'quad_top_left')
        issue_id: Optional beads issue ID (e.g., 'cic-3dj')
        description: Optional short task description
        max_description_length: Maximum length for description before truncation

    Returns:
        Formatted tab title string
    """
    # Start with session name in brackets
    title = f"[{session_name}]"

    # Add issue ID if provided
    if issue_id:
        title += f" {issue_id}"

        # Add description if provided
        if description:
            # Truncate long descriptions
            if len(description) > max_description_length:
                description = description[:max_description_length - 3] + "..."
            title += f": {description}"
    elif description:
        # No issue ID but have description
        if len(description) > max_description_length:
            description = description[:max_description_length - 3] + "..."
        title += f" {description}"

    return title


async def create_session_customizations(
    connection: "iterm2.Connection",
    session_name: str,
    session_index: int = 0,
    issue_id: Optional[str] = None,
    task_description: Optional[str] = None,
) -> "iterm2.LocalWriteOnlyProfile":
    """
    Create a LocalWriteOnlyProfile with per-session customizations.

    This creates a profile customization object that can be applied to a
    session to set its tab color, title, and other visual properties.

    Args:
        connection: Active iTerm2 connection (used for appearance detection)
        session_name: The session identifier for the tab title
        session_index: Index for tab color generation (0-based)
        issue_id: Optional beads issue ID for the tab title
        task_description: Optional task description for the tab title

    Returns:
        LocalWriteOnlyProfile with customizations applied
    """
    import iterm2

    profile = iterm2.LocalWriteOnlyProfile()

    # Set tab title
    title = format_tab_title(session_name, issue_id, task_description)
    profile.set_name(title)

    # Set tab color
    tab_color = await generate_iterm_tab_color(session_index)
    profile.set_tab_color(tab_color)
    profile.set_use_tab_color(True)

    # Apply current appearance mode colors
    mode = await detect_appearance_mode(connection)
    colors = get_colors_for_mode(mode)
    _apply_colors_to_profile(profile, colors)

    logger.debug(f"Created session customizations for '{session_name}' with {mode} mode")

    return profile


async def apply_customizations_to_session(
    session: "iterm2.Session",
    customizations: "iterm2.LocalWriteOnlyProfile",
) -> None:
    """
    Apply a LocalWriteOnlyProfile's customizations to an existing session.

    Args:
        session: The iTerm2 session to customize
        customizations: The LocalWriteOnlyProfile with settings to apply
    """
    await session.async_set_profile_properties(customizations)
    logger.debug(f"Applied customizations to session {session.session_id}")


async def update_session_title(
    session: "iterm2.Session",
    session_name: str,
    issue_id: Optional[str] = None,
    task_description: Optional[str] = None,
) -> None:
    """
    Update just the tab title for an existing session.

    This is a lightweight alternative to create_session_customizations()
    when you only need to update the title (e.g., when a task changes).

    Args:
        session: The iTerm2 session to update
        session_name: The session identifier for the tab title
        issue_id: Optional beads issue ID for the tab title
        task_description: Optional task description for the tab title
    """
    import iterm2

    title = format_tab_title(session_name, issue_id, task_description)

    profile = iterm2.LocalWriteOnlyProfile()
    profile.set_name(title)

    await session.async_set_profile_properties(profile)
    logger.debug(f"Updated title for session {session.session_id} to '{title}'")
