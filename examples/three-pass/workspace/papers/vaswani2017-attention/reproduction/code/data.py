#!/usr/bin/env python3
"""Registry-lookup toy dataset for the "Attention Is All You Need" reproduction.

Vaswani et al. 2017, section 3.2 (p.3): "An attention function can be described
as mapping a query and a set of key-value pairs to an output, where the query,
keys, values, and output are all vectors." This dataset instantiates exactly
that structure as data. Each example is a tiny 4-record registry:

    {"pairs": [["k3","v7"],["k0","v2"],["k8","v5"],["k5","v9"]], "query": "k8", "target": "v5"}

The right answer is the value paired with the queried key, so solving the task
*is* retrieval-by-content: score the query against the keys, read out the
matching record's value -- which is what eq (1) computes (phase 2 implements
the equation; this phase implements no equation, only the structure).

Properties later phases rely on (PLAN.md recipe, authoritative):
  * Keys distinct and values distinct within an example, paired by a uniform
    random bijection: conditioned on everything an order/binding-blind model
    can see, the pairing is uniform, so its best accuracy is exactly 25%.
  * Records listed in random order, queried slot balanced across positions:
    position cannot leak the answer (asserted by the --check leak guard).
  * No degenerate majority target value: the constant baseline stays ~10%
    (asserted by the --check leak guard).

Determinism: the whole stream comes from a single random.Random(17), and each
line's byte rendering is pinned (render_line reproduces the schema line above
exactly). --check regenerates the stream in memory and compares the files
byte-for-byte, so a re-run can never silently produce different data.

Usage (Python 3 stdlib only; paths resolve relative to this file):
    python3 data.py            # write data/train.jsonl (2048), val.jsonl (256), test.jsonl (512)
    python3 data.py --check    # validate existing files; exit 0 iff every check passes
"""

import argparse
import json
import random
from collections import Counter
from pathlib import Path

# --- Universe and sizes (PLAN.md "Toy data recipe", authoritative) -----------

KEYS = ["k%d" % i for i in range(10)]    # 10 key symbols k0..k9
VALUES = ["v%d" % i for i in range(10)]  # 10 value symbols v0..v9
RECORDS_PER_EXAMPLE = 4

DATA_SEED = 17                            # data seed (train seed 42 belongs to phase 3)
SPLITS = (("train", 2048), ("val", 256), ("test", 512))  # one stream, split in this order

DATA_DIR = Path(__file__).resolve().parent / "data"

# --- Leak-guard bounds (phase-1 spec, acceptance check 4) --------------------

SLOT_FREQ_BOUNDS = (0.20, 0.30)    # queried record's slot index 0..3, over train
TARGET_FREQ_BOUNDS = (0.06, 0.14)  # each target value v0..v9, over train


# --- Generation --------------------------------------------------------------

def make_example(rng):
    """One registry: section 3.2's "query and a set of key-value pairs" + answer.

    Recipe steps, in order: sample 4 distinct keys; sample 4 distinct values;
    pair them by a uniform random bijection; list the records in random order;
    pick the query uniformly from the 4 keys; target = the queried key's value.
    """
    keys = rng.sample(KEYS, RECORDS_PER_EXAMPLE)      # 4 distinct keys
    values = rng.sample(VALUES, RECORDS_PER_EXAMPLE)  # 4 distinct values
    rng.shuffle(values)                    # uniform random bijection keys[i] <-> values[i]
    pairs = [[k, v] for k, v in zip(keys, values)]
    rng.shuffle(pairs)                     # record order must carry no information
    query = rng.choice([k for k, _ in pairs])          # uniform over the 4 keys
    target = next(v for k, v in pairs if k == query)   # the paired value (keys distinct)
    return {"pairs": pairs, "query": query, "target": target}


def generate_stream():
    """All 2816 examples from a single random.Random(17) stream (PLAN.md seeds)."""
    rng = random.Random(DATA_SEED)
    total = sum(size for _, size in SPLITS)
    return [make_example(rng) for _ in range(total)]


def split_stream(stream):
    """Cut the one stream into train/val/test in stream order (2048/256/512)."""
    out, start = {}, 0
    for name, size in SPLITS:
        out[name] = stream[start:start + size]
        start += size
    return out


def render_line(example):
    """Render one example exactly as the phase-1 schema line shows it.

    The byte format is pinned so --check can regenerate from seed 17 and compare
    files byte-for-byte. Symbols come from the closed k0..k9/v0..v9 alphabet, so
    this is always valid JSON (json.loads-compatible) with no escaping concerns.
    """
    pairs = ",".join('["%s","%s"]' % (k, v) for k, v in example["pairs"])
    return '{"pairs": [%s], "query": "%s", "target": "%s"}' % (
        pairs, example["query"], example["target"])


def expected_file_bytes():
    """The exact bytes each of the three files must contain (determinism oracle)."""
    splits = split_stream(generate_stream())
    return {name: "".join(render_line(ex) + "\n" for ex in splits[name]).encode("utf-8")
            for name, _ in SPLITS}


