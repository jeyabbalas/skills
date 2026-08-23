"""Exercise 2.3 (Think Stats 2e, p.29): Mode and AllModes.

Contract
--------
Mode(hist) -> value
    hist is a dict-like mapping values to integer frequencies (what
    thinkstats2.Hist holds). Return the most frequent value. If several
    values tie for the highest frequency, any one of them is acceptable.
    Raise ValueError on an empty hist.

AllModes(hist) -> list of (value, freq) pairs
    All value-frequency pairs in descending order of frequency. Ties may
    appear in any order relative to each other.

Examples
--------
Mode({7: 3049, 8: 1889, 6: 2223}) == 7
AllModes({1: 1, 2: 2}) == [(2, 2), (1, 1)]

Edge cases: single-value hist; all frequencies equal; empty hist (ValueError).
"""


# --- student's solution (cbell, 2026-08-16) ---

def Mode(hist):
    if not hist:
        raise ValueError("empty hist has no mode")
    best = None
    best_freq = -1
    for value, freq in hist.items():
        if freq > best_freq:
            best = value
            best_freq = freq
    return best


def AllModes(hist):
    pairs = list(hist.items())
    pairs.sort(key=lambda pair: pair[1], reverse=True)
    return pairs
