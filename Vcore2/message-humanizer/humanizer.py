"""
VCore Message Humanizer
Transforms AI-generated text into casual, human-sounding messages.

Usage:
    from humanizer import humanize
    result = humanize("Your request has been processed successfully.")
    # → "got it done 👍"

CLI:
    echo "Your request has been processed." | python humanizer.py
    python humanizer.py "Your solution has been implemented."
    python humanizer.py --level 3  # 1=light, 2=medium (default), 3=heavy
"""

import random
import re
import sys
import argparse
from dataclasses import dataclass, field
from typing import Optional


# ── Configuration ──────────────────────────────────────────────────────────────

@dataclass
class HumanizerConfig:
    level: int = 2                  # 1=light, 2=medium, 3=heavy
    emoji_chance: float = 0.30      # probability of adding emoji
    typo_chance: float = 0.08       # probability of typo per word
    contraction_always: bool = True  # always apply contractions
    seed: Optional[int] = None      # for reproducible output in tests


# ── Corporate speak → Human replacements ──────────────────────────────────────

CORPORATE_REPLACEMENTS = [
    # Stiff openers
    (r'\bCertainly[,!]?\s*', ''),
    (r'\bAbsolutely[,!]?\s*', ''),
    (r'\bOf course[,!]?\s*', ''),
    (r"I'?d be happy to\s*", ''),
    (r"I'?m pleased to\s*", ''),
    (r"I'?m delighted to\s*", ''),
    (r'\bGreat question[.!]?\s*', ''),
    (r'\bExcellent question[.!]?\s*', ''),
    (r'\bThank you for (your|the) (question|inquiry|message)[.!]?\s*', ''),
    (r'\bThank you for reaching out[.!]?\s*', 'hey, '),
    (r'\bAs an AI(?: language model)?[,.]?\s*', ''),
    (r'\bAs a language model[,.]?\s*', ''),

    # Wordy phrases → short
    (r'\bin order to\b', 'to'),
    (r'\bat this (point in time|juncture)\b', 'now'),
    (r'\bprior to\b', 'before'),
    (r'\bsubsequently\b', 'then'),
    (r'\bfacilitate\b', 'help'),
    (r'\butilize\b', 'use'),
    (r'\bcommence\b', 'start'),
    (r'\binitiate\b', 'kick off'),
    (r'\bterminate\b', 'end'),
    (r'\bascertain\b', 'find out'),
    (r'\bdemonstrate\b', 'show'),
    (r'\bprovide assistance\b', 'help'),
    (r'\bin the event that\b', 'if'),
    (r'\bwith regard to\b', 'about'),
    (r'\bwith respect to\b', 'about'),
    (r'\bin terms of\b', 'for'),
    (r'\bdue to the fact that\b', 'because'),
    (r'\bfor the purpose of\b', 'to'),
    (r'\ba large number of\b', 'a lot of'),
    (r'\bin the near future\b', 'soon'),
    (r'\bgoing forward\b', 'from now on'),
    (r'\blevarage\b', 'use'),
    (r'\bsynergy\b', 'teamwork'),
    (r'\bpivot\b', 'switch'),
    (r'\bbandwidth\b', 'time'),
    (r'\bcircle back\b', 'follow up'),
    (r'\btake this offline\b', 'talk later'),
    (r'\bmoving the needle\b', 'making progress'),
    (r'\bbest practices\b', 'what works'),
    (r'\bvalue-add\b', 'helpful'),
    (r'\bproactive\b', 'ahead of things'),
    (r'\bholistic approach\b', 'the full picture'),
    (r'\bcore competenc(y|ies)\b', 'strengths'),
    (r'\baction item\b', 'to-do'),
    (r'\btouchbase\b', 'check in'),
    (r'\btouch base\b', 'check in'),
    (r'\bdive deep\b', 'dig in'),
    (r'\bdeep dive\b', 'deep look'),
    (r'\bpain point\b', 'problem'),
    (r'\bsolution\b', 'fix'),
    (r'\boptimize\b', 'improve'),
    (r'\bstakeholder(s)?\b', 'team'),
    (r'\bdeliverable(s)?\b', 'output'),
    (r'\bscalable\b', 'can grow'),
    (r'\brobust\b', 'solid'),
    (r'\bseamless\b', 'smooth'),
    (r'\btransparent\b', 'open'),
    (r'\binnovative\b', 'new'),
    (r'\bcutting.edge\b', 'latest'),
    (r'\bstate.of.the.art\b', 'up to date'),

    # Formal sentence structures
    (r'\bIt is (important|crucial|essential) (to|that)\b', "you'll want to"),
    (r'\bPlease (note|be advised) that\b', 'heads up —'),
    (r'\bI would like to\b', "i want to"),
    (r'\bI would suggest\b', "i'd suggest"),
    (r'\bIt is recommended\b', "i'd recommend"),
    (r'\bIt should be noted\b', 'btw'),
    (r'\bFor your (reference|convenience)\b', 'fyi'),
    (r'\bAs previously (mentioned|discussed|stated)\b', 'like i said'),
    (r'\bIn conclusion\b', 'so'),
    (r'\bTo summarize\b', 'tldr'),
    (r'\bFeel free to\b', 'go ahead and'),
    (r'\bDo not hesitate to\b', ''),
    (r'\bshould you (have|need|require)\b', 'if you'),
    (r'\bhave been (implemented|completed|executed)\b', r'are done'),
    (r'\bhas been (implemented|completed|executed)\b', r'is done'),
]

