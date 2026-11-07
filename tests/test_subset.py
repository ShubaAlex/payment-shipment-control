import random

from paymatch.subset import best_subset, subsets_in_range


def test_finds_exact_combination():
    items = [("a", 12300), ("b", 17800), ("c", 24500), ("d", 9900)]
    assert sorted(best_subset(items, 54595, 54605)) == ["a", "b", "c"]


def test_prefers_fewer_payments():
    items = [("a", 10000), ("b", 20000), ("c", 30000)]
    assert best_subset(items, 29995, 30005) == ["c"]


def test_reports_all_variants_for_ambiguity():
    items = [("a", 10000), ("b", 20000), ("c", 30000)]
    variants = subsets_in_range(items, 29995, 30005, limit=5)
    assert sorted(map(sorted, variants)) == [["a", "b"], ["c"]]


def test_none_when_impossible():
    assert best_subset([("a", 100), ("b", 200)], 250, 260) is None


def test_thirty_items_fast_and_correct():
    rnd = random.Random(7)
    items = [(i, rnd.randint(1000, 90000)) for i in range(30)]
    target = sum(a for i, a in items if i in (3, 11, 19, 27))
    got = best_subset(items, target, target)
    assert got is not None and sum(a for i, a in items if i in got) == target