def write_files():
    """Write data/train.jsonl, val.jsonl, test.jsonl (deterministic, overwrites)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, payload in expected_file_bytes().items():
        path = DATA_DIR / (name + ".jsonl")
        path.write_bytes(payload)
        print("wrote %s (%d lines)" % (path, payload.count(b"\n")))


# --- Validation (--check) ----------------------------------------------------

def validate_example(obj):
    """Return None if one parsed example is valid, else the reason it is not."""
    if not isinstance(obj, dict) or list(obj) != ["pairs", "query", "target"]:
        return "fields are not exactly pairs, query, target (in that order)"
    pairs = obj["pairs"]
    if not (isinstance(pairs, list) and len(pairs) == RECORDS_PER_EXAMPLE):
        return "does not have exactly 4 pairs"
    if not all(isinstance(p, list) and len(p) == 2
               and all(isinstance(s, str) for s in p) for p in pairs):
        return "a record is not a [key, value] pair of strings"
    keys = [k for k, _ in pairs]
    values = [v for _, v in pairs]
    if len(set(keys)) != RECORDS_PER_EXAMPLE:
        return "keys are not distinct"
    if len(set(values)) != RECORDS_PER_EXAMPLE:
        return "values are not distinct"
    if not set(keys) <= set(KEYS):
        return "key symbol outside k0..k9"
    if not set(values) <= set(VALUES):
        return "value symbol outside v0..v9"
    if obj["query"] not in keys:
        return "query is not one of the 4 keys"
    if obj["target"] != dict(zip(keys, values))[obj["query"]]:
        return "target is not the queried key's paired value"
    return None


def check():
    """Run all acceptance checks; return 0 iff everything passes."""
    problems = []

    # Load the three files as raw bytes (byte-exactness matters below).
    raw = {}
    for name, _ in SPLITS:
        path = DATA_DIR / (name + ".jsonl")
        if path.is_file():
            raw[name] = path.read_bytes()
        else:
            problems.append("%s.jsonl: missing (run data.py with no arguments first)" % name)
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1

    # Check 2 -- per-line validity (every line of all three files).
    parsed = {}
    for name, size in SPLITS:
        lines = raw[name].decode("utf-8").splitlines()
        if len(lines) != size:
            problems.append("%s.jsonl: %d lines, expected %d" % (name, len(lines), size))
        objs = []
        for i, line in enumerate(lines, start=1):
            try:
                obj = json.loads(line)
            except ValueError as exc:
                problems.append("%s.jsonl line %d: invalid JSON (%s)" % (name, i, exc))
                continue
            reason = validate_example(obj)
            if reason:
                problems.append("%s.jsonl line %d: %s" % (name, i, reason))
            objs.append(obj)
        parsed[name] = objs
        print("validity: %s.jsonl -- %d/%d lines valid" % (name, size - sum(
            1 for p in problems if p.startswith(name + ".jsonl")), size))

    # Check 3 -- determinism: regenerate from seed 17, compare byte-for-byte.
    for name, payload in expected_file_bytes().items():
        if raw[name] == payload:
            print("determinism: %s.jsonl matches regeneration from seed %d byte-for-byte"
                  % (name, DATA_SEED))
        else:
            got, want = raw[name].splitlines(), payload.splitlines()
            diff = next((i for i, (g, w) in enumerate(zip(got, want), start=1) if g != w),
                        min(len(got), len(want)) + 1)
            problems.append("%s.jsonl: differs from seed-%d regeneration (first at line %d)"
                            % (name, DATA_SEED, diff))

    # Check 4 -- leak guards over train, printed and asserted.
    train = parsed["train"]
    n = len(train)
    slot_counts = Counter(next(i for i, (k, _) in enumerate(ex["pairs"])
                               if k == ex["query"]) for ex in train)
    target_counts = Counter(ex["target"] for ex in train)

    lo, hi = SLOT_FREQ_BOUNDS
    print("leak guard: queried-slot frequency over train (each must be in [%.2f, %.2f])"
          % (lo, hi))
    for slot in range(RECORDS_PER_EXAMPLE):
        freq = slot_counts[slot] / n
        verdict = "ok" if lo <= freq <= hi else "OUT OF BOUNDS"
        print("  slot %d: %.4f (%d/%d) %s" % (slot, freq, slot_counts[slot], n, verdict))
        if verdict != "ok":
            problems.append("slot %d frequency %.4f outside [%.2f, %.2f] -- position leaks"
                            % (slot, freq, lo, hi))

    lo, hi = TARGET_FREQ_BOUNDS
    print("leak guard: target-value frequency over train (each must be in [%.2f, %.2f])"
          % (lo, hi))
    for value in VALUES:
        freq = target_counts[value] / n
        verdict = "ok" if lo <= freq <= hi else "OUT OF BOUNDS"
        print("  %s: %.4f (%d/%d) %s" % (value, freq, target_counts[value], n, verdict))
        if verdict != "ok":
            problems.append("target %s frequency %.4f outside [%.2f, %.2f] -- degenerate class"
                            % (value, freq, lo, hi))

    if problems:
        print("--check: %d problem(s)" % len(problems))
        for p in problems:
            print("FAIL:", p)
        return 1
    print("--check: all checks passed (validity, determinism, leak guards)")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate or validate the registry-lookup toy dataset "
                    "(Attention Is All You Need reproduction, phase 1).")
    parser.add_argument("--check", action="store_true",
                        help="validate existing data files instead of writing; "
                             "exit nonzero on any failure")
    args = parser.parse_args()
    if args.check:
        raise SystemExit(check())
    write_files()


if __name__ == "__main__":
    main()
