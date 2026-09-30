###################################################################################################
# Module Name: DelayBudget
# Description: A delay budget tracker for automatic pipeline register insertion.
#
#   The delay budget defines a maximum combinational path cost per pipeline stage.
#   The budget unit is "8-bit adder equivalents":
#       - 1 × 8-bit adder       = cost 1
#       - 1 × 8-bit multiplier  = cost 3  (≈ 3 cascaded 8-bit adders)
#
#   When accumulated combinational cost exceeds the budget, a pipeline register
#   boundary is inferred, the cost resets, and the pipeline depth increments.
#
#   This replaces the manual `delay` variable tracking previously used in
#   C_INIT_GENERATION and similar modules.
#
# Author: Auto-generated
# Date: 2025
# Version: V0.1.0
###################################################################################################
from __future__ import annotations
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Cost constants (in 8-bit-adder equivalents)
# ---------------------------------------------------------------------------
COST_ADDER_8B = 1  # One 8-bit adder
COST_MUL_8B = 3  # One 8-bit multiplier ≈ 3 cascaded 8-bit adders
COST_MUX_2TO1 = 0  # Trivial MUX (negligible)
COST_MUX = 0.3  # Control-path MUX ≈ 0.3 × 8-bit adder (Hybrid runtime selector)


# Default budget: 1 × 8-bit multiplier worth of combinational logic
DEFAULT_BUDGET = COST_MUL_8B  # = 3 adder-equivalents


def set_default_budget(budget: int) -> None:
    global DEFAULT_BUDGET
    DEFAULT_BUDGET = budget


# ---------------------------------------------------------------------------
# Width-aware cost helpers (REFINEMENT §2.1)
# ---------------------------------------------------------------------------
import math as _math


def cost_adder(width: int) -> int:
    """N-bit ripple adder cost, scaled from 8-bit baseline.

    cost = ceil(N / 8) × COST_ADDER_8B

    Examples
    --------
    >>> cost_adder(8)   # 1
    >>> cost_adder(11)  # 2
    >>> cost_adder(12)  # 2
    """
    return _math.ceil(width / 8) * COST_ADDER_8B


def cost_mul(width_a: int, width_b: int | None = None) -> int:
    """Multiplier cost, proportional to area ∝ wa × wb.

    cost = ceil(wa / 8) × ceil(wb / 8) × COST_MUL_8B

    If *width_b* is ``None``, a square multiplier (wa == wb) is assumed.

    Examples
    --------
    >>> cost_mul(8)       # 3  (8×8)
    >>> cost_mul(12, 8)   # 6  (12×8)
    >>> cost_mul(12)      # 12 (12×12)
    """
    if width_b is None:
        width_b = width_a
    return _math.ceil(width_a / 8) * _math.ceil(width_b / 8) * COST_MUL_8B


@dataclass
class DelayBudget:
    """Track combinational delay and automatically determine pipeline boundaries.

    Usage
    -----
    >>> budget = DelayBudget(max_comb_cost=3)
    >>> budget.add_comb(COST_ADDER_8B)   # cost=1, no overflow
    >>> budget.add_comb(COST_ADDER_8B)   # cost=2, no overflow
    >>> budget.add_comb(COST_ADDER_8B)   # cost=3, no overflow (exact budget)
    >>> budget.add_comb(COST_ADDER_8B)   # cost would be 4 → auto-insert register
    >>> budget.pipeline_depth            # == 1 (one register inserted)

    The caller can also **force** a pipeline register with ``add_register()``
    (e.g. after a multiplier that itself is pipelined with N_CLK > 0).

    Attributes
    ----------
    max_comb_cost : int
        Maximum combinational cost allowed in a single pipeline stage.
    pipeline_depth : int
        Total number of pipeline register stages inserted so far.
    current_comb_cost : int
        Accumulated combinational cost in the *current* (uncommitted) stage.
    """

    max_comb_cost: int = DEFAULT_BUDGET
    pipeline_depth: int = field(default=0, init=False)
    current_comb_cost: int = field(default=0, init=False)
    _history: list[dict] = field(default_factory=list, init=False, repr=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_comb(self, cost: int | float, *, tag: str = "") -> int:
        """Add combinational logic cost.  If the accumulated cost would exceed
        the budget, a pipeline register boundary is inserted *before* this
        operation, the cost resets, and then the new cost is applied.

        Parameters
        ----------
        cost : int | float
            Cost of the combinational operation in adder-equivalents.
        tag : str, optional
            Human-readable label for debugging / logging.

        Returns
        -------
        int
            Number of pipeline registers that were automatically inserted
            (0 or 1).
        """
        if cost < 0:
            raise ValueError(f"cost must be non-negative, got {cost}")

        inserted = 0
        if (
            self.current_comb_cost + cost > self.max_comb_cost
            and self.current_comb_cost > 0
        ):
            # Budget exceeded → insert a register boundary
            self._commit_stage(reason=f"auto-before-{tag}" if tag else "auto")
            inserted = 1

        self.current_comb_cost += cost
        self._history.append(
            {
                "action": "comb",
                "cost": cost,
                "tag": tag,
                "comb_after": self.current_comb_cost,
                "depth_after": self.pipeline_depth,
                "auto_inserted": inserted,
            }
        )
        return inserted

    def add_register(self, n_clk: int = 1, *, tag: str = "") -> None:
        """Explicitly add *n_clk* pipeline register stages (e.g. for a
        pipelined multiplier with ``N_CLK=2``).  Resets the combinational
        cost accumulator.

        Parameters
        ----------
        n_clk : int
            Number of explicit pipeline registers to insert.
        tag : str, optional
            Human-readable label.
        """
        if n_clk < 0:
            raise ValueError(f"n_clk must be non-negative, got {n_clk}")
        if n_clk == 0:
            return  # nothing to do
        self.current_comb_cost = 0
        self.pipeline_depth += n_clk
        self._history.append(
            {
                "action": "register",
                "n_clk": n_clk,
                "tag": tag,
                "comb_after": 0,
                "depth_after": self.pipeline_depth,
            }
        )

    def need_register_before(self, cost: int) -> bool:
        """Check whether adding *cost* would exceed the budget (without
        actually modifying state).  Useful when the caller wants to insert
        a ``ModuleDelay`` manually.
        """
        return (
            self.current_comb_cost + cost > self.max_comb_cost
            and self.current_comb_cost > 0
        )

    def flush(self, *, tag: str = "") -> int:
        """Force a register boundary if any combinational cost is pending.
        Returns the number of registers inserted (0 or 1).
        """
        if self.current_comb_cost > 0:
            self._commit_stage(reason=tag or "flush")
            return 1
        return 0

    @property
    def total_delay(self) -> int:
        """Alias for ``pipeline_depth`` — total clock-cycle latency."""
        return self.pipeline_depth

    def delay_of(self, signal: str = "") -> int:
        """Return the current pipeline depth (for use in alignment delays)."""
        return self.pipeline_depth

    def summary(self) -> str:
        """Return a human-readable summary of the delay budget history."""
        lines = [f"DelayBudget(max_comb_cost={self.max_comb_cost})"]
        for entry in self._history:
            lines.append(f"  {entry}")
        lines.append(
            f"  => pipeline_depth={self.pipeline_depth}, "
            f"current_comb_cost={self.current_comb_cost}"
        )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _commit_stage(self, reason: str = "") -> None:
        """Insert one pipeline register and reset combinational cost."""
        self.pipeline_depth += 1
        self.current_comb_cost = 0
        self._history.append(
            {
                "action": "auto_register",
                "reason": reason,
                "depth_after": self.pipeline_depth,
            }
        )
