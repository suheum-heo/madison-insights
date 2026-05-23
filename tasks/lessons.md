# Lessons Learned

Patterns and corrections captured during development to prevent recurring mistakes.

---

<!-- Format:
## YYYY-MM-DD — Short title
**Mistake:** What went wrong
**Fix:** What the correct approach is
**Rule:** Generalized rule to apply going forward
-->

## 2026-05-23 — CLAUDE.md workflow not followed at session start

**Mistake:** Skipped plan mode, skipped tasks/todo.md plan + check-in, and made zero git commits throughout the entire session despite multiple meaningful milestones (schema, data load, EDA).

**Fix:** At the start of any non-trivial task — enter plan mode, write the plan to tasks/todo.md, get approval, then implement. Commit after each milestone (schema created, data loaded, EDA complete) and push immediately after.

**Rule:** Before writing a single line of code: (1) enter plan mode, (2) write plan to todo.md, (3) check in with user. After each milestone: git commit + git push.
