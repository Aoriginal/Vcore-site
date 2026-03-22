"""
VCore Pattern Extraction System
Analyzes conversation logs and generates playbooks.

Reads: /SecondBrain/ConversationHistory/*/all_messages.json
Writes: /SecondBrain/SharedKnowledge/Playbooks/*.md

Usage:
    python extractor.py                        # analyze last 7 days
    python extractor.py --days 30              # analyze last 30 days
    python extractor.py --date 2026-05-01      # analyze specific date
    python extractor.py --output /path/to/out  # custom output dir
    python extractor.py --summary              # print summary only, no file write
"""

import json
import re
import sys
import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


# ── Paths ─────────────────────────────────────────────────────────────────────

DEFAULT_HISTORY_DIR = Path(
    __file__).parent.parent.parent / "SecondBrain" / "ConversationHistory"
DEFAULT_PLAYBOOK_DIR = Path(
    __file__).parent.parent.parent / "SecondBrain" / "SharedKnowledge" / "Playbooks"

CATEGORIES = ["messaging", "copy", "pricing", "retention", "operations", "builds", "creative", "system"]


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class Message:
    id: int
    channel_id: str
    agent_id: str
    agent_name: str
    content: str
    msg_type: str
    created_at: str

    @classmethod
    def from_dict(cls, d: dict) -> "Message":
        return cls(
            id=d.get("id", 0),
            channel_id=d.get("channel_id", ""),
            agent_id=d.get("agent_id", ""),
            agent_name=d.get("agent_name", ""),
            content=d.get("content", ""),
            msg_type=d.get("msg_type", "text"),
            created_at=d.get("created_at", ""),
        )


@dataclass
class Pattern:
    name: str
    category: str
    evidence: list[str]
    frequency: int
    sentiment: str   # positive | negative | neutral
    application: str
    confidence: str  # Low | Medium | High


