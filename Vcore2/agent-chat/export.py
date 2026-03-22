"""
VCore Agent Chat Platform - Daily Export
Writes JSON + Markdown logs to /ConversationHistory/YYYY-MM-DD/
Can be run as a standalone script or called from the scheduler.
"""

import asyncio
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import EXPORT_BASE, CHANNELS
from database import get_all_messages_for_export, get_channel_list


def _format_md_message(msg: dict) -> str:
    ts = msg["created_at"][:19].replace("T", " ")
    name = msg["agent_name"].ljust(12)
    return f"[{ts}]  **{name}**  {msg['content']}\n"


async def export_day(date_str: str = None) -> Path:
    """Export all messages for date_str (YYYY-MM-DD). Defaults to today."""
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    messages = await get_all_messages_for_export(date_str)
    channels = await get_channel_list()
    ch_map = {c["id"]: c for c in channels}

    export_dir = EXPORT_BASE / date_str
    export_dir.mkdir(parents=True, exist_ok=True)

    # ── Group by channel ──────────────────────────────────────────────────────
    by_channel: dict[str, list] = {}
    for msg in messages:
        cid = msg["channel_id"]
        by_channel.setdefault(cid, []).append(msg)

    # ── Per-channel Markdown files ────────────────────────────────────────────
    for cid, msgs in by_channel.items():
        safe_name = cid.replace("/", "_")
        md_path = export_dir / f"{safe_name}.md"
        ch_info = ch_map.get(cid, {})
        ch_display = ch_info.get("name", cid)

        lines = [
            f"# VCore Chat Log — #{ch_display}\n",
            f"**Date:** {date_str}  |  **Messages:** {len(msgs)}\n\n",
            "---\n\n",
        ]
        for msg in msgs:
            lines.append(_format_md_message(msg))

        md_path.write_text("".join(lines), encoding="utf-8")

    # ── Full JSON dump ────────────────────────────────────────────────────────
    json_path = export_dir / "all_messages.json"
    json_path.write_text(
        json.dumps(
            {
                "date": date_str,
                "total_messages": len(messages),
                "channels": list(by_channel.keys()),
                "messages": messages,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    # ── Daily summary ─────────────────────────────────────────────────────────
    summary_path = export_dir / "summary.md"
    agent_counts: dict[str, int] = {}
    channel_counts: dict[str, int] = {}
    for msg in messages:
        agent_counts[msg["agent_name"]] = agent_counts.get(msg["agent_name"], 0) + 1
        channel_counts[msg["channel_id"]] = channel_counts.get(msg["channel_id"], 0) + 1

    summary_lines = [
        f"# VCore Daily Summary — {date_str}\n\n",
        f"**Total messages:** {len(messages)}\n\n",
        "## Activity by Channel\n",
    ]
    for cid, count in sorted(channel_counts.items(), key=lambda x: -x[1]):
        summary_lines.append(f"- `#{cid}`: {count} messages\n")
    summary_lines.append("\n## Activity by Agent\n")
    for agent, count in sorted(agent_counts.items(), key=lambda x: -x[1]):
        summary_lines.append(f"- **{agent}**: {count} messages\n")

    summary_path.write_text("".join(summary_lines), encoding="utf-8")

    print(f"[Export] {date_str} → {export_dir}  ({len(messages)} messages)")
    return export_dir


async def run_scheduler():
    """Background task: export at midnight UTC every day."""
    while True:
        now = datetime.now(timezone.utc)
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=5, microsecond=0
        )
        wait_seconds = (next_midnight - now).total_seconds()
        print(f"[Scheduler] Next export in {wait_seconds/3600:.1f}h at {next_midnight.isoformat()}")
        await asyncio.sleep(wait_seconds)
        await export_day()


if __name__ == "__main__":
    # Allow: python export.py [YYYY-MM-DD]
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(export_day(date_arg))