# ── Contractions ───────────────────────────────────────────────────────────────

CONTRACTIONS = [
    (r'\bI am\b', "I'm"),
    (r'\bI have\b', "I've"),
    (r'\bI will\b', "I'll"),
    (r'\bI would\b', "I'd"),
    (r'\byou are\b', "you're"),
    (r'\byou have\b', "you've"),
    (r'\byou will\b', "you'll"),
    (r'\byou would\b', "you'd"),
    (r'\bwe are\b', "we're"),
    (r'\bwe have\b', "we've"),
    (r'\bwe will\b', "we'll"),
    (r'\bwe would\b', "we'd"),
    (r'\bthey are\b', "they're"),
    (r'\bthey have\b', "they've"),
    (r'\bthey will\b', "they'll"),
    (r'\bdo not\b', "don't"),
    (r'\bdoes not\b', "doesn't"),
    (r'\bdid not\b', "didn't"),
    (r'\bcannot\b', "can't"),
    (r'\bwill not\b', "won't"),
    (r'\bwould not\b', "wouldn't"),
    (r'\bcould not\b', "couldn't"),
    (r'\bshould not\b', "shouldn't"),
    (r'\bis not\b', "isn't"),
    (r'\bare not\b', "aren't"),
    (r'\bwas not\b', "wasn't"),
    (r'\bwere not\b', "weren't"),
    (r'\bhave not\b', "haven't"),
    (r'\bhas not\b', "hasn't"),
    (r'\bhad not\b', "hadn't"),
    (r'\bthat is\b', "that's"),
    (r'\bthat would\b', "that'd"),
    (r'\bthat will\b', "that'll"),
    (r'\bhere is\b', "here's"),
    (r'\bthere is\b', "there's"),
    (r'\bwhat is\b', "what's"),
    (r'\bwhat are\b', "what're"),
    (r'\bwhat will\b', "what'll"),
    (r'\blet us\b', "let's"),
    (r'\bit is\b', "it's"),
    (r'\bit has\b', "it's"),
    (r'\bit will\b', "it'll"),
    (r'\bit would\b', "it'd"),
]

# ── Casual substitutions ───────────────────────────────────────────────────────

