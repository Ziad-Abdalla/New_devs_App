"""Finance: totals "slightly off by a few cents".

Latent with this seed (every per-property total is already whole cents). The
rule now: sum the exact NUMERIC values, round once at the end, half-up, to cents.
"""
from decimal import Decimal

from app.services.reservations import to_cents


def test_sum_first_then_round_once():
    rows = [Decimal("333.333"), Decimal("333.333"), Decimal("333.334")]  # res-dec-1/2/3
    assert to_cents(sum(rows)) == Decimal("1000.00")
    assert sum(to_cents(r) for r in rows) == Decimal("999.99")  # per-row rounding drifts a cent


def test_half_cent_rounds_up():
    # The old browser rule, Math.round(x * 100) / 100, gives 1.00 for 1.005 (binary floats)
    assert to_cents("1000.005") == Decimal("1000.01")
    assert to_cents("2.675") == Decimal("2.68")
    assert to_cents("2.674") == Decimal("2.67")
