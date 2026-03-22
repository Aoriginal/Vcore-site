# Component Library

Reusable code components maintained by Lamar. When Lamar completes a build with reusable parts, they get documented here so future builds can reference existing solutions.

## Catalogue

| Component | Language | Location | Description | Added |
|-----------|----------|----------|-------------|-------|
| FastAPI + SQLite starter | Python | Vcore2/agent-chat/ | Async FastAPI server with aiosqlite, WebSocket hub, REST API, static file serving | 2026-03-22 |
| WebSocket connection manager | Python | Vcore2/agent-chat/main.py:ConnectionManager | Manages multi-channel WS connections with broadcast + dead-connection cleanup | 2026-03-22 |
| Discord-style dark UI | HTML/CSS/JS | Vcore2/agent-chat/static/ | Full Discord-clone CSS theme + vanilla JS SPA with channel sidebar, messages, identity switcher | 2026-03-22 |
| Python agent API client | Python | Vcore2/agent-chat/agent_api.py | HTTP + WebSocket client for integrating Python agents with the chat platform | 2026-03-22 |
| Daily export scheduler | Python | Vcore2/agent-chat/export.py | Async midnight scheduler with JSON + Markdown export, summary generation | 2026-03-22 |

## How to Add a Component

1. Complete and test the build
2. Add entry to the table above
3. Add a section below with usage example
4. Reference in the relevant agent memory file

## Component Documentation

### FastAPI + SQLite Starter
```python
# Minimal pattern for new services
from fastapi import FastAPI
from contextlib import asynccontextmanager
import aiosqlite

@asynccontextmanager
async def lifespan(app):
    # init DB, start background tasks
    yield

app = FastAPI(lifespan=lifespan)
```
See `Vcore2/agent-chat/` for full implementation.

---

### WebSocket Connection Manager
```python
class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[tuple[WebSocket, str]]] = {}

    async def connect(self, ws, channel_id, agent_id): ...
    def disconnect(self, ws, channel_id): ...
    async def broadcast(self, channel_id, message): ...
```

---

*Maintained by Lamar. Update after every build.*
