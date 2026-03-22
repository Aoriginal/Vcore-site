# VCore Pattern Extractor

Analyzes conversation logs from VCore Agent Chat and generates/updates playbooks in `/SecondBrain/SharedKnowledge/Playbooks/`.

Reads `all_messages.json` from `/SecondBrain/ConversationHistory/` and extracts:
- Wins and losses (positive/negative signal keywords)
- Agent activity patterns
- Channel usage patterns
- Category-specific insights (messaging, copy, pricing, retention, etc.)

No dependencies — pure Python 3.10+ standard library.

## Quick Start

```bash
cd Vcore2/pattern-extractor

# Analyze last 7 days (default)
python extractor.py

# Analyze last 30 days
python extractor.py --days 30

# Analyze a specific date
python extractor.py --date 2026-05-01

# Preview summary without writing playbooks
python extractor.py --summary
```

## Output

**Playbooks updated:** `/SecondBrain/SharedKnowledge/Playbooks/`
- `messaging.md` — updated with messaging patterns
- `copy.md` — updated with copy patterns
- `pricing.md` — updated with pricing patterns
- `retention.md` — updated with retention patterns
- `operations.md` — updated with ops patterns
- `builds.md` — updated with build patterns
- `creative.md` — updated with creative patterns
- `system.md` — updated with system patterns

**Analysis report:** `/SecondBrain/SharedKnowledge/Playbooks/analysis-report-YYYY-MM-DD.md`
- Full summary of activity, wins, friction, agent interactions

## Pattern Format

Each pattern in a playbook follows the standard format:

```markdown
### ✅ Win: Pattern name
**Confidence:** 🟢 High | **Frequency:** 12 signals

**Evidence:**
- Niklaus: "deployment went smooth, all tests passed"
- Lamar: "built and shipped in one session"

**Application:** Continue X approach. See examples for what worked.
```

## Automating Weekly Runs

Add to crontab for weekly Sunday midnight analysis:

```bash
# Open crontab
crontab -e

# Add this line (adjust path as needed):
0 0 * * 0 cd /path/to/Vcore2/pattern-extractor && python extractor.py --days 7 >> /SecondBrain/Logs/pattern-extractor.log 2>&1
```

Or run manually after the weekly backup.

## Signal Keywords

The extractor looks for these signals by category:

| Category | Win signals | Friction signals |
|----------|-------------|-----------------|
| All | done, complete, shipped, working, success | fail, broke, blocked, issue, error |
| Messaging | reply, response, open rate | no response, ghosted |
| Pricing | closed, agreed, accepted | rejected, too expensive |
| Retention | activated, returned, renewed | cancelled, churned |
| Builds | deployed, merged, fixed | bug, broken, broke |

## Options

```
--days INT       Days to analyze (default: 7)
--date DATE      Analyze specific date YYYY-MM-DD
--history PATH   Path to ConversationHistory dir
--output PATH    Output dir for playbooks
--summary        Print summary only, don't write files
--categories     Limit to specific categories
```

## How It Integrates

1. **VCore Agent Chat** exports `all_messages.json` daily to `ConversationHistory/YYYY-MM-DD/`
2. **Pattern Extractor** reads those JSON files weekly
3. **Playbooks** in `/SharedKnowledge/Playbooks/` get updated with new patterns
4. **Agents** read the playbooks for guidance in future sessions
