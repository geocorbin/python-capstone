# Engineering Code Review Process — Northwind Analytics Inc.

## 1. Purpose
Code review exists to catch defects early, share knowledge across the team, and keep the
codebase maintainable. It is a collaborative process, not a gatekeeping exercise.

## 2. Workflow
1. Engineer opens a pull request (PR) against `main` with a clear description, linked ticket,
   and screenshots/logs for UI or behavior changes.
2. Automated checks run: unit tests, linting, type checking, and security scanning (SAST). A PR
   cannot be merged if any required check fails.
3. At least one approving review is required before merge; PRs touching authentication, billing,
   or data-migration code require two approvals, including one from a senior engineer.
4. Reviewers respond to new PRs within 1 business day. If a reviewer cannot review promptly, they
   should reassign or flag the delay in the team channel.
5. The PR author addresses feedback, re-requests review, and merges once approved and checks
   pass. Squash-merge is the default to keep history clean.

## 3. What Reviewers Look For
- Correctness: does the code do what the ticket describes, including edge cases?
- Tests: are new code paths covered by unit or integration tests?
- Readability: naming, structure, and comments that explain "why," not just "what."
- Security: input validation, avoidance of injection risks, proper handling of secrets.
- Scope: PRs should be reasonably small and focused; large PRs may be asked to split.

## 4. Handling Disagreements
If author and reviewer disagree after two rounds of comments, either party can loop in a third
engineer or the team lead for a tie-breaking opinion. Style preferences without a written
standard defer to the PR author unless they violate the team's lint configuration.

## 5. Emergency Hotfixes
Hotfixes for active incidents may be merged with a single reviewer's approval (even async, e.g.
a Slack thumbs-up) to restore service quickly, but must receive a full retroactive review within
24 hours and be linked to the incident ticket.

## 6. Post-Merge
Authors are responsible for monitoring their change after deploy (error rates, dashboards) for
at least 24 hours. If a regression is detected, the author owns reverting or hotfixing it.