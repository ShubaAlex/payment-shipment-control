"""Сопоставление оплат, заявленных менеджерами, с реальными поступлениями: выписки банков и кассы магазинов.

Порядок для каждой заявленной оплаты:
  1. номер счёта в назначении платежа или в основании кассового ордера + сумма;
  2. сумма и дата в окне там, где указал менеджер (способ оплаты и фирма — первая гипотеза);
  3. сумма и дата в окне «везде»: другой способ, другая фирма → засчитываем с пометкой «найдено не там, где указано»;
  4. карточные оплаты — разбор дневной суммы эквайринга: какой набор оплат её составил. Если вариантов
     несколько, не угадываем, а просим проверить вручную.
Не нашлось: свежая оплата (≤ 2 рабочих дней) — «ждём», иначе — тревога."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional

from .subset import subsets_in_range

TOLERANCE = 5.0          # ₽: округления и копейки в таблицах менеджеров
DAYS_BEFORE = 3          # приход может быть раньше, чем менеджер внёс оплату в таблицу
WORKDAYS_AFTER = 3       # банк зачисляет на следующий рабочий день, эквайринг после выходных — пачкой
FRESH_WORKDAYS = 2


@dataclass
class Claim:
    """Оплата, которую менеджер записал в свою таблицу."""
    invoice: str
    manager: str
    client: str
    amount: float
    day: date
    method: str          # cash | card | qr | bank
    firm: str            # на какую фирму или в какую кассу


@dataclass
class Incoming:
    """Поступление: строка выписки банка или приход в кассе."""
    id: str
    source: str          # bank | cash
    account: str         # фирма (для банка) или касса магазина
    day: date
    amount: float
    payer: str = ""
    purpose: str = ""
    acquiring: bool = False


@dataclass
class Result:
    claim: Claim
    status: str                          # ok | elsewhere | acquiring | ambiguous | waiting | missing
    matched: List[str] = field(default_factory=list)
    note: str = ""


def add_workdays(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def workdays_between(a: date, b: date) -> int:
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def _window(c: Claim):
    return c.day - timedelta(days=DAYS_BEFORE), add_workdays(c.day, WORKDAYS_AFTER)


def _expected_source(c: Claim) -> str:
    return "cash" if c.method == "cash" else "bank"


def _where(x: Incoming) -> str:
    return x.account if x.source == "cash" else "выписка " + x.account


def match(claims: List[Claim], incoming: List[Incoming], today: date) -> List[Result]:
    used: set = set()
    results: Dict[int, Result] = {}

    def fits(c: Claim, x: Incoming) -> bool:
        lo, hi = _window(c)
        return x.id not in used and not x.acquiring and lo <= x.day <= hi and abs(x.amount - c.amount) <= TOLERANCE

    # 1. номер счёта в назначении / основании
    for n, c in enumerate(claims):
        hit = next((x for x in incoming if fits(c, x) and f"№{c.invoice}" in x.purpose.replace(" ", "")), None)
        if hit:
            used.add(hit.id)
            same = hit.source == _expected_source(c) and hit.account == c.firm
            results[n] = Result(c, "ok" if same else "elsewhere", [hit.id],
                                "номер счёта в назначении" + ("" if same else f"; найдено не там, где указано: {_where(hit)}"))

    # 2. там, где указал менеджер; 3. везде
    for strict in (True, False):
        for n, c in enumerate(claims):
            if n in results or c.method == "card":
                continue
            cands = [x for x in incoming if fits(c, x) and (not strict or (x.source == _expected_source(c) and x.account == c.firm))]
            if cands:
                hit = min(cands, key=lambda x: abs((x.day - c.day).days))
                used.add(hit.id)
                where = _where(hit)
                results[n] = Result(c, "ok" if strict else "elsewhere", [hit.id],
                                    where if strict else f"найдено не там, где указано: {where}")

    # 4. эквайринг: дневная сумма = набор карточных оплат этой фирмы за 1–3 рабочих дня до зачисления
    for x in sorted((x for x in incoming if x.acquiring), key=lambda x: x.day):
        pending = [(n, c.amount) for n, c in enumerate(claims)
                   if n not in results and c.method == "card" and c.firm == x.account
                   and x.day - timedelta(days=DAYS_BEFORE + 2) <= c.day <= x.day]
        variants = subsets_in_range(pending, x.amount - TOLERANCE, x.amount + TOLERANCE, limit=2)
        if len(variants) == 1:
            used.add(x.id)
            for n in variants[0]:
                results[n] = Result(claims[n], "acquiring", [x.id], f"эквайринг {x.account} {x.day:%d.%m}: {x.amount:,.0f} ₽ из {len(variants[0])} оплат".replace(",", " "))
        elif len(variants) > 1:
            text = " или ".join(" + ".join("№" + claims[n].invoice for n in v) for v in variants)
            for n in {n for v in variants for n in v}:
                results[n] = Result(claims[n], "ambiguous", [x.id],
                                    f"эквайринг {x.account} {x.day:%d.%m} на {x.amount:,.0f} ₽ — это {text}; проверьте вручную".replace(",", " "))

    # не нашлось
    for n, c in enumerate(claims):
        if n not in results:
            fresh = workdays_between(c.day, today) <= FRESH_WORKDAYS
            results[n] = Result(c, "waiting" if fresh else "missing", [], "свежая оплата, ждём выписку" if fresh else "поступление не найдено")
    return [results[n] for n in range(len(claims))]
