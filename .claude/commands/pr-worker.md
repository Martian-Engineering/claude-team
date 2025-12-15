# PR Worker

Create a pull request from a worker's branch: $ARGUMENTS

## Process

1. Identify the worker session or branch from $ARGUMENTS
   - Can be session ID (e.g., "worker-1") or branch name (e.g., "cic-abc/feature")

2. If session ID provided:
   - Get session info via `get_session_status`
   - Find the worktree/branch from project path

3. Detect the parent branch (branch the worktree diverged from):
   ```bash
   git merge-base --fork-point main <branch> || \
   git merge-base --fork-point $(git branch --show-current) <branch>
   ```
   Or check git reflog for the branch point. If unclear, ask user.

4. Gather PR information:
   - Get commits on branch: `git log <parent>..<branch> --oneline`
   - Get changed files: `git diff <parent>..<branch> --stat`
   - Extract issue ID from branch name if present

5. Push branch if not already pushed:
   ```bash
   git push -u origin <branch>
   ```

6. Create PR using gh CLI (targeting parent branch):
   ```bash
   gh pr create --base <parent-branch> --title "<issue-id>: <summary>" --body "$(cat <<'EOF'
   ## Summary
   <bullet points from commits>

   ## Changes
   <list of changed files>

   ## Testing
   - [ ] Tests pass
   - [ ] Manual verification

   ---
   Related: <issue-id>
   EOF
   )"
   ```

7. Report the PR URL

## Output Format

```
## Pull Request Created

**Branch:** cic-abc/feature-name
**PR:** https://github.com/org/repo/pull/42
**Title:** cic-abc: Implement feature X

### Commits
- <sha> Add new endpoint
- <sha> Update tests

### Files Changed
- src/api/endpoint.py
- tests/test_endpoint.py

**Next steps:**
- Review PR at <url>
- After merge, run `/cleanup-worktrees` to remove worktree
```

## Notes

- Requires `gh` CLI to be authenticated
- Branch must have commits ahead of main
- Does not close the worker session (do that separately if desired)