CASUAL_SUBS = [
    # Starting words
    (r'^However,\s*', 'but '),
    (r'^Furthermore,\s*', 'also '),
    (r'^Additionally,\s*', 'also '),
    (r'^Moreover,\s*', 'plus '),
    (r'^Therefore,\s*', 'so '),
    (r'^Thus,\s*', 'so '),
    (r'^Hence,\s*', 'so '),
    (r'^Consequently,\s*', 'so '),
    (r'^Subsequently,\s*', 'then '),
    (r'^Nevertheless,\s*', 'still '),
    (r'^Nonetheless,\s*', 'still '),
    (r'^Regarding\s+', 'about '),
    (r'^With that said,\s*', ''),

    # Common AI phrases
    (r'\bcertainly possible\b', 'definitely doable'),
    (r'\bhappy to help\b', 'on it'),
    (r'\blet me know if you (have|need)\b', 'lmk if you'),
    (r'\blet me know\b', 'lmk'),
    (r'\bplease let me know\b', 'lmk'),
    (r'\bI hope (this|that)\b', 'hope this'),
    (r'\bI hope you\b', 'hope you'),
    (r'\bthis should help\b', 'that should do it'),
    (r'\bthis will help\b', "this'll help"),
    (r'\bthank you for your patience\b', 'appreciate the patience'),
    (r'\bI appreciate\b', 'appreciate'),
    (r'\bplease find (the|attached)\b', 'here\'s the'),
    (r'\bgoing to\b', 'gonna'),
    (r'\bwant to\b', 'wanna'),
    (r'\bgot to\b', 'gotta'),
    (r'\bkind of\b', 'kinda'),
    (r'\bsort of\b', 'sorta'),
    (r'\ba lot\b', 'a lot'),  # keep, but context-dependent
    (r'\bok\b', 'ok'),
    (r'\bOkay\b', 'ok'),
    (r'\byeah\b', 'yeah'),
    (r'\byes\b', 'yep'),
    (r'\bno problem\b', 'no prob'),
    (r'\bof course\b', 'sure'),
    (r'\bcorrect\b', 'right'),
]

# ── Emojis by context ──────────────────────────────────────────────────────────

CONTEXT_EMOJIS = {
    'done|complete|finish|ready|ship': ['✅', '👍', '💪', '🎉'],
    'error|fail|broke|wrong|issue|bug': ['😬', '🙈', '💀', '😅'],
    'wait|soon|later|delay|hold': ['⏳', '🕐', '👀'],
    'good|great|nice|solid|awesome': ['👍', '🔥', '💯', '😊'],
    'think|idea|question|maybe|hmm': ['🤔', '💭', '🧠'],
    'money|cost|price|paid|revenue': ['💰', '💵', '📈'],
    'fast|quick|rapid|speed|now': ['⚡', '🚀', '💨'],
    'update|change|new|latest': ['🔄', '✨', '🆕'],
    'check|look|review|read': ['👀', '📋', '🔍'],
    'meeting|chat|talk|call': ['💬', '📞', '🗣️'],
}

GENERAL_EMOJIS = ['👍', '😊', '😂', '✅', '💯', '🔥']

# ── Natural typos ──────────────────────────────────────────────────────────────

COMMON_TYPOS = {
    'the': 'teh',
    'and': 'adn',
    'that': 'taht',
    'this': 'tihs',
    'have': 'ahve',
    'just': 'jsut',
    'with': 'wiht',
    'your': 'yoru',
    'their': 'thier',
    'here': 'heer',
    'you': 'yuo',
    'its': "it's",  # common swap
}

# ── Length variations ──────────────────────────────────────────────────────────

