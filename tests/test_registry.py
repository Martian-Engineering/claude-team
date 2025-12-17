"""Tests for the session registry module."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from claude_team_mcp.registry import (
    ManagedSession,
    SessionRegistry,
    SessionStatus,
)


class TestManagedSessionBlocker:
    """Tests for blocker methods on ManagedSession."""

    def _create_session(self, session_id: str = "test-session") -> ManagedSession:
        """Helper to create a test ManagedSession."""
        return ManagedSession(
            session_id=session_id,
            iterm_session=MagicMock(),
            project_path="/test/project",
        )

    def test_set_blocker_sets_reason(self):
        """set_blocker should set the blocker_reason field."""
        session = self._create_session()
        session.set_blocker("Missing API credentials")
        assert session.blocker_reason == "Missing API credentials"

    def test_set_blocker_sets_timestamp(self):
        """set_blocker should record when blocker was set."""
        session = self._create_session()
        before = datetime.now()
        session.set_blocker("Test blocker")
        after = datetime.now()

        assert session.blocker_at is not None
        assert before <= session.blocker_at <= after

    def test_set_blocker_updates_activity(self):
        """set_blocker should update last_activity."""
        session = self._create_session()
        original_activity = session.last_activity
        session.set_blocker("Blocker")
        assert session.last_activity >= original_activity

    def test_clear_blocker_clears_reason(self):
        """clear_blocker should clear the blocker_reason."""
        session = self._create_session()
        session.set_blocker("Some blocker")
        session.clear_blocker()
        assert session.blocker_reason is None

    def test_clear_blocker_clears_timestamp(self):
        """clear_blocker should clear blocker_at."""
        session = self._create_session()
        session.set_blocker("Some blocker")
        session.clear_blocker()
        assert session.blocker_at is None

    def test_clear_blocker_updates_activity(self):
        """clear_blocker should update last_activity."""
        session = self._create_session()
        session.set_blocker("Blocker")
        original_activity = session.last_activity
        session.clear_blocker()
        assert session.last_activity >= original_activity

    def test_is_blocked_returns_true_when_blocked(self):
        """is_blocked should return True when blocker is set."""
        session = self._create_session()
        session.set_blocker("I'm blocked!")
        assert session.is_blocked() is True

    def test_is_blocked_returns_false_when_not_blocked(self):
        """is_blocked should return False when no blocker."""
        session = self._create_session()
        assert session.is_blocked() is False

    def test_is_blocked_returns_false_after_clear(self):
        """is_blocked should return False after clearing blocker."""
        session = self._create_session()
        session.set_blocker("Blocked")
        session.clear_blocker()
        assert session.is_blocked() is False

    def test_can_set_new_blocker_after_clear(self):
        """Should be able to set a new blocker after clearing."""
        session = self._create_session()
        session.set_blocker("First blocker")
        session.clear_blocker()
        session.set_blocker("Second blocker")
        assert session.blocker_reason == "Second blocker"
        assert session.is_blocked() is True

    def test_to_dict_includes_blocker_info(self):
        """to_dict should include blocker information."""
        session = self._create_session()
        session.set_blocker("Waiting for approval")

        result = session.to_dict()
        assert result["is_blocked"] is True
        assert result["blocker_reason"] == "Waiting for approval"
        assert result["blocker_at"] is not None

    def test_to_dict_blocker_info_when_not_blocked(self):
        """to_dict should show not blocked when no blocker."""
        session = self._create_session()

        result = session.to_dict()
        assert result["is_blocked"] is False
        assert result["blocker_reason"] is None
        assert result["blocker_at"] is None


class TestSessionRegistryListBlocked:
    """Tests for list_blocked on SessionRegistry."""

    def test_list_blocked_returns_empty_when_none_blocked(self):
        """list_blocked should return empty list when no sessions blocked."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        registry.add(mock_iterm, "/path/a", name="Worker-A")
        registry.add(mock_iterm, "/path/b", name="Worker-B")

        blocked = registry.list_blocked()
        assert blocked == []

    def test_list_blocked_returns_blocked_sessions(self):
        """list_blocked should return sessions with blockers."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        session_a = registry.add(mock_iterm, "/path/a", name="Worker-A")
        session_b = registry.add(mock_iterm, "/path/b", name="Worker-B")
        session_c = registry.add(mock_iterm, "/path/c", name="Worker-C")

        session_a.set_blocker("Needs clarification")
        session_c.set_blocker("Missing dependency")

        blocked = registry.list_blocked()
        assert len(blocked) == 2
        assert session_a in blocked
        assert session_c in blocked
        assert session_b not in blocked

    def test_list_blocked_excludes_cleared_blockers(self):
        """list_blocked should not include sessions with cleared blockers."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        session = registry.add(mock_iterm, "/path/a", name="Worker")
        session.set_blocker("Blocked")
        session.clear_blocker()

        blocked = registry.list_blocked()
        assert len(blocked) == 0

    def test_list_blocked_returns_all_blocked(self):
        """list_blocked should return all blocked sessions."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        sessions = [
            registry.add(mock_iterm, f"/path/{i}", name=f"Worker-{i}")
            for i in range(5)
        ]

        # Block all sessions
        for i, session in enumerate(sessions):
            session.set_blocker(f"Blocker {i}")

        blocked = registry.list_blocked()
        assert len(blocked) == 5


class TestSessionRegistryBasics:
    """Basic tests for SessionRegistry functionality."""

    def test_add_creates_session(self):
        """add should create and return a ManagedSession."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        session = registry.add(mock_iterm, "/test/path", name="TestWorker")

        assert session is not None
        assert session.name == "TestWorker"
        assert session.project_path == "/test/path"

    def test_get_returns_session(self):
        """get should return session by ID."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        session = registry.add(mock_iterm, "/test/path")
        retrieved = registry.get(session.session_id)

        assert retrieved is session

    def test_get_returns_none_for_unknown(self):
        """get should return None for unknown session ID."""
        registry = SessionRegistry()
        assert registry.get("nonexistent") is None

    def test_count_returns_session_count(self):
        """count should return number of sessions."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        assert registry.count() == 0
        registry.add(mock_iterm, "/path/a")
        assert registry.count() == 1
        registry.add(mock_iterm, "/path/b")
        assert registry.count() == 2

    def test_list_all_returns_all_sessions(self):
        """list_all should return all registered sessions."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        session_a = registry.add(mock_iterm, "/path/a")
        session_b = registry.add(mock_iterm, "/path/b")

        all_sessions = registry.list_all()
        assert len(all_sessions) == 2
        assert session_a in all_sessions
        assert session_b in all_sessions

    def test_remove_removes_session(self):
        """remove should remove session from registry."""
        registry = SessionRegistry()
        mock_iterm = MagicMock()

        session = registry.add(mock_iterm, "/test/path")
        registry.remove(session.session_id)

        assert registry.get(session.session_id) is None
        assert registry.count() == 0
