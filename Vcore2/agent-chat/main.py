"""
VCore Agent Chat Platform - FastAPI Backend
WebSocket-based real-time messaging with SQLite persistence.

Run: uvicorn main:app --host 0.0.0.0 --port 8765 --reload
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    AGENTS, CHANNELS, agent_can_read, agent_can_post, get_visible_channels
)
from database import (
    init_db, save_message, get_messages,
    get_or_create_dm, get_dm_channels_for_agent, get_channel_list
)
from export import export_day, run_scheduler


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Post system boot message
    await save_message("general", "system", "SYSTEM", "🟢 VCore Chat Platform online.", "system")
    # Start daily export scheduler in background
    asyncio.create_task(run_scheduler())
    yield


app = FastAPI(title="VCore Agent Chat", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── WebSocket connection manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        # channel_id → list of (websocket, agent_id)
        self._connections: dict[str, list[tuple[WebSocket, str]]] = {}

    async def connect(self, ws: WebSocket, channel_id: str, agent_id: str):
        await ws.accept()
        self._connections.setdefault(channel_id, []).append((ws, agent_id))

    def disconnect(self, ws: WebSocket, channel_id: str):
        if channel_id in self._connections:
            self._connections[channel_id] = [
                (w, a) for w, a in self._connections[channel_id] if w is not ws
            ]

    async def broadcast(self, channel_id: str, message: dict):
        dead = []
        for ws, agent_id in self._connections.get(channel_id, []):
            if agent_can_read(agent_id, channel_id):
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((ws, channel_id))
        for ws, cid in dead:
            self.disconnect(ws, cid)

    def online_agents(self, channel_id: str) -> list[str]:
        return [a for _, a in self._connections.get(channel_id, [])]


manager = ConnectionManager()


# ── REST: agents & channels ───────────────────────────────────────────────────

@app.get("/api/agents")
async def list_agents():
    return list(AGENTS.values())


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    for a in AGENTS.values():
        if a["id"] == agent_id:
            return a
    raise HTTPException(404, "Agent not found")


@app.get("/api/channels")
async def list_channels(agent_id: str = Query("user")):
    visible = get_visible_channels(agent_id)
    # Attach DM channels
    dms = await get_dm_channels_for_agent(agent_id)
    for dm in dms:
        other = dm["agent_b"] if dm["agent_a"] == agent_id else dm["agent_a"]
        visible.append({
            "id": dm["id"],
            "name": dm["id"],
            "display": f"@ {other}",
            "type": "dm",
            "description": f"DM with {other}",
            "allowed_agents": [dm["agent_a"], dm["agent_b"]],
            "icon": "💬",
        })
    return visible


@app.get("/api/channels/{channel_id}/messages")
async def channel_messages(
    channel_id: str,
    agent_id: str = Query("user"),
    limit: int = Query(100, le=500),
    before_id: Optional[int] = Query(None),
):
    if not agent_can_read(agent_id, channel_id):
        raise HTTPException(403, "Access denied to this channel")
    msgs = await get_messages(channel_id, limit=limit, before_id=before_id)
    return msgs


# ── REST: send message (HTTP fallback, WS preferred) ─────────────────────────

class SendMessageRequest(BaseModel):
    agent_id: str
    content: str
    msg_type: str = "text"
    metadata: Optional[dict] = None


@app.post("/api/channels/{channel_id}/messages")
async def send_message(channel_id: str, req: SendMessageRequest):
    if not agent_can_post(req.agent_id, channel_id):
        raise HTTPException(403, "Agent cannot post to this channel")

    agent = None
    for a in AGENTS.values():
        if a["id"] == req.agent_id:
            agent = a
            break
    if agent is None:
        raise HTTPException(404, "Agent not found")

    msg = await save_message(
        channel_id=channel_id,
        agent_id=req.agent_id,
        agent_name=agent["display"],
        content=req.content,
        msg_type=req.msg_type,
        metadata=req.metadata,
    )
    await manager.broadcast(channel_id, {"event": "message", "data": msg})
    return msg


# ── REST: DM ──────────────────────────────────────────────────────────────────

@app.post("/api/dm/{agent_a}/{agent_b}")
async def open_dm(agent_a: str, agent_b: str):
    dm_id = await get_or_create_dm(agent_a, agent_b)
    return {"dm_channel_id": dm_id}


# ── REST: export ──────────────────────────────────────────────────────────────

@app.post("/api/export")
async def trigger_export(date: Optional[str] = None):
    out_dir = await export_day(date)
    return {"status": "ok", "export_path": str(out_dir)}


# ── WebSocket: real-time messaging ────────────────────────────────────────────

@app.websocket("/ws/{channel_id}/{agent_id}")
async def websocket_endpoint(ws: WebSocket, channel_id: str, agent_id: str):
    if not agent_can_read(agent_id, channel_id):
        await ws.close(code=4003)
        return

    await manager.connect(ws, channel_id, agent_id)

    # Notify channel of join
    agent_name = next(
        (a["display"] for a in AGENTS.values() if a["id"] == agent_id), agent_id
    )
    join_msg = await save_message(
        channel_id, "system", "SYSTEM",
        f"{agent_name} joined #{channel_id}", "system"
    )
    await manager.broadcast(channel_id, {"event": "join", "data": join_msg})

    try:
        while True:
            raw = await ws.receive_text()
            payload = json.loads(raw)
            action = payload.get("action", "send")

            if action == "send":
                content = payload.get("content", "").strip()
                if not content:
                    continue
                if not agent_can_post(agent_id, channel_id):
                    await ws.send_json({"event": "error", "data": {"message": "Permission denied"}})
                    continue
                msg = await save_message(
                    channel_id=channel_id,
                    agent_id=agent_id,
                    agent_name=agent_name,
                    content=content,
                    msg_type=payload.get("msg_type", "text"),
                    metadata=payload.get("metadata"),
                )
                await manager.broadcast(channel_id, {"event": "message", "data": msg})

            elif action == "ping":
                await ws.send_json({"event": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(ws, channel_id)
        leave_msg = await save_message(
            channel_id, "system", "SYSTEM",
            f"{agent_name} left #{channel_id}", "system"
        )
        await manager.broadcast(channel_id, {"event": "leave", "data": leave_msg})


# ── Serve frontend ────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return FileResponse("templates/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "VCore Agent Chat", "timestamp": datetime.now(timezone.utc).isoformat()}
