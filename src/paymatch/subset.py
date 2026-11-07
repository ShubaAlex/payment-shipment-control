"""Подбор набора платежей под одну сумму: «встреча посередине» (meet-in-the-middle).

Эквайринг приходит на расчётный счёт одной суммой за день, а за ней стоят карточные оплаты нескольких счетов.
Полный перебор 2^n при n≈30 — миллиард вариантов. Делим платежи пополам, считаем все суммы каждой половины
(2 · 2^15 ≈ 65 тыс.), сортируем правую и для каждой левой суммы ищем дополнение бинарным поиском."""
from bisect import bisect_left
from typing import Hashable, Iterable, List, Optional, Sequence, Tuple

Item = Tuple[Hashable, float]
MAX_ITEMS = 30


def _half_sums(part: Sequence[Item]) -> List[Tuple[float, tuple]]:
    out = [(0.0, ())]
    for key, amount in part:
        out += [(s + amount, ids + (key,)) for s, ids in out]
    return out


def subsets_in_range(items: Iterable[Item], lo: float, hi: float, limit: int = 2) -> List[List[Hashable]]:
    """Все (до limit) разные наборы id, сумма которых в [lo, hi]. Сначала наборы из меньшего числа платежей."""
    items = [it for it in items if it[1] > 0][:MAX_ITEMS]
    if not items:
        return []
    half = len(items) // 2
    left, right = _half_sums(items[:half]), sorted(_half_sums(items[half:]))
    keys = [s for s, _ in right]
    found = []
    for s, ids in left:
        j = bisect_left(keys, lo - s)
        while j < len(right) and keys[j] <= hi - s:
            combo = ids + right[j][1]
            if combo:
                found.append(combo)
            j += 1
    found.sort(key=len)
    unique, seen = [], set()
    for combo in found:
        k = frozenset(combo)
        if k not in seen:
            seen.add(k)
            unique.append(list(combo))
        if len(unique) >= limit:
            break
    return unique


def best_subset(items: Iterable[Item], lo: float, hi: float) -> Optional[List[Hashable]]:
    """Один набор с суммой в [lo, hi] из наименьшего числа платежей или None."""
    found = subsets_in_range(items, lo, hi, limit=1)
    return found[0] if found else None
