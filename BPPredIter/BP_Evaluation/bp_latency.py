"""Shared cycle model for Polar BP latency evaluation."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CycleTerms:
    groups: int
    cycles_per_iteration: int
    decision_cycles: int

    @property
    def cycles_per_group(self) -> float:
        return self.cycles_per_iteration / self.groups


@dataclass(frozen=True)
class LatencyError:
    signed_cycles: float
    absolute_cycles: float
    percent: float | None


def cycle_terms(n: int, m: int) -> CycleTerms:
    if n <= 0 or n & (n - 1):
        raise ValueError(f"N must be a positive power of two, got N={n}")
    if m <= 0 or n % m:
        raise ValueError(f"M must be positive and divide N, got N={n}, M={m}")
    groups = n // m
    return CycleTerms(groups, 2 * groups * int(math.log2(n)) - 1, groups)


def calculate_latency(iterations: float, terms: CycleTerms) -> int:
    """Convert an iteration count to BP decoder latency in cycles."""
    return round(iterations) * terms.cycles_per_iteration + terms.decision_cycles


def iterations_from_latency(latency: float, terms: CycleTerms) -> float:
    return (latency - terms.decision_cycles) / terms.cycles_per_iteration


def latency_error(theory_latency: float, sim_latency: float) -> LatencyError:
    signed = sim_latency - theory_latency
    return LatencyError(
        signed,
        abs(signed),
        signed / theory_latency * 100 if theory_latency else None,
    )