# Filler phrases to strip when shortening
LENGTH_FILLER = [
    r'In (other words|summary|brief|short),?\s*',
    r'To (put it simply|be clear|clarify),?\s*',
    r'For (clarity|context|reference),?\s*',
    r'As (mentioned|noted|discussed) (above|previously|earlier),?\s*',
    r'It is worth (noting|mentioning) that\s*',
    r'It is (important|crucial|essential) to (note|mention|remember) that\s*',
    r'First and foremost,?\s*',
    r'Last but not least,?\s*',
    r'All things considered,?\s*',
    r'At the end of the day,?\s*',
    r'When all is said and done,?\s*',
]


# ── Core transform functions ───────────────────────────────────────────────────

def apply_replacements(text: str, patterns: list, flags: int = re.IGNORECASE) -> str:
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text, flags=flags)
    return text


def clean_up(text: str) -> str:
    """Fix spacing, double punctuation, empty lines from replacements."""
    # Fix double spaces
    text = re.sub(r'  +', ' ', text)
    # Fix ", ," or ". ." artifacts
    text = re.sub(r'[,\.]\s*[,\.]', '.', text)
    # Fix sentence-start spaces
    text = re.sub(r'^\s+', '', text, flags=re.MULTILINE)
    # Fix empty lines from stripped openers
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Fix ". ," artifacts
    text = re.sub(r'\.\s*,', '.', text)
    # Strip trailing whitespace
    text = text.strip()
    return text


def lowercase_start(text: str, rng: random.Random, level: int) -> str:
    """Occasionally lowercase the first letter (casual effect)."""
    if level < 2:
        return text
    if rng.random() < 0.4 and text:
        return text[0].lower() + text[1:]
    return text


def add_typo(word: str, rng: random.Random) -> str:
    """Add a natural typo to a word."""
    lower = word.lower()
    if lower in COMMON_TYPOS:
        typo = COMMON_TYPOS[lower]
        # Preserve case of original
        if word[0].isupper():
            return typo.capitalize()
        return typo
    # Random adjacent swap
    if len(word) >= 4:
        i = rng.randint(1, len(word) - 2)
        chars = list(word)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]
        return ''.join(chars)
    return word


def maybe_add_typos(text: str, rng: random.Random, chance: float) -> str:
    """Sprinkle natural typos."""
    if chance <= 0:
        return text
    words = text.split()
    result = []
    for word in words:
        # Only apply to clean alpha words, not URLs or punctuation-heavy
        if rng.random() < chance and re.match(r'^[a-zA-Z]{4,}$', word):
            result.append(add_typo(word, rng))
        else:
            result.append(word)
    return ' '.join(result)


def get_emoji(text: str, rng: random.Random) -> str:
    """Pick a contextually appropriate emoji."""
    text_lower = text.lower()
    for pattern, emojis in CONTEXT_EMOJIS.items():
        if any(kw in text_lower for kw in pattern.split('|')):
            return rng.choice(emojis)
    return rng.choice(GENERAL_EMOJIS)


def add_emoji(text: str, rng: random.Random, chance: float) -> str:
    """Add emoji sparingly — max one per message."""
    if rng.random() > chance:
        return text
    emoji = get_emoji(text, rng)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 1:
        # Add after a middle sentence
        idx = rng.randint(0, len(sentences) - 1)
        sentences[idx] = sentences[idx].rstrip('.!?') + ' ' + emoji + sentences[idx][-1] if sentences[idx][-1] in '.!?' else sentences[idx] + ' ' + emoji
        return ' '.join(sentences)
    else:
        # Add at end
        return text.rstrip() + ' ' + emoji


def strip_filler(text: str) -> str:
    """Remove filler phrases to shorten."""
    for pattern in LENGTH_FILLER:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    return text


def vary_length(text: str, rng: random.Random, level: int) -> str:
    """Adjust message length — heavier levels cut more aggressively."""
    if level < 2:
        return text

    # Strip filler phrases
    text = strip_filler(text)

    if level >= 3:
        # Split into sentences, drop the last one if it's just a closing
        sentences = re.split(r'(?<=[.!?])\s+', text)
        closers = ['let me know', "hope this helps", "hope that helps",
                   "feel free", "please reach out", "don't hesitate",
                   "i hope", "have a great", "best regards", "cheers",
                   "looking forward", "thank you"]
        filtered = [s for s in sentences if not any(c in s.lower() for c in closers)]
        if filtered:
            text = ' '.join(filtered)

    return text.strip()


