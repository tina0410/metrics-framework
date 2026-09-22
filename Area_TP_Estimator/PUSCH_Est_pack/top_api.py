"""Semantic, validated public API for generating the PUSCH TOP RTL."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, Mapping, Optional, Sequence

from PyTU import OfMode, QuMode, QuType


class QuantKey(str, Enum):
    """The complete public numerical-width namespace."""

    Y = "Y"
    H_LS = "H_LS"
    H_FI = "H_FI"
    H_TI = "H_TI"
    FI_LMMSE_COEFF = "FI_LMMSE_COEFF"
    TI_LMMSE_COEFF = "TI_LMMSE_COEFF"


_REQUIRED_QUANT_KEYS = frozenset(QuantKey)


def _validate_qu_type(name: str, value: Any, *, structural: bool = False) -> None:
    if not isinstance(value, QuType):
        raise TypeError(f"{name} must be a QuType, got {type(value).__name__}")
    if not isinstance(value.DWT, int) or value.DWT < 1:
        raise ValueError(f"{name}.DWT must be a positive integer")
    if not isinstance(value.FRAC, int) or not 0 <= value.FRAC <= value.DWT:
        raise ValueError(f"{name}.FRAC must be in 0..DWT")
    if not isinstance(value.IF_SIGNED, bool):
        raise TypeError(f"{name}.IF_SIGNED must be bool")
    if structural and (value.FRAC != 0 or value.IF_SIGNED):
        raise ValueError(f"{name} must be an unsigned integer format")


def validate_quants(quants: Mapping[QuantKey, QuType]) -> None:
    """Require exactly the six approved quantization keys."""

    if not isinstance(quants, Mapping):
        raise TypeError("quants must be a mapping from QuantKey to QuType")
    raw_keys = set(quants)
    invalid = sorted(repr(key) for key in raw_keys if not isinstance(key, QuantKey))
    missing = sorted(key.value for key in _REQUIRED_QUANT_KEYS - raw_keys)
    extra = sorted(key.value for key in raw_keys - _REQUIRED_QUANT_KEYS if isinstance(key, QuantKey))
    if invalid or missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        if invalid:
            details.append(f"non_QuantKey={invalid}")
        raise ValueError("quants must contain exactly the approved QuantKey set: " + ", ".join(details))
    for key in QuantKey:
        _validate_qu_type(f"quants[{key.value}]", quants[key])


@dataclass(frozen=True)
class ProtocolSpec:
    """Generated protocol capability and unresolved slot-index structure.

    ``slot_index_format`` remains explicit.  It is not defaulted to four bits
    because the supported NR semantics/range have not been settled.
    """

    pusch: Mapping[str, Any]
    dmrs: Mapping[str, Any]
    antenna_ports: Sequence[int]
    slot_index_format: QuType

    def __post_init__(self) -> None:
        object.__setattr__(self, "pusch", dict(self.pusch))
        object.__setattr__(self, "dmrs", dict(self.dmrs))
        object.__setattr__(self, "antenna_ports", tuple(self.antenna_ports))
        self.validate()

    def validate(self) -> None:
        missing_pusch = {"num_RB_range", "num_symbols_range", "is_ECP"} - set(self.pusch)
        missing_dmrs = {"dmrs_Uplink", "dmrs_Type"} - set(self.dmrs)
        if missing_pusch:
            raise ValueError(f"protocol.pusch missing keys: {sorted(missing_pusch)}")
        if missing_dmrs:
            raise ValueError(f"protocol.dmrs missing keys: {sorted(missing_dmrs)}")
        for name in ("num_RB_range", "num_symbols_range"):
            bounds = self.pusch[name]
            if not isinstance(bounds, (tuple, list)) or len(bounds) != 2:
                raise ValueError(f"protocol.pusch[{name!r}] must be a two-element range")
            if not all(isinstance(item, int) for item in bounds) or bounds[0] < 1 or bounds[0] > bounds[1]:
                raise ValueError(f"protocol.pusch[{name!r}] has invalid bounds {bounds!r}")
        if self.dmrs["dmrs_Type"] not in (1, 2, "Hybrid"):
            raise ValueError("protocol.dmrs['dmrs_Type'] must be 1, 2, or 'Hybrid'")
        if not self.antenna_ports or len(set(self.antenna_ports)) != len(self.antenna_ports):
            raise ValueError("protocol.antenna_ports must be non-empty and unique")
        if not all(isinstance(port, int) and 0 <= port <= 23 for port in self.antenna_ports):
            raise ValueError("protocol.antenna_ports must contain integer port IDs in 0..23")
        _validate_qu_type("protocol.slot_index_format", self.slot_index_format, structural=True)

    def symbol_index_format(self) -> QuType:
        max_symbols = int(self.pusch["num_symbols_range"][1])
        width = max((max_symbols - 1).bit_length(), 1)
        return QuType(width, 0, False)


@dataclass(frozen=True)
class ArchitectureConfig:
    rb_parallelism: int
    fi_lmmse_parallelism: int
    freq_interp: Literal["nn", "linear", "lmmse"]
    time_interp: Literal["nn", "linear", "lmmse"]
    input_mode: Literal["A", "B"] = "A"
    switchable_ports: bool = True
    fi_re_parallelism: int = 12
    ti_re_parallelism: int = 3
    fi_lmmse_real_coeff: bool = True
    ti_lmmse_real_coeff: bool = True
    fi_lmmse_coeff_source: Literal["ROM", "SRAM"] = "ROM"
    ti_lmmse_coeff_source: Literal["ROM", "SRAM"] = "ROM"

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.rb_parallelism < 1:
            raise ValueError("architecture.rb_parallelism must be positive")
        if self.freq_interp not in ("nn", "linear", "lmmse"):
            raise ValueError(f"unsupported frequency interpolation {self.freq_interp!r}")
        if self.time_interp not in ("nn", "linear", "lmmse"):
            raise ValueError(f"unsupported time interpolation {self.time_interp!r}")
        if self.input_mode not in ("A", "B"):
            raise ValueError("architecture.input_mode must be 'A' or 'B'")
        if self.fi_re_parallelism < 1 or 12 % self.fi_re_parallelism:
            raise ValueError("architecture.fi_re_parallelism must divide 12")
        if self.ti_re_parallelism < 1 or 12 % self.ti_re_parallelism:
            raise ValueError("architecture.ti_re_parallelism must divide 12")
        if self.fi_lmmse_parallelism < self.rb_parallelism:
            raise ValueError("architecture.fi_lmmse_parallelism must be >= rb_parallelism")
        if self.fi_lmmse_parallelism % self.rb_parallelism:
            raise ValueError("architecture.fi_lmmse_parallelism must be divisible by rb_parallelism")
        if self.fi_lmmse_coeff_source not in ("ROM", "SRAM"):
            raise ValueError("architecture.fi_lmmse_coeff_source must be ROM or SRAM")
        if self.ti_lmmse_coeff_source not in ("ROM", "SRAM"):
            raise ValueError("architecture.ti_lmmse_coeff_source must be ROM or SRAM")


@dataclass(frozen=True)
class ArithmeticConfig:
    """Arithmetic behavior only; no widths belong in this object."""

    ls_quant_mode: Any = QuMode.TRN.TCPL
    ls_overflow_mode: Any = OfMode.WRP.TCPL

    def __post_init__(self) -> None:
        if not isinstance(self.ls_quant_mode, (QuMode.TRN, QuMode.RND)):
            raise TypeError("arithmetic.ls_quant_mode must be a QuMode value")
        if not isinstance(self.ls_overflow_mode, (OfMode.WRP, OfMode.SAT)):
            raise TypeError("arithmetic.ls_overflow_mode must be an OfMode value")


@dataclass(frozen=True)
class ImplementationConfig:
    """Coefficient-generation and physical-memory implementation inputs."""

    ti_lmmse_f_d_norm: float = 0.01
    ti_lmmse_w_coeffs: Optional[Sequence[Sequence[float]]] = None
    fi_lmmse_tau_rms: float = 3.0
    fi_lmmse_snr_linear: float = 100.0
    fi_lmmse_channel_model: Optional[str] = "TDL-C"
    fi_lmmse_delay_spread: float = 200e-9
    fi_lmmse_scs: float = 30e3
    sram_macro: Optional[Mapping[str, Any]] = None
    production_observation_layouts: Optional[Sequence[Mapping[str, Any]]] = None

    def __post_init__(self) -> None:
        if self.fi_lmmse_tau_rms <= 0 or self.fi_lmmse_snr_linear <= 0:
            raise ValueError("implementation FI LMMSE tau_rms and SNR must be positive")
        if self.fi_lmmse_delay_spread <= 0 or self.fi_lmmse_scs <= 0:
            raise ValueError("implementation FI delay spread and SCS must be positive")


@dataclass(frozen=True)
class ResolvedTopConfig:
    """Validated, private generator inputs resolved from the semantic API."""

    generator_kwargs: Mapping[str, Any]


def resolve_top_config(
    protocol: ProtocolSpec,
    architecture: ArchitectureConfig,
    quants: Mapping[QuantKey, QuType],
    arithmetic: ArithmeticConfig,
    implementation: ImplementationConfig,
) -> ResolvedTopConfig:
    """Resolve semantic inputs and generator-owned structural formats."""

    protocol.validate()
    architecture.validate()
    validate_quants(quants)
    symbol_index_format = protocol.symbol_index_format()
    _validate_qu_type("resolved symbol index format", symbol_index_format, structural=True)

    kwargs = {
        "pusch_params": dict(protocol.pusch),
        "puschdmrs_params": dict(protocol.dmrs),
        "LMMSE_INTERP_PARALLELISM": architecture.fi_lmmse_parallelism,
        "Y": quants[QuantKey.Y],
        "RB_PARALLELISM": architecture.rb_parallelism,
        "ANTENNA_PORTS": list(protocol.antenna_ports),
        "Qu_H_interp_t": quants[QuantKey.H_TI],
        "Qu_H_interp_f": quants[QuantKey.H_FI],
        "freq_interp_method": architecture.freq_interp,
        "time_interp_method": architecture.time_interp,
        "Qu_symbol_idx": symbol_index_format,
        "Qu_slot_idx": protocol.slot_index_format,
        "QU_H_LS": quants[QuantKey.H_LS],
        "QU_MODE_LS": arithmetic.ls_quant_mode,
        "OF_MODE_LS": arithmetic.ls_overflow_mode,
        "switchable_ports": architecture.switchable_ports,
        "INPUT_MODE": architecture.input_mode,
        "TI_RE_PARALLELISM": architecture.ti_re_parallelism,
        "TI_LMMSE_COEFF_SOURCE": architecture.ti_lmmse_coeff_source,
        "Qu_TI_LMMSE_COEFF": quants[QuantKey.TI_LMMSE_COEFF],
        "TI_LMMSE_REAL_COEFF": architecture.ti_lmmse_real_coeff,
        "TI_LMMSE_f_d_norm": implementation.ti_lmmse_f_d_norm,
        "TI_LMMSE_W_coeffs": implementation.ti_lmmse_w_coeffs,
        "Qu_FI_LMMSE_COEFF": quants[QuantKey.FI_LMMSE_COEFF],
        "FI_LMMSE_REAL_COEFF": architecture.fi_lmmse_real_coeff,
        "FI_LMMSE_tau_rms": implementation.fi_lmmse_tau_rms,
        "FI_LMMSE_snr_linear": implementation.fi_lmmse_snr_linear,
        "FI_LMMSE_COEFF_SOURCE": architecture.fi_lmmse_coeff_source,
        "FI_LMMSE_channel_model": implementation.fi_lmmse_channel_model,
        "FI_LMMSE_delay_spread": implementation.fi_lmmse_delay_spread,
        "FI_LMMSE_scs": implementation.fi_lmmse_scs,
        "FI_RE_PARALLELISM": architecture.fi_re_parallelism,
        "SRAM_MACRO_CONFIG": implementation.sram_macro,
        "production_observation_layouts": implementation.production_observation_layouts,
    }
    if len(kwargs) != 34:
        raise AssertionError(f"resolved TOP mapping must contain 34 fields, got {len(kwargs)}")
    return ResolvedTopConfig(kwargs)


def ModuleTOP(
    protocol: ProtocolSpec,
    architecture: ArchitectureConfig,
    quants: Mapping[QuantKey, QuType],
    arithmetic: ArithmeticConfig,
    implementation: ImplementationConfig,
) -> None:
    """Generate TOP through the semantic public interface."""

    # from v_top import ModuleTOP as _ModuleTOP
# 
    # _ModuleTOP(
    #     protocol=protocol,
    #     architecture=architecture,
    #     quants=quants,
    #     arithmetic=arithmetic,
    #     implementation=implementation,
    # )


__all__ = [
    "ArchitectureConfig",
    "ArithmeticConfig",
    "ImplementationConfig",
    "ModuleTOP",
    "ProtocolSpec",
    "QuantKey",
    "ResolvedTopConfig",
    "resolve_top_config",
    "validate_quants",
]
