"""Infer only supported rolling windows when no explicit data scope was selected."""
import re


def inferred_range(prompt):
    patterns = {
        '-15m': r'\b(?:last|past)\s+(?:15\s*(?:minutes?|mins?|m)|quarter(?:\s+of\s+an?)?\s+hour)\b',
        '-1h': r'\b(?:last|past)\s+(?:(?:one|1)\s*)?(?:hour|hr)\b',
        '-24h': r'\b(?:last|past)\s+(?:24\s*(?:hours?|hrs?|h)|(?:one\s+)?day)\b',
        '-7d': r'\b(?:last|past)\s+(?:7\s*days?|(?:one\s+)?week)\b',
    }
    matches = [window for window, pattern in patterns.items() if re.search(pattern,prompt,re.I)]
    return matches[0] if len(matches) == 1 else None
