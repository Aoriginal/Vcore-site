# Skill: Status Report Template
**Used by:** All agents
**When to use:** Daily standup, task completion report, or when asked for an update

---

## Quick Update (< 5 things happening)

```
**[Agent Name] — [Date] Status**

✅ Done: [What completed since last update]
🔵 Active: [What's in progress right now]
⚠️ Blocked: [What's stuck and why]
🕐 Next: [What starts after current task]
```

---

## Full Status Report (multi-task / multi-day)

```markdown
# Status Report: [Agent Name]
**Date:** YYYY-MM-DD | **Period:** [e.g., "Week of March 22"]

## Completed This Period
| Task | Outcome | Notes |
|------|---------|-------|
| | | |

## In Progress
| Task | % Done | ETA | Blocker |
|------|--------|-----|---------|
| | | | |

## Blocked
| Task | Blocked By | Who Needs to Act | Since |
|------|-----------|-----------------|-------|
| | | | |

## Coming Up
| Task | Start | Dependencies |
|------|-------|-------------|
| | | |

## Decisions Needed from User/Niklaus
| Decision | Context | Options | Recommendation |
|----------|---------|---------|----------------|
| | | | |

## Metrics (if applicable)
| Metric | Target | Actual | Trend |
|--------|--------|--------|-------|
| | | | |
```

---

## Example Quick Update

```
**Lamar — 2026-03-22 Status**

✅ Done: VCore Agent Chat platform — all features complete, pushed to branch
🔵 Active: Nothing — awaiting next build request
⚠️ Blocked: None
🕐 Next: Pattern extractor + message humanizer builds (queued)
```
