"""Tests for formatting utilities."""

import pytest

from claude_team_mcp.formatting import format_session_title, format_badge_text


class TestFormatSessionTitle:
    """Tests for format_session_title function."""

    def test_full_title_with_all_parts(self):
        """Test with session name, issue ID, and task description."""
        result = format_session_title("worker-1", "cic-3dj", "profile module")
        assert result == "[worker-1] cic-3dj: profile module"

    def test_title_with_issue_id_only(self):
        """Test with session name and issue ID, no description."""
        result = format_session_title("worker-2", issue_id="cic-abc")
        assert result == "[worker-2] cic-abc"

    def test_title_with_task_desc_only(self):
        """Test with session name and description, no issue ID."""
        result = format_session_title("worker-3", task_desc="refactor auth")
        assert result == "[worker-3] refactor auth"

    def test_title_with_session_name_only(self):
        """Test with just session name."""
        result = format_session_title("worker-4")
        assert result == "[worker-4]"

    def test_title_with_none_values(self):
        """Test explicit None values."""
        result = format_session_title("worker-5", None, None)
        assert result == "[worker-5]"

    def test_title_with_empty_strings(self):
        """Empty strings should be treated like None."""
        # Empty issue_id with task_desc
        result = format_session_title("worker-6", "", "some task")
        assert result == "[worker-6] some task"


class TestFormatBadgeText:
    """Tests for format_badge_text function."""

    def test_badge_with_bead_and_description(self):
        """Test multi-line badge with bead and description."""
        result = format_badge_text("Groucho", "cic-3dj", "profile module")
        assert result == "cic-3dj\nprofile module"

    def test_badge_with_name_and_description(self):
        """Test multi-line badge with name and description (no bead)."""
        result = format_badge_text("Groucho", description="quick task")
        assert result == "Groucho\nquick task"

    def test_badge_with_bead_only(self):
        """Test single-line badge with just bead."""
        result = format_badge_text("Groucho", bead="cic-xyz")
        assert result == "cic-xyz"

    def test_badge_with_name_only(self):
        """Test single-line badge with just name."""
        result = format_badge_text("Groucho")
        assert result == "Groucho"

    def test_badge_bead_takes_precedence_over_name(self):
        """Test that bead is shown on first line when provided, not name."""
        result = format_badge_text("Groucho", bead="cic-abc")
        assert result == "cic-abc"
        assert "Groucho" not in result

    def test_badge_newline_separator(self):
        """Test that multi-line badge uses newline separator."""
        result = format_badge_text("Worker", bead="cic-123", description="task")
        assert "\n" in result
        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0] == "cic-123"
        assert lines[1] == "task"

    def test_badge_empty_bead_uses_name(self):
        """Test that empty string bead falls back to name."""
        result = format_badge_text("Groucho", bead="", description="task")
        assert result == "Groucho\ntask"

    def test_badge_none_bead_uses_name(self):
        """Test that None bead falls back to name."""
        result = format_badge_text("Groucho", bead=None, description="task")
        assert result == "Groucho\ntask"

    def test_badge_description_truncation(self):
        """Test that long descriptions are truncated with ellipsis."""
        long_desc = "implement user authentication system with OAuth"
        result = format_badge_text("Groucho", description=long_desc, max_desc_length=30)
        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[1].endswith("...")
        assert len(lines[1]) == 30

    def test_badge_description_exact_length(self):
        """Test description exactly at max length is not truncated."""
        desc = "a" * 30
        result = format_badge_text("Groucho", description=desc, max_desc_length=30)
        lines = result.split("\n")
        assert lines[1] == desc
        assert "..." not in lines[1]

    def test_badge_description_one_over(self):
        """Test description one char over max length is truncated."""
        desc = "a" * 31
        result = format_badge_text("Groucho", description=desc, max_desc_length=30)
        lines = result.split("\n")
        assert lines[1].endswith("...")
        assert len(lines[1]) == 30

    def test_badge_custom_max_desc_length(self):
        """Test custom max_desc_length parameter."""
        desc = "this is a moderately long description"
        result = format_badge_text("Groucho", description=desc, max_desc_length=20)
        lines = result.split("\n")
        assert len(lines[1]) == 20
        assert lines[1] == "this is a moderat..."

    def test_badge_default_max_desc_length(self):
        """Test default max_desc_length is 30."""
        desc = "a" * 35
        result = format_badge_text("Groucho", description=desc)
        lines = result.split("\n")
        assert len(lines[1]) == 30

    def test_badge_first_line_not_truncated(self):
        """Test that first line (bead/name) is never truncated."""
        long_bead = "cic-very-long-bead-identifier-here"
        result = format_badge_text("Groucho", bead=long_bead)
        assert result == long_bead
