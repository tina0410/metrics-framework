"""
Constants for the PUSCH Channel Estimation HDL generator.

These constants replace magic numbers scattered across PyTV source files.
All protocol-derived or architecture-fixed values live here.
"""

# ---------------------------------------------------------------------------
# 5G NR Protocol Constants
# ---------------------------------------------------------------------------
RE_PER_RB = 12              # Resource Elements per Resource Block
LFSR_WIDTH = 31             # Gold sequence LFSR register width (3GPP TS 38.211 §5.2.1)
C_INIT_WIDTH = LFSR_WIDTH   # c_init seed width (same as LFSR width)

# ---------------------------------------------------------------------------
# Architecture Constants
# ---------------------------------------------------------------------------
MAX_FDCDM = 4               # Maximum fdCDM averaging window size
Q_ROUNDING_BITS = 8         # Fractional bits for ×51/256 rounding in linear interpolation
