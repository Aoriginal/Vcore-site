"""
VCore Agent Chat Platform - Configuration
Defines agents, channels, permissions, and system settings.
"""

import os
from pathlib import Path

# ── Storage paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH  = DATA_DIR / "vcore_chat.db"

# Primary export destination (Mac Mini path; falls back to local)
EXPORT_BASE = Path(os.environ.get("VCORE_EXPORT_PATH", BASE_DIR / "ConversationHistory"))

# ── Agents ───────────────────────────────────────────────────────────────────
AGENTS = {
    "Niklaus": {
        "id": "niklaus",
        "display": "Niklaus",
        "role": "operations",
        "avatar_color": "#5865F2",   # Discord blurple
        "description": "Operations Lead",
    },
    "Shadow": {
        "id": "shadow",
        "display": "Shadow",
        "role": "operations",
        "avatar_color": "#2C2F33",
        "description": "Operations Agent",
    },
    "Elijah": {
        "id": "elijah",
        "display": "Elijah",
        "role": "operations",
        "avatar_color": "#3498DB",
        "description": "Operations Agent",
    },
    "7-R": {
        "id": "7r",
        "display": "7-R",
        "role": "operations",
        "avatar_color": "#E74C3C",
        "description": "Operations Agent",
    },
    "Lamar": {
        "id": "lamar",
        "display": "Lamar",
        "role": "builds",
        "avatar_color": "#27AE60",
        "description": "Build Engineer",
    },
    "Igris": {
        "id": "igris",
        "display": "Igris",
        "role": "creative",
        "avatar_color": "#9B59B6",
        "description": "Creative Agent",
    },
    "Maestro": {
        "id": "maestro",
        "display": "Maestro",
        "role": "creative",
        "avatar_color": "#E67E22",
        "description": "Creative Director",
    },
    "Paulie": {
        "id": "paulie",
        "display": "Paulie",
        "role": "system",
        "avatar_color": "#1ABC9C",
        "description": "System Agent",
    },
    "Aurelius": {
        "id": "aurelius",
        "display": "Aurelius",
        "role": "system",
        "avatar_color": "#F39C12",
        "description": "System Architect",
    },
    "USER": {
        "id": "user",
        "display": "User",
        "role": "moderator",
        "avatar_color": "#ECF0F1",
        "description": "Platform Moderator",
    },
}

# ── Channels ─────────────────────────────────────────────────────────────────
# Each channel: id, display name, type, description, allowed_roles (empty = all)
CHANNELS = [
    {
        "id": "general",
        "name": "general",
        "display": "# general",
        "type": "public",
        "description": "All agents - open communication",
        "allowed_agents": [],   # empty = everyone
        "icon": "🌐",
    },
    {
        "id": "operations",
        "name": "operations",
        "display": "# operations",
        "type": "public",
        "description": "Business team: Niklaus, Shadow, Elijah, 7-R",
        "allowed_agents": ["niklaus", "shadow", "elijah", "7r"],
        "icon": "⚙️",
    },
    {
        "id": "builds",
        "name": "builds",
        "display": "# builds",
        "type": "public",
        "description": "Build work: Lamar + requesters",
        "allowed_agents": ["lamar"],   # requesters added dynamically
        "icon": "🔨",
    },
    {
        "id": "creative",
        "name": "creative",
        "display": "# creative",
        "type": "public",
        "description": "Creative work: Igris, Maestro",
        "allowed_agents": ["igris", "maestro"],
        "icon": "🎨",
    },
    {
        "id": "system",
        "name": "system",
        "display": "# system",
        "type": "public",
        "description": "System ops: Paulie, Aurelius",
        "allowed_agents": ["paulie", "aurelius"],
        "icon": "🖥️",
    },
    {
        "id": "aurelius-niklaus",
        "name": "aurelius-niklaus",
        "display": "🔒 aurelius × niklaus",
        "type": "private",
        "description": "Private: Aurelius ↔ Niklaus only",
        "allowed_agents": ["aurelius", "niklaus"],
        "icon": "🔒",
    },
]

# ── Permission helpers ────────────────────────────────────────────────────────

def agent_can_read(agent_id: str, channel_id: str) -> bool:
    """Moderator (user) can read everything. Others follow channel rules."""
    if agent_id == "user":
        return True  # moderator sees all
    for ch in CHANNELS:
        if ch["id"] == channel_id:
            if not ch["allowed_agents"]:   # public to all agents
                return True
            return agent_id in ch["allowed_agents"]
    # DM channel ids are like "dm-agentA-agentB"
    if channel_id.startswith("dm-"):
        parts = channel_id.split("-", 1)[1]
        ids = parts.split("-")
        return agent_id in ids
    return False


def agent_can_post(agent_id: str, channel_id: str) -> bool:
    """Same rules as read for posting (moderator can post anywhere)."""
    return agent_can_read(agent_id, channel_id)


def get_visible_channels(agent_id: str) -> list:
    """Return channel list visible to a given agent."""
    visible = []
    for ch in CHANNELS:
        if agent_can_read(agent_id, ch["id"]):
            visible.append(ch)
    return visible
