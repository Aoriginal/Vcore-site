# VCore Message Humanizer

Transforms AI-generated text into casual, human-sounding messages. No dependencies — pure Python standard library.

## Quick Start

```bash
cd Vcore2/message-humanizer

# Pipe text
echo "Certainly! Your request has been processed successfully." | python humanizer.py

# Direct argument
python humanizer.py "I would be happy to facilitate this for you."

# Show before/after diff
python humanizer.py --show-diff "Please be advised that the implementation has been completed."
```

## Levels

| Level | Effect |
|-------|--------|
| `--level 1` | Light — contractions + remove openers only |
| `--level 2` | Medium (default) — corporate vocab → casual, vary length |
| `--level 3` | Heavy — aggressive shortening + occasional typos |

## Options

```
--level {1,2,3}      Humanization intensity (default: 2)
--no-emoji           Disable emoji entirely
--no-typos           Disable natural typos (level 3 only)
--emoji-chance FLOAT Emoji probability 0.0-1.0 (default: 0.30)
--show-diff          Print before/after comparison
--seed INT           Random seed for reproducible output
```

## Examples

```bash
# Light touch
python humanizer.py --level 1 "I would like to inform you that the task is complete."
# → "I'd like to inform you that the task is complete."

# Medium (default)
python humanizer.py "Certainly! Please find the deliverables attached. Do not hesitate to reach out."
# → "here are the outputs. lmk if you need anything 👍"

# Heavy
python humanizer.py --level 3 "We need to leverage our core competencies and synergize our stakeholder engagement to drive value."
# → "we gotta play to our strengths and actually get the team working together"

# No emoji
python humanizer.py --no-emoji "The implementation has been completed successfully."
# → "it's done"

# Reproducible output (same seed = same output)
python humanizer.py --seed 42 "Your solution has been implemented."
```

## Use as a Library

```python
from humanizer import humanize, humanize_batch, HumanizerConfig

# Simple
result = humanize("Your request has been processed successfully.")
print(result)  # → "got it done 👍"

# With config
config = HumanizerConfig(
    level=3,
    emoji_chance=0.5,
    typo_chance=0.05,
    seed=42,
)
result = humanize("Certainly! I would be happy to assist you.", config)

# Batch
messages = [
    "The implementation has been completed.",
    "Please note that this is in progress.",
    "I would be happy to facilitate this for you.",
]
results = humanize_batch(messages)
for r in results:
    print(r)
```

## What It Does

**Removes:**
- `Certainly!`, `Of course!`, `Absolutely!`, `Great question!`
- `As an AI language model...`
- `I'd be happy to...`, `I'm pleased to...`
- `Please be advised that...`

**Replaces:**
- `utilize` → `use`
- `facilitate` → `help`
- `leverage` → `use`
- `synergy` → `teamwork`
- `bandwidth` → `time`
- `circle back` → `follow up`
- `going forward` → `from now on`
- `in order to` → `to`
- `prior to` → `before`
- + 60 more substitutions

**Adds:**
- Contractions (always applied)
- Casual vocabulary (`gonna`, `wanna`, `lmk`, `fyi`, `btw`)
- Contextual emoji (max one per message, 30% chance by default)
- Sentence length variation (strips filler closers)

**Emojis used:** 😂 👍 😊 ✅ 💯 🔥 and contextual ones based on message content.

## No Dependencies

Zero external packages required. Uses Python 3.8+ standard library only.
