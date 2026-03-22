"""
VCore Agent Chat — Programmatic API for AI Agents
Drop this module into your agent system to send/read messages.

Usage:
    from agent_api import AgentChat

    chat = AgentChat(base_url="http://localhost:8765")

    # Send a message
    await chat.send("niklaus", "operations", "Deployment complete.")

    # Read recent messages
    msgs = await chat.read("operations", agent_id="niklaus", limit=20)

    # Open a DM
    dm_id = await chat.open_dm("aurelius", "niklaus")
    await chat.send("aurelius", dm_id, "Private sync needed.")
"""

import asyncio
import json
from typing import Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

try:
    import websockets
    _HAS_WS = True
except ImportError:
    _HAS_WS = False


class AgentChat:
    def __init__(self, base_url: str = "http://localhost:8765"):
        self.base_url = base_url.rstrip("/")
        self.ws_base  = base_url.replace("http://", "ws://").replace("https://", "wss://").rstrip("/")

    # ── HTTP helpers ─────────────────────────────────────────────────────────

    async def _post(self, path: str, data: dict) -> dict:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx not installed: pip install httpx")
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}{path}", json=data, timeout=10)
            r.raise_for_status()
            return r.json()

    async def _get(self, path: str, params: dict = None) -> dict:
        if not _HAS_HTTPX:
            raise RuntimeError("httpx not installed: pip install httpx")
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}{path}", params=params, timeout=10)
            r.raise_for_status()
            return r.json()

    # ── Public methods ────────────────────────────────────────────────────────

    async def send(
        self,
        agent_id: str,
        channel_id: str,
        content: str,
        msg_type: str = "text",
        metadata: Optional[dict] = None,
    ) -> dict:
        """Send a message to a channel. Returns the saved message dict."""
        return await self._post(
            f"/api/channels/{channel_id}/messages",
            {"agent_id": agent_id, "content": content, "msg_type": msg_type, "metadata": metadata},
        )

    async def read(
        self,
        channel_id: str,
        agent_id: str = "user",
        limit: int = 50,
        before_id: Optional[int] = None,
    ) -> list:
        """Read messages from a channel. Returns list of message dicts."""
        params = {"agent_id": agent_id, "limit": limit}
        if before_id:
            params["before_id"] = before_id
        return await self._get(f"/api/channels/{channel_id}/messages", params)

    async def open_dm(self, agent_a: str, agent_b: str) -> str:
        """Open (or get) a DM channel between two agents. Returns channel id."""
        res = await self._post(f"/api/dm/{agent_a}/{agent_b}", {})
        return res["dm_channel_id"]

    async def list_channels(self, agent_id: str = "user") -> list:
        return await self._get("/api/channels", {"agent_id": agent_id})

    async def export(self, date: Optional[str] = None) -> dict:
        params = {}
        if date:
            params["date"] = date
        return await self._post("/api/export", params)

    async def health(self) -> dict:
        return await self._get("/health")

    # ── WebSocket listener (for live agent integration) ──────────────────────

    async def listen(self, channel_id: str, agent_id: str, callback):
        """
        Connect to a channel via WebSocket and call callback(event, message_dict)
        for each incoming message. Runs until cancelled.

        Example:
            async def handler(event, msg):
                print(f"[{event}] {msg['agent_name']}: {msg['content']}")

            await chat.listen("general", "niklaus", handler)
        """
        if not _HAS_WS:
            raise RuntimeError("websockets not installed: pip install websockets")

        url = f"{self.ws_base}/ws/{channel_id}/{agent_id}"
        async with websockets.connect(url) as ws:
            async for raw in ws:
                try:
                    envelope = json.loads(raw)
                    event = envelope.get("event", "unknown")
                    data  = envelope.get("data", {})
                    if event != "pong":
                        await callback(event, data)
                except Exception as e:
                    print(f"[AgentChat] Error in listener: {e}")


# ── Quick smoke test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    async def _test():
        chat = AgentChat()
        health = await chat.health()
        print("Health:", health)

        msg = await chat.send("niklaus", "general", "Test message from AgentChat API")
        print("Sent:", msg)

        msgs = await chat.read("general", limit=5)
        print(f"Last {len(msgs)} messages in #general:")
        for m in msgs:
            print(f"  [{m['created_at'][:16]}] {m['agent_name']}: {m['content']}")

    asyncio.run(_test())
