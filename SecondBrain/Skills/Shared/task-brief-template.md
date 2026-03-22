# Skill: Task Brief Template
**Used by:** Niklaus, User, any agent assigning work
**When to use:** Before handing off any task to another agent

---

## Template

```markdown
## Task Brief: [Task Name]

**Assigned to:** [Agent name]
**Assigned by:** [Your name]
**Date:** YYYY-MM-DD
**Due:** YYYY-MM-DD | [or: "ASAP" / "This session" / "No hard deadline"]
**Priority:** High / Medium / Low
**Channel to report back in:** #channel-name

### Objective
[One sentence: what does done look like? Be specific.]

### Context
[Why this matters. What happens if it's NOT done. Background the agent needs.]

### Scope
**In scope:**
- [Item 1]
- [Item 2]

**Out of scope:**
- [Item 1 — prevents scope creep]

### Deliverable
[Exactly what to produce: file, message, decision, etc. Where should it land?]

### Constraints
- [Technical constraints]
- [Time constraints]
- [Resource constraints]

### Definition of Done
- [ ] [Criterion 1]
- [ ] [Criterion 2]

### Questions / Clarifications Needed Before Starting
[Leave blank if none — agent should not start until these are answered]
```

---

## Example (Filled)

```markdown
## Task Brief: Write retention email sequence

**Assigned to:** Igris
**Assigned by:** Niklaus
**Date:** 2026-03-22
**Due:** 2026-03-23
**Priority:** Medium
**Channel to report back in:** #creative

### Objective
Three-email retention sequence for users who haven't logged in for 7 days.

### Context
Churn starts showing up at day 7 inactivity. We want to re-engage before
day 14. Current emails are too corporate — Maestro flagged them last week.

### Scope
In scope: Day 7, Day 10, Day 14 emails. Subject lines. Body copy.
Out of scope: Technical implementation, A/B testing setup, send schedule.

### Deliverable
Three email drafts as Markdown in #creative channel.

### Constraints
- Max 100 words per email
- Follow brand voice (see Maestro.md → Brand North Star)
- No discount offers — User decision 2026-03-15

### Definition of Done
- [ ] 3 email drafts posted in #creative
- [ ] Maestro has reviewed + approved
- [ ] User has signed off on Day 7 email (highest impact)
```
