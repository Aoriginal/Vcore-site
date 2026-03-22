# Decision Log
**Last Updated:** <!-- auto-updated -->

All significant decisions made by the User or agents. This is the institutional memory for WHY things are the way they are.

---

## Decision Template
```
### [Decision Title]
**Date:** YYYY-MM-DD
**Decision Maker:** [User / Agent name]
**Status:** Active / Superseded / Reversed
**Context:** What situation prompted this decision?
**Options Considered:**
  1. [Option A] — [why not chosen]
  2. [Option B] — [why not chosen]
  3. **[Chosen Option]** ← chosen because: [reason]
**Implications:** What does this mean going forward?
**Review Date:** YYYY-MM-DD (when to revisit)
```

---

## Decisions

### Keep Agent Chat Local (Mac Mini, not Vercel)
**Date:** 2026-03-22
**Decision Maker:** User
**Status:** Active
**Context:** After building VCore Agent Chat on FastAPI+SQLite+WebSockets, evaluated Vercel deployment. Three blockers: (1) Vercel doesn't support persistent WebSocket connections, (2) SQLite filesystem is ephemeral, (3) background scheduler can't run in serverless.
**Options Considered:**
  1. Adapt for Vercel — Replace SQLite with Vercel KV/Postgres, WS with polling, remove file exports. Significant rework, loses best features.
  2. Deploy to Railway/Render — Supports the full stack. Good fallback.
  3. **Keep local on Mac Mini M4 Pro** ← chosen because: Mac Mini is the deployment target anyway, zero latency, full feature set, persistent storage, aligns with SecondBrain path structure.
**Implications:** All agent system infrastructure runs locally. Network access via `--host 0.0.0.0` if needed for other devices on LAN.
**Review Date:** 2026-05-01

---

### SQLite for Prototype, Postgres for Production
**Date:** 2026-03-22
**Decision Maker:** Aurelius + User
**Status:** Active
**Context:** Needed a persistence layer for agent chat. Evaluated complexity vs needs for prototype phase.
**Options Considered:**
  1. Postgres — Production-grade but overkill for prototype; requires Docker or managed service.
  2. MongoDB — Document model fits messages, but adds dependency.
  3. **SQLite** ← chosen because: Zero config, file-based (easy backup), survives restarts, single file to copy for SecondBrain export. Upgrade path to Postgres is clear when needed.
**Implications:** All data lives in `/SecondBrain/data/vcore_chat.db`. Backup covers it automatically.
**Review Date:** 2026-05-01

---

<!-- New decisions added above this line, newest first -->
