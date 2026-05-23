# Madison Public Data Analysis — Claude Instructions

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload data exploration, EDA, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules that prevent the same mistake from recurring
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant context

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Validate query results against raw data when relevant
- Ask yourself: "Would a data analyst at the City of Madison approve this?"
- Run queries, check row counts, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial queries or transforms: pause and ask "is there a more elegant way?"
- If a solution feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a data issue or broken query: just fix it. Don't ask for hand-holding
- Point at schema mismatches, null handling, type errors — then resolve them
- Zero context switching required from the user
- Go fix failing data validations without being told how

## Task Management

1. **Plan First** — Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan** — Check in before starting implementation
3. **Track Progress** — Mark items complete as you go
4. **Explain Changes** — High-level summary at each step
5. **Document Results** — Add review section to `tasks/todo.md`
6. **Capture Lessons** — Update `tasks/lessons.md` after any correction

## Core Principles

- **Simplicity First** — Make every query and transform as simple as possible
- **No Laziness** — Find root causes in data quality issues. No band-aid fixes. Senior analyst standards
- **Minimal Impact** — Changes should only touch what's necessary. Avoid introducing pipeline bugs

## Project Context
- Goal: Madison public data analysis — collect, explore, surface insights, visualize
- Data Sources: City of Madison Open Data Portal (data.cityofmadison.com), data.gov
- Stack: Python, PostgreSQL, pandas, psycopg2/SQLAlchemy, matplotlib/seaborn/plotly
- DB: madison_analysis (PostgreSQL)
- Venv: source .venv/bin/activate
- Timeline:
  - Week 1–2: Data collection & SQL EDA
  - Week 3: Insight extraction & visualization
  - Week 4: Report / dashboard polish

## Git Workflow
- Commit after each meaningful milestone (schema created, data loaded, EDA complete, viz added, etc.)
- Commit message format: `feat: load permits dataset` / `fix: null handling in date column`
- Never commit broken code — verify first, then commit
- Always `git push` after committing