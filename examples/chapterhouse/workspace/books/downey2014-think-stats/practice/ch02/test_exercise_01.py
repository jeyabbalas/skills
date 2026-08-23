"""Tests for exercise_01 (Mode / AllModes). Run: python3 test_exercise_01.py  (or pytest)."""


def test_mode_birthwgt_lb_counts():
    from exercise_01 import Mode
    # the book's published birthwgt_lb counts for 6, 7, 8 pounds (ch.1, p.11)
    assert Mode({6: 2223, 7: 3049, 8: 1889}) == 7


def test_mode_single_value():
    from exercise_01 import Mode
    assert Mode({39: 4744}) == 39


def test_mode_tie_returns_one_of_the_tied():
    from exercise_01 import Mode
    assert Mode({1: 5, 2: 5, 3: 1}) in (1, 2)


def test_mode_empty_raises():
    from exercise_01 import Mode
    try:
        Mode({})
    except ValueError:
        return
    raise AssertionError("Mode({}) should raise ValueError")


def test_allmodes_descending():
    from exercise_01 import AllModes
    pairs = AllModes({1: 1, 5: 1, 3: 1, 2: 2})
    assert pairs[0] == (2, 2)
    freqs = [freq for _, freq in pairs]
    assert freqs == sorted(freqs, reverse=True)


def test_allmodes_complete():
    from exercise_01 import AllModes
    hist = {1: 1, 2: 2, 3: 1, 5: 1}
    assert sorted(AllModes(hist)) == sorted(hist.items())


if __name__ == "__main__":
    import sys
    import traceback
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception:
                fails += 1
                print("FAIL", name)
                traceback.print_exc()
    sys.exit(1 if fails else 0)
