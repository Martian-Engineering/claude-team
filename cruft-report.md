# Cruft & Disagreement Report

Generated: 2025-12-19

---

## Dead Code / Unused Functions

### 1. `iterm_utils.py:885-925` — `find_claude_session()`
Never called anywhere in codebase.

**Comment:**
Not sure what this would even do - we find claude sessions by tags now.

---

### 2. `iterm_utils.py:863-882` — `get_window_for_session()`
Never called anywhere in codebase.

**Comment:**
We're gonna want to do some stuff like this soon but let's rip it for now.

---

### 3. `iterm_utils.py:796-812` — `count_panes_in_window()`
Never called anywhere in codebase.

**Comment:**
We'll do this later too - rip for now.

---

### 4. `iterm_utils.py:256-266` — `create_tab()`
Never called anywhere in codebase.

**Comment:**
Rip for now.

---

### 5. `iterm_utils.py:780,815-860` — `find_available_window()`, `MAX_PANES_PER_TAB`
Imported in server.py but never used.

**Comment:**
Rip for now.

---

### 6. `session_state.py:614-639` — `watch_session()`
Generator function never called.

**Comment:**
No idea what this would do - rip it.

---

### 7. `names.py:250-257` — `get_random_set()`
Never called anywhere.

**Comment:**
rip it.

---

### 8. `profile.py:113` — `TAB_TITLE_FORMAT` constant
Defined but never used.

**Comment:**
Need you to tell me what this "should be doing" if that's clear at all.

---

### 9. `profile.py:129-138` — `TAB_COLORS` array
Vestigial, replaced by golden ratio system in colors.py.

**Comment:**
Golden Ratio system of colors? PSHEW blew my mind. Whatever ok sure. Rip the thing that isn't in use.

---

## Duplicate Implementations

### 10. Tab color generation
- `profile.py:594-607` — static 8-color palette
- `colors.py:23-69` — golden ratio distribution

Server imports from colors.py; profile.py version is dead.

**Comment:**
kill the profile version.

---

### 11. Title formatting
- `profile.py:776-816` — `format_tab_title()`
- `formatting.py:11-53` — `format_session_title()`

Server imports from formatting.py; profile.py version is dead.

**Comment:**
kill the profile version. Oh this harkons back to the formatting - i guess kill tab formatting - this is the same issue written differently.

---

### 12. Profile creation mechanisms
- `profile.py:446-508` — `ensure_profile_exists()` via JSON file
- `profile.py:631-720` — `get_or_create_profile()` via iTerm2 API

Two different mechanisms for same goal.

**Comment:**
I need some support understanding the differences here and which actually gets used where.

---

### 13. Completion detection
- `session_state.py:857-919` — `wait_for_response()` uses time-based idle detection
- `idle_detection.py:29-45` — `is_idle()` uses Stop hook detection

Both actively used. Time-based approach is vestigial alongside deterministic Stop hooks.

**Comment:**
Need to know if there's a special case where we use wait for response. Basically my prior is we should ALWAYS be using stop hook detection.

---

### 14. Session discovery
- `registry.py:118-133` — `discover_claude_session()` timestamp-based
- `registry.py:135-158` — `discover_claude_session_by_marker()` marker-based

Docstring says prefer marker-based, but timestamp-based still used as fallback.

**Comment:**
We shouldn't be discovering claudes by anything other than markers.

---

## Vestigial Parameters

### 15. `server.py:1625-1626` — `project_path` on `import_session`
Documented as "Ignored (recovered from marker). Kept for API compatibility."

**Comment:**
Kill it - api compatibility lol.

---

### 16. `iterm_utils.py:272` — `before` on `split_pane`
Never passed with non-default value.

**Comment:**
No idea what this would do - not enough detail

---

### 17. `iterm_utils.py:485` — `resume_session` on `start_claude_in_session`
Never passed non-None.

**Comment:**
Don't know what this is either - confused.

---

### 18. `session_state.py:862` — `baseline_message_uuid` on `wait_for_response`
Old approach for detecting new messages; Stop hooks make this unnecessary.

**Comment:**
Yes - rip to my stop hook detection.

---

### 19. `session_state.py:861` — `idle_threshold` on `wait_for_response`
Time-based heuristic alongside deterministic Stop hooks.