@dataclass
class AnalysisResult:
    date_range: str
    total_messages: int
    messages_by_channel: dict
    messages_by_agent: dict
    active_agents: list
    patterns: list[Pattern]
    wins: list[str]
    losses: list[str]
    keywords: dict          # category → Counter
    agent_interactions: dict  # (agent_a, agent_b) → count
    channel_activity: dict   # hour → count


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_messages_for_date(history_dir: Path, date_str: str) -> list[Message]:
    """Load all messages from a specific date's JSON export."""
    json_path = history_dir / date_str / "all_messages.json"
    if not json_path.exists():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        messages = data.get("messages", [])
        return [Message.from_dict(m) for m in messages if m.get("msg_type") != "system"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  [WARN] Could not parse {json_path}: {e}")
        return []


def load_messages_for_range(history_dir: Path, days: int) -> list[Message]:
    """Load messages from the last N days."""
    all_messages = []
    today = datetime.now(timezone.utc)
    for i in range(days):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        msgs = load_messages_for_date(history_dir, date_str)
        all_messages.extend(msgs)
        if msgs:
            print(f"  Loaded {len(msgs):4d} messages from {date_str}")
    return all_messages


# ── Signal detection ───────────────────────────────────────────────────────────

# Keyword signals mapped to categories
CATEGORY_SIGNALS = {
    "messaging": [
        "message", "email", "outreach", "follow.up", "reply", "response",
        "cold", "warm", "subject", "open rate", "click", "send", "inbox",
        "dm", "sequence", "template", "outbound",
    ],
    "copy": [
        "copy", "headline", "landing page", "cta", "button", "hook",
        "hook", "ad", "tagline", "description", "title", "body",
        "write", "draft", "tone", "voice", "brand",
    ],
    "pricing": [
        "price", "pricing", "cost", "fee", "charge", "rate", "plan",
        "tier", "subscription", "annual", "monthly", "discount", "deal",
        "negotiat", "objection", "budget", "expensive", "cheap",
    ],
    "retention": [
        "retain", "retention", "churn", "cancel", "unsubscribe", "renew",
        "engage", "engagement", "active", "inactive", "lapsed", "return",
        "onboard", "activate", "aha moment", "day 7", "day 30",
    ],
    "operations": [
        "operation", "process", "workflow", "task", "deploy", "execute",
        "coordinate", "manage", "assign", "delegate", "plan", "schedule",
        "blocker", "milestone", "sprint",
    ],
    "builds": [
        "build", "code", "implement", "develop", "feature", "bug",
        "fix", "deploy", "test", "review", "merge", "branch", "api",
        "database", "server", "frontend", "backend",
    ],
    "creative": [
        "creative", "design", "brand", "visual", "color", "font",
        "image", "illustration", "campaign", "concept", "story",
        "narrative", "aesthetic", "style",
    ],
    "system": [
        "system", "infrastructure", "server", "monitor", "health",
        "alert", "incident", "downtime", "performance", "config",
        "environment", "setup", "architecture",
    ],
}

WIN_SIGNALS = [
    r'\b(done|complete|finished|shipped|working|success|solved|fixed|deployed)\b',
    r'\b(win|won|got it|nailed it|worked|landed|closed)\b',
    r'\b(approved|accepted|merged|confirmed|agreed)\b',
]

LOSS_SIGNALS = [
    r'\b(fail|failed|broke|broken|blocked|stuck|issue|problem|bug|error)\b',
    r'\b(reject|declined|cancelled|lost|didn.t work|not working)\b',
    r'\b(too slow|too expensive|not interested|no response|ghosted)\b',
]

QUESTION_PATTERN = re.compile(r'\?$', re.MULTILINE)


def detect_sentiment(content: str) -> str:
    cl = content.lower()
    win_score = sum(1 for p in WIN_SIGNALS if re.search(p, cl))
    loss_score = sum(1 for p in LOSS_SIGNALS if re.search(p, cl))
    if win_score > loss_score:
        return "positive"
    if loss_score > win_score:
        return "negative"
    return "neutral"


def categorize_message(content: str) -> list[str]:
    cl = content.lower()
    matched = []
    for category, signals in CATEGORY_SIGNALS.items():
        if any(re.search(r'\b' + s + r'\b', cl) for s in signals):
            matched.append(category)
    return matched if matched else ["general"]


# ── Pattern extraction ─────────────────────────────────────────────────────────

def extract_key_phrases(messages: list[Message], category: str) -> list[str]:
    """Extract notable phrases from messages in a category."""
    signals = CATEGORY_SIGNALS.get(category, [])
    relevant = []
    for msg in messages:
        cl = msg.content.lower()
        if any(re.search(r'\b' + s + r'\b', cl) for s in signals):
            # Find the sentence containing the signal
            sentences = re.split(r'[.!?\n]', msg.content)
            for sent in sentences:
                sent = sent.strip()
                if len(sent) > 20 and any(
                    re.search(r'\b' + s + r'\b', sent.lower()) for s in signals
                ):
                    relevant.append(f"{msg.agent_name}: {sent}")
    return relevant[:10]  # cap at 10 examples


def find_patterns(messages: list[Message]) -> list[Pattern]:
    patterns = []

    # ── Pattern: Most active channel analysis ─────────────────────────────────
    channel_counts = Counter(m.channel_id for m in messages)
    if channel_counts:
        top_channel, top_count = channel_counts.most_common(1)[0]
        patterns.append(Pattern(
            name=f"#{top_channel} is the primary communication hub",
            category="operations",
            evidence=[
                f"{top_count} messages in #{top_channel} during analysis period",
                f"Activity distribution: " + ", ".join(
                    f"#{ch}: {cnt}" for ch, cnt in channel_counts.most_common(5)
                ),
            ],
            frequency=top_count,
            sentiment="neutral",
            application=f"Prioritize #{top_channel} for important announcements. "
                       f"Agents check this channel most frequently.",
            confidence="High" if top_count > 20 else "Medium",
        ))

    # ── Pattern: Agent responsiveness ─────────────────────────────────────────
    agent_counts = Counter(m.agent_id for m in messages if m.agent_id != "system")
    if len(agent_counts) >= 2:
        most_active = agent_counts.most_common(3)
        patterns.append(Pattern(
            name="Agent activity distribution",
            category="operations",
            evidence=[
                f"{name}: {count} messages" for name, count in most_active
            ],
            frequency=sum(agent_counts.values()),
            sentiment="neutral",
            application="Assign high-volume tasks to agents with demonstrated activity. "
                       "Low-activity agents may need direct prompting.",
            confidence="High" if len(messages) > 50 else "Low",
        ))

    # ── Pattern: Question density ──────────────────────────────────────────────
    question_msgs = [m for m in messages if '?' in m.content]
    q_rate = len(question_msgs) / max(len(messages), 1)
    if q_rate > 0.15:
        patterns.append(Pattern(
            name="High question rate — agents need clearer briefs",
            category="operations",
            evidence=[
                f"{len(question_msgs)} questions out of {len(messages)} messages ({q_rate:.0%} rate)",
                "Sample questions: " + "; ".join(
                    m.content[:60] + "..." for m in question_msgs[:3]
                ),
            ],
            frequency=len(question_msgs),
            sentiment="negative",
            application="Improve task brief quality using the task-brief-template. "
                       "High question rate indicates ambiguous requirements.",
            confidence="Medium" if len(messages) > 20 else "Low",
        ))

    # ── Pattern: Category-specific wins ───────────────────────────────────────
    for category in CATEGORIES:
        cat_messages = [m for m in messages if category in categorize_message(m.content)]
        if not cat_messages:
            continue

        positive = [m for m in cat_messages if detect_sentiment(m.content) == "positive"]
        negative = [m for m in cat_messages if detect_sentiment(m.content) == "negative"]

        if positive:
            patterns.append(Pattern(
                name=f"{category.title()}: {len(positive)} positive signals",
                category=category,
                evidence=[m.content[:100] for m in positive[:3]],
                frequency=len(positive),
                sentiment="positive",
                application=f"Continue approaches that generated positive {category} signals. "
                           f"See examples above for what worked.",
                confidence="High" if len(positive) > 5 else "Medium" if len(positive) > 2 else "Low",
            ))

        if negative:
            patterns.append(Pattern(
                name=f"{category.title()}: {len(negative)} friction points",
                category=category,
                evidence=[m.content[:100] for m in negative[:3]],
                frequency=len(negative),
                sentiment="negative",
                application=f"Address recurring {category} friction. "
                           f"Review examples above to identify root causes.",
                confidence="High" if len(negative) > 5 else "Medium" if len(negative) > 2 else "Low",
            ))

    # ── Pattern: Time-of-day activity ─────────────────────────────────────────
    hour_counts = Counter()
    for msg in messages:
        try:
            dt = datetime.fromisoformat(msg.created_at.replace("Z", "+00:00"))
            hour_counts[dt.hour] += 1
        except (ValueError, AttributeError):
            pass

    if hour_counts:
        peak_hour, peak_count = hour_counts.most_common(1)[0]
        patterns.append(Pattern(
            name=f"Peak activity at {peak_hour:02d}:00 UTC",
            category="operations",
            evidence=[
                f"{peak_count} messages at hour {peak_hour}:00 UTC",
                "Hourly distribution: " + ", ".join(
                    f"{h:02d}h:{c}" for h, c in sorted(hour_counts.most_common(5))
                ),
            ],
            frequency=peak_count,
            sentiment="neutral",
            application=f"Schedule important decisions and announcements around "
                       f"{peak_hour:02d}:00 UTC when agent activity peaks.",
            confidence="Medium" if len(messages) > 100 else "Low",
        ))

    return patterns


# ── Analysis ────────────────────────────────────────────────────────────────────

def analyze(messages: list[Message], date_range: str) -> AnalysisResult:
    """Run full analysis on a set of messages."""
    # Basic counts
    by_channel = dict(Counter(m.channel_id for m in messages).most_common())
    by_agent = dict(Counter(m.agent_name for m in messages).most_common())
    active_agents = [a for a, _ in Counter(m.agent_name for m in messages).most_common()]

    # Win/loss extraction
    wins, losses = [], []
    for msg in messages:
        cl = msg.content.lower()
        if any(re.search(p, cl) for p in WIN_SIGNALS):
            wins.append(f"[{msg.channel_id}] {msg.agent_name}: {msg.content[:120]}")
        if any(re.search(p, cl) for p in LOSS_SIGNALS):
            losses.append(f"[{msg.channel_id}] {msg.agent_name}: {msg.content[:120]}")

    # Category keyword counts
    keywords = {}
    for category, signals in CATEGORY_SIGNALS.items():
        counter = Counter()
        for msg in messages:
            for signal in signals:
                matches = re.findall(r'\b' + signal + r'\b', msg.content.lower())
                counter[signal] += len(matches)
        keywords[category] = dict(counter.most_common(5))

    # Agent interaction graph (who responds after whom)
    interactions = Counter()
    sorted_msgs = sorted(messages, key=lambda m: m.created_at)
    for i in range(1, len(sorted_msgs)):
        prev = sorted_msgs[i - 1]
        curr = sorted_msgs[i]
        if prev.channel_id == curr.channel_id and prev.agent_id != curr.agent_id:
            pair = tuple(sorted([prev.agent_id, curr.agent_id]))
            interactions[pair] += 1

    # Hour activity
    hour_activity = Counter()
    for msg in messages:
        try:
            dt = datetime.fromisoformat(msg.created_at.replace("Z", "+00:00"))
            hour_activity[dt.hour] += 1
        except (ValueError, AttributeError):
            pass

    # Find patterns
    patterns = find_patterns(messages)

    return AnalysisResult(
        date_range=date_range,
        total_messages=len(messages),
        messages_by_channel=by_channel,
        messages_by_agent=by_agent,
        active_agents=active_agents,
        patterns=patterns,
        wins=wins[:20],
        losses=losses[:20],
        keywords=keywords,
        agent_interactions=dict(interactions.most_common(10)),
        channel_activity=dict(hour_activity),
    )


# ── Playbook generation ────────────────────────────────────────────────────────

def _confidence_to_icon(c: str) -> str:
    return {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(c, "⚪")


def _sentiment_to_label(s: str) -> str:
    return {"positive": "✅ Win", "negative": "⚠️ Friction", "neutral": "📊 Insight"}.get(s, s)


def generate_playbook_update(result: AnalysisResult, category: str) -> str:
    """Generate a Markdown playbook section for a category."""
    cat_patterns = [p for p in result.patterns if p.category == category]
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"## Auto-Generated Patterns — {result.date_range}\n",
        f"*Generated {now_str} | {result.total_messages} messages analyzed*\n\n",
        "---\n\n",
    ]

    if not cat_patterns:
        lines.append(f"*No significant {category} patterns detected in this period. "
                     f"Accumulate more conversation data for richer analysis.*\n")
        return "".join(lines)

    for pattern in cat_patterns:
        conf_icon = _confidence_to_icon(pattern.confidence)
        sentiment_label = _sentiment_to_label(pattern.sentiment)

        lines.append(f"### {sentiment_label}: {pattern.name}\n")
        lines.append(f"**Confidence:** {conf_icon} {pattern.confidence} | "
                     f"**Frequency:** {pattern.frequency} signals\n\n")
        lines.append("**Evidence:**\n")
        for ev in pattern.evidence:
            lines.append(f"- {ev}\n")
        lines.append(f"\n**Application:** {pattern.application}\n\n")
        lines.append("---\n\n")

    return "".join(lines)


def generate_full_report(result: AnalysisResult, output_dir: Path) -> list[Path]:
    """Write playbook updates + summary report to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    # ── Per-category playbook inserts ─────────────────────────────────────────
    for category in CATEGORIES:
        playbook_path = output_dir / f"{category}.md"
        insert = generate_playbook_update(result, category)

        if playbook_path.exists():
            # Append new section after existing content
            existing = playbook_path.read_text(encoding="utf-8")
            # Remove old auto-generated section if present
            existing = re.sub(
                r'## Auto-Generated Patterns.*?(?=^## |\Z)',
                '', existing, flags=re.DOTALL | re.MULTILINE
            ).rstrip()
            new_content = existing + "\n\n" + insert
        else:
            # Create new playbook
            new_content = (
                f"# Playbook: {category.title()}\n"
                f"**Category:** {category.title()} | **Version:** auto\n\n"
                f"*Auto-generated by VCore Pattern Extractor*\n\n---\n\n"
                + insert
            )

        playbook_path.write_text(new_content, encoding="utf-8")
        written.append(playbook_path)

    # ── Master summary report ─────────────────────────────────────────────────
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report_lines = [
        f"# VCore Pattern Analysis Report\n",
        f"**Generated:** {now_str}\n",
        f"**Period:** {result.date_range}\n",
        f"**Total messages analyzed:** {result.total_messages}\n\n",
        "---\n\n",

        "## Activity Overview\n\n",
        "### By Channel\n",
    ]
    for ch, cnt in result.messages_by_channel.items():
        bar = "█" * min(int(cnt / max(result.total_messages, 1) * 40), 40)
        report_lines.append(f"| `#{ch}` | {cnt:4d} | {bar} |\n")

    report_lines += [
        "\n### By Agent\n",
    ]
    for agent, cnt in result.messages_by_agent.items():
        report_lines.append(f"| **{agent}** | {cnt} |\n")

    report_lines += [
        "\n---\n\n",
        "## Active Agents This Period\n",
        ", ".join(result.active_agents) + "\n\n",

        "---\n\n",
        "## Wins Detected\n",
    ]
    if result.wins:
        for w in result.wins[:10]:
            report_lines.append(f"- {w}\n")
    else:
        report_lines.append("*No wins detected — try adding outcome keywords to messages.*\n")

    report_lines += ["\n## Friction Points Detected\n"]
    if result.losses:
        for l in result.losses[:10]:
            report_lines.append(f"- {l}\n")
    else:
        report_lines.append("*No friction points detected.*\n")

    report_lines += [
        "\n---\n\n",
        "## Patterns Found\n",
    ]
    for p in result.patterns:
        conf_icon = _confidence_to_icon(p.confidence)
        report_lines.append(
            f"- {conf_icon} **[{p.category}]** {p.name} "
            f"*(conf: {p.confidence}, freq: {p.frequency})*\n"
        )

    report_lines += [
        "\n---\n\n",
        "## Most Active Agent Pairs\n",
    ]
    for (a, b), cnt in result.agent_interactions.items():
        report_lines.append(f"- {a} ↔ {b}: {cnt} interactions\n")

    report_lines += [
        "\n---\n\n",
        "*Playbooks updated in /SecondBrain/SharedKnowledge/Playbooks/*\n",
    ]

    report_path = output_dir / f"analysis-report-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    report_path.write_text("".join(report_lines), encoding="utf-8")
    written.append(report_path)

    return written


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="VCore Pattern Extractor — analyze conversation logs and update playbooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extractor.py                   # last 7 days
  python extractor.py --days 30         # last 30 days
  python extractor.py --date 2026-05-01 # specific date
  python extractor.py --summary         # print summary, don't write playbooks
  python extractor.py --history /path/to/ConversationHistory
  python extractor.py --output /path/to/Playbooks
        """,
    )
    parser.add_argument('--days', type=int, default=7, help='Days to analyze (default: 7)')
    parser.add_argument('--date', help='Analyze specific date YYYY-MM-DD')
    parser.add_argument('--history', help='Path to ConversationHistory dir', default=str(DEFAULT_HISTORY_DIR))
    parser.add_argument('--output', help='Output dir for playbooks', default=str(DEFAULT_PLAYBOOK_DIR))
    parser.add_argument('--summary', action='store_true', help='Print summary only, no file writes')
    parser.add_argument('--categories', nargs='+', choices=CATEGORIES,
                        help='Limit to specific categories')

    args = parser.parse_args()

    history_dir = Path(args.history)
    output_dir = Path(args.output)

    print("")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  VCore Pattern Extractor")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  History: {history_dir}")
    print(f"  Output:  {output_dir}")
    print("")

    if not history_dir.exists():
        print(f"[ERROR] History dir not found: {history_dir}")
        print("  Make sure VCore Agent Chat has been running and exporting logs.")
        print(f"  Expected path: {history_dir}")
        sys.exit(1)

    # Load messages
    if args.date:
        print(f"Loading messages for {args.date}...")
        messages = load_messages_for_date(history_dir, args.date)
        date_range = args.date
    else:
        print(f"Loading messages from last {args.days} days...")
        messages = load_messages_for_range(history_dir, args.days)
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=args.days)
        date_range = f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"

    if not messages:
        print(f"\n[WARN] No messages found for this period.")
        print("  Run VCore Agent Chat and send some messages first.")
        print("  Then trigger an export via the UI or: python export.py")
        sys.exit(0)

    print(f"\nLoaded {len(messages)} messages. Analyzing...")

    result = analyze(messages, date_range)

    # Print summary
    print("")
    print(f"  Period:    {date_range}")
    print(f"  Messages:  {result.total_messages}")
    print(f"  Agents:    {', '.join(result.active_agents[:5])}"
          + (f" + {len(result.active_agents)-5} more" if len(result.active_agents) > 5 else ""))
    print(f"  Channels:  {', '.join(f'#{k}' for k in list(result.messages_by_channel.keys())[:5])}")
    print(f"  Wins:      {len(result.wins)}")
    print(f"  Friction:  {len(result.losses)}")
    print(f"  Patterns:  {len(result.patterns)}")
    print("")

    if args.summary:
        print("Patterns found:")
        for p in result.patterns:
            print(f"  [{p.category}] {p.name} (conf: {p.confidence})")
        return

    # Write playbooks
    written = generate_full_report(result, output_dir)
    print(f"Written {len(written)} files:")
    for path in written:
        print(f"  → {path}")

    print("")
    print("✅ Done. Playbooks updated.")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
