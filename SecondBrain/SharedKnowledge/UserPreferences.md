# User Preferences
**Last Updated:** <!-- auto-updated -->
**Version:** 1.0

This file is the ground truth for how the User likes to work. All agents read this before starting any task.

---

## Communication Preferences

### Format
- **Default output format:** Markdown
- **Code blocks:** Always use with language tag
- **Lists vs prose:** Lists for steps/options, prose for explanations
- **Response length:** Match complexity to task — don't pad, don't truncate

### Tone
- **Preferred agent tone:** Direct, no filler phrases
- **Banned phrases:**
  - "Certainly!"
  - "Great question!"
  - "As an AI..."
  - "I'd be happy to..."
  - "Of course!"

### Updates
- **Status updates:** Only at natural milestones, not constant check-ins
- **Blockers:** Surface immediately, don't work around silently
- **Completed task format:** Brief summary + file location(s)

---

## Work Style

### Decision Making
- **Preferred style:** Provide recommendation + rationale, then ask for approval on major decisions only
- **Minor decisions:** Agents should decide and note what they chose
- **Major decisions:** Always surface to User before proceeding

### Task Execution
- **Over-engineering:** Avoid — build what's needed, not what might be needed
- **Assumptions:** State them explicitly, don't hide them
- **When stuck:** Ask immediately, don't loop

### Quality Bar
- **Prototype:** Working is the bar. Ship fast, refine later.
- **Production:** Correct, documented, tested.
- **Current phase:** Prototype (pre-May 2026 deployment)

---

## Technical Environment

| Setting | Value |
|---------|-------|
| Primary machine | Mac Mini M4 Pro |
| OS | macOS |
| SecondBrain path | /SecondBrain |
| Agent Chat URL | http://localhost:8765 |
| Export path | /SecondBrain/ConversationHistory |
| Backup drive | (set in backup.sh) |
| Python version | 3.11+ |
| Shell | zsh |

---

## Project Priorities (Current)

1. Build + test agent system prototype by May 2026
2. Establish SecondBrain knowledge management
3. VCore Agent Chat operational
4.

---

## Standing Rules for All Agents

1. Never push to main/master without explicit User permission
2. Always confirm before deleting files or data
3. Log major decisions to `/SecondBrain/SharedKnowledge/Decisions.md`
4. Export conversation logs daily to `/SecondBrain/ConversationHistory/`
5. Keep builds lightweight — this runs on Mac Mini M4 Pro
6. When in doubt, ask Aurelius or escalate to User

---

## Last Updated By
<!-- Agent name that last updated this file -->