**Comment:**


---

## Documentation Disagreements

### 20. `CLAUDE.md:15` — Lists `task_completion.py`
File doesn't exist. Functionality split between `idle_detection.py` and `session_state.py`.

**Comment:**


---

### 21. `CLAUDE.md:9` — "13 MCP tools"
Actually 15 tools.

**Comment:**


---

### 22. `CLAUDE.md:38` — Tool named `spawn_session`
Actual tool is `spawn_team`.

**Comment:**


---

### 23. `CLAUDE.md:69-71` — Layout names
Doc says: `new_window`, `split_vertical`, `split_horizontal`, `quad`, `auto_layout`
Code uses: `single`, `vertical`, `horizontal`, `quad`, `triple_vertical`

**Comment:**


---

### 24. `server.py:105-109` — HINTS mentions `split_from_session`
No such parameter exists on any current tool.

**Comment:**


---

## Inconsistencies

### 25. Naming: controller vs coordinator
- `registry.py:81` uses `controller_annotation`
- Everywhere else uses "coordinator" terminology

**Comment:**


---

### 26. Naming: customizations parameter
- `create_window()` uses `profile_customizations`
- `create_multi_pane_layout()` uses `pane_customizations`

Same concept, different names.

**Comment:**


---

### 27. Default timeouts vary
- `send_message`: 120s
- `get_response`: 60s
- `wait_for_idle`: 600s

Conceptually similar "wait for Claude" operations.

**Comment:**


---

### 28. Test import path inconsistency
- `test_colors.py` uses `src.claude_team_mcp.colors`
- All other tests use `claude_team_mcp.*`

**Comment:**


---

## Anti-Patterns / Structural Issues

### 29. `session_state.py:87-92` — `is_processing` checks `tool_uses`
Can disagree with Stop hook state: if Claude's last message had tool_use that completed, `is_processing` is True even after Stop hook fires.

**Comment:**


---

### 30. `session_state.py:797-854` — `is_session_stopped()` parses file twice
Calls `get_last_stop_hook_for_session()` (parses file), then opens and parses same file again.

**Comment:**


---

### 31. `session_state.py:402-405` — Naive fallback in `find_jsonl_by_iterm_id`
When `unslugify_path()` returns None, falls back to naive `replace('-', '/')` which contradicts the sophisticated greedy algorithm.

**Comment:**


---

### 32. `session_state.py:295` — `time` imported twice
Imported at top of file and again inside `find_jsonl_by_marker()`.

**Comment:**


---

### 33. `session_state.py:642-644` — Empty section header
"Response Waiting" header with nothing under it; actual function is 200 lines later.

**Comment:**


---

### 34. `registry.py:90-95` — Uses `object.__setattr__` unnecessarily
Comment says "since we're in `__post_init__`" but dataclass isn't frozen; this workaround is only needed for frozen dataclasses.

**Comment:**


---

### 35. `registry.py:59` + `server.py:1789` — `SessionStatus.CLOSED` unobservable
Status is set to CLOSED then `remove()` called immediately. `list_by_status(CLOSED)` always returns empty.

**Comment:**


---

### 36. `server.py:1776-1779` — Worktree cleanup uses wrong path
`close_session` uses `session.project_path` for `remove_worktree()` but when worktrees are enabled, `project_path` is the worktree path, not the main repo.

**Comment:**


---

### 37. `profile.py:318` — Dynamic profile ignores appearance mode
Always uses dark colors despite `get_colors_for_mode()` existing.

**Comment:**


---

### 38. `server.py:26-37` — Multiple unused imports from iterm_utils
`MAX_PANES_PER_TAB`, `count_panes_in_tab`, `create_window`, `find_available_window`, `split_pane`, `start_claude_in_session` — imported but not used directly.

**Comment:**


---

## Summary

**Highest-impact clusters:**

1. **profile.py** — Lots of vestigial code (colors, formatting, profile creation) replaced by other modules

2. **Two completion detection mechanisms** — Time-based (`wait_for_response`) vs Stop hook (`is_idle`)

3. **iterm_utils.py** — ~5 unused functions

4. **CLAUDE.md** — Stale in several places

**Comment:**