# ── Main humanize function ─────────────────────────────────────────────────────

def humanize(text: str, config: Optional[HumanizerConfig] = None) -> str:
    """
    Transform AI text into a casual, human-sounding message.

    Args:
        text:   The AI-generated text to transform.
        config: HumanizerConfig with level, emoji_chance, typo_chance, etc.

    Returns:
        Humanized text string.
    """
    if config is None:
        config = HumanizerConfig()

    rng = random.Random(config.seed)

    # 1. Strip corporate speak
    text = apply_replacements(text, CORPORATE_REPLACEMENTS)

    # 2. Apply contractions
    if config.contraction_always or config.level >= 1:
        text = apply_replacements(text, CONTRACTIONS)

    # 3. Casual vocabulary swaps
    if config.level >= 2:
        text = apply_replacements(text, CASUAL_SUBS)

    # 4. Clean up artifacts from substitutions
    text = clean_up(text)

    # 5. Vary length
    text = vary_length(text, rng, config.level)

    # 6. Lowercase start (casual)
    text = lowercase_start(text, rng, config.level)

    # 7. Natural typos (level 3 only — use sparingly)
    if config.level >= 3:
        text = maybe_add_typos(text, rng, config.typo_chance)

    # 8. Emoji (after all text transforms)
    text = add_emoji(text, rng, config.emoji_chance)

    # 9. Final cleanup
    text = clean_up(text)

    return text


# ── Batch humanizer ────────────────────────────────────────────────────────────

def humanize_batch(messages: list[str], config: Optional[HumanizerConfig] = None) -> list[str]:
    """Humanize a list of messages."""
    return [humanize(m, config) for m in messages]


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='VCore Message Humanizer — transform AI text into casual speech',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  echo "Your request has been processed." | python humanizer.py
  python humanizer.py "Certainly! I would be happy to facilitate this."
  python humanizer.py --level 1 "Please note that this has been completed."
  python humanizer.py --level 3 --no-emoji "Leverage our synergies."
  python humanizer.py --show-diff "Certainly! This has been implemented."
        """,
    )
    parser.add_argument('text', nargs='?', help='Text to humanize (or pipe via stdin)')
    parser.add_argument('--level', type=int, choices=[1, 2, 3], default=2,
                        help='1=light, 2=medium (default), 3=heavy')
    parser.add_argument('--no-emoji', action='store_true', help='Disable emoji')
    parser.add_argument('--no-typos', action='store_true', help='Disable typos')
    parser.add_argument('--emoji-chance', type=float, default=0.30,
                        help='Emoji probability 0.0-1.0 (default: 0.30)')
    parser.add_argument('--show-diff', action='store_true',
                        help='Show before/after comparison')
    parser.add_argument('--seed', type=int, help='Random seed for reproducibility')

    args = parser.parse_args()

    # Get input
    if args.text:
        original = args.text
    elif not sys.stdin.isatty():
        original = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(0)

    if not original:
        print("Error: no text provided.", file=sys.stderr)
        sys.exit(1)

    config = HumanizerConfig(
        level=args.level,
        emoji_chance=0.0 if args.no_emoji else args.emoji_chance,
        typo_chance=0.0 if args.no_typos else 0.08,
        seed=args.seed,
    )

    result = humanize(original, config)

    if args.show_diff:
        print("── ORIGINAL ──────────────────────────────")
        print(original)
        print("── HUMANIZED ─────────────────────────────")
        print(result)
        print("──────────────────────────────────────────")
    else:
        print(result)


if __name__ == '__main__':
    main()
