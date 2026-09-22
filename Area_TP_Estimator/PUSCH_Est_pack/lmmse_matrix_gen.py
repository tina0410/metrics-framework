###################################################################################################
# Module Name: lmmse_matrix_gen
# Description: Pre-computation of LMMSE interpolation coefficient matrices.
#   Provides:
#     1. Frequency-domain LMMSE W matrix (sinc / TDL covariance model)
#     2. Time-domain LMMSE W matrix (Wiener / Jakes model)
#     3. Channel covariance matrix computation (frequency and time)
#     4. Complex coefficient quantisation utilities
#
#   All matrices are computed at Python elaborate-time and synthesised into
#   ROM constants in the generated Verilog.
###################################################################################################
import math
import cmath
from typing import List, Literal, Optional, Tuple

# =============================================================================
# Common Utilities
# =============================================================================

def quantise_real(val: float, frac_bits: int, total_bits: int) -> int:
    """Quantise a real float to signed fixed-point.
    
    :param val: floating-point value
    :param frac_bits: number of fractional bits
    :param total_bits: total bit-width including sign bit
    :returns: signed integer representation
    """
    scale = (1 << frac_bits)
    q = round(val * scale)
    max_val = (1 << (total_bits - 1)) - 1
    min_val = -(1 << (total_bits - 1))
    return max(min_val, min(max_val, q))


def quantise_complex(val: complex, frac_bits: int, total_bits: int) -> Tuple[int, int]:
    """Quantise a complex float to signed fixed-point (re, im) pair.

    :param val: complex floating-point value
    :param frac_bits: fractional bits per component
    :param total_bits: total bit-width per component
    :returns: (re_quantised, im_quantised)
    """
    return (quantise_real(val.real, frac_bits, total_bits),
            quantise_real(val.imag, frac_bits, total_bits))


def quantise_real_checked(val: float, frac_bits: int, total_bits: int) -> int:
    """Quantise with explicit range checking and no silent saturation.

    This intentionally preserves Python's existing ``round`` convention so
    Phase 1 changes representability handling, not coefficient rounding.
    """

    if not isinstance(frac_bits, int) or frac_bits < 0:
        raise ValueError(f"frac_bits must be a non-negative integer, got {frac_bits!r}")
    if not isinstance(total_bits, int) or total_bits <= 0:
        raise ValueError(f"total_bits must be a positive integer, got {total_bits!r}")
    if frac_bits >= total_bits:
        raise ValueError(
            f"signed format requires frac_bits < total_bits, got Q{total_bits}.{frac_bits}"
        )
    try:
        finite = math.isfinite(val)
    except TypeError as error:
        raise TypeError(f"coefficient must be a real scalar, got {val!r}") from error
    if not finite:
        raise ValueError(f"coefficient must be finite, got {val!r}")

    quantised = round(val * (1 << frac_bits))
    minimum = -(1 << (total_bits - 1))
    maximum = (1 << (total_bits - 1)) - 1
    if quantised < minimum or quantised > maximum:
        raise OverflowError(
            f"coefficient {val!r} rounds to {quantised}, outside signed "
            f"{total_bits}-bit range [{minimum}, {maximum}]"
        )
    return quantised


def quantise_complex_checked(
    val: complex,
    frac_bits: int,
    total_bits: int,
) -> Tuple[int, int]:
    """Fail-closed fixed-point emission for both complex components."""

    try:
        value = complex(val)
    except (TypeError, ValueError) as error:
        raise TypeError(f"coefficient must be complex-compatible, got {val!r}") from error
    return (
        quantise_real_checked(value.real, frac_bits, total_bits),
        quantise_real_checked(value.imag, frac_bits, total_bits),
    )


# =============================================================================
# 3GPP TDL Channel Model Delay/Power Tables (TR 38.901 Table 7.7.2-*)
# =============================================================================

# Normalised delays (ns-scale factors, multiply by 1e-9 to get seconds template)
# and powers (dB).  These are the template values; actual delays are scaled to
# achieve a target RMS delay spread.

TDL_MODELS = {
    'TDL-A': {
        'delay_ns': [0, 0.3819, 0.4025, 0.5868, 0.4610, 0.5375, 0.6708,
                     0.5750, 0.7618, 1.5375, 1.8978, 2.2242, 2.1718, 2.4942,
                     2.5119, 3.0582, 4.0810, 4.4579, 4.5695, 4.7966, 5.0066,
                     5.3043, 9.6586],
        'power_dB': [-13.4, 0, -2.2, -4, -6, -8.2, -9.9, -10.5, -7.5,
                     -15.9, -6.6, -16.7, -12.4, -15.2, -10.8, -11.3, -12.7,
                     -16.2, -18.3, -18.9, -16.6, -19.9, -29.7],
        'is_los': False,
    },
    'TDL-B': {
        'delay_ns': [0, 0.1072, 0.2155, 0.2095, 0.2870, 0.2986, 0.3752,
                     0.5055, 0.3681, 0.3697, 0.5700, 0.5283, 1.1021, 1.2756,
                     1.5474, 1.7842, 2.0169, 2.8294, 3.0219, 3.6187, 4.1067,
                     4.2790, 4.7834],
        'power_dB': [0, -2.2, -4, -3.2, -9.8, -1.2, -3.4, -5.2, -7.6,
                     -3, -8.9, -9, -4.8, -5.7, -7.5, -1.9, -7.6, -12.2,
                     -9.8, -11.4, -14.9, -9.2, -11.3],
        'is_los': False,
    },
    'TDL-C': {
        'delay_ns': [0, 0.2099, 0.2219, 0.2329, 0.2176, 0.6366, 0.6448,
                     0.6560, 0.6584, 0.7935, 0.8213, 0.9336, 1.2285, 1.3083,
                     2.1704, 2.7105, 4.2589, 4.6003, 5.4902, 5.6077, 6.3065,
                     6.6374, 7.0427, 8.6523],
        'power_dB': [-4.4, -1.2, -3.5, -5.2, -2.5, 0, -2.2, -3.9, -7.4,
                     -7.1, -10.7, -11.1, -5.1, -6.8, -8.7, -13.2, -13.9,
                     -13.9, -15.8, -17.1, -16, -15.7, -21.6, -22.8],
        'is_los': False,
    },
    'TDL-D': {
        'delay_ns': [0, 0.035, 0.612, 1.363, 1.405, 1.804, 2.596, 1.775,
                     4.042, 7.937, 9.424, 9.708, 12.525],
        'power_dB': [-0.2, -13.5, -18.8, -21, -22.8, -17.9, -20.1, -21.9,
                     -22.9, -27.8, -23.6, -24.8, -30.0],
        'is_los': True,
    },
    'TDL-E': {
        'delay_ns': [0, 0.5133, 0.5440, 0.5630, 0.5440, 0.7112, 1.9092,
                     1.9293, 1.9589, 2.6426, 3.7136, 5.4524, 12.0034, 20.6519],
        'power_dB': [-0.03, -22.03, -15.8, -18.1, -19.8, -22.9, -22.4,
                     -18.6, -20.8, -22.6, -22.3, -25.6, -20.2, -29.8],
        'is_los': True,
    },
}


def _load_tdl_model(model: str, delay_spread: float) -> Tuple[List[float], List[float], bool]:
    """
    Load TDL channel model parameters and scale delays to target RMS delay spread.
    
    :param model: model name ('TDL-A' through 'TDL-E')
    :param delay_spread: target RMS delay spread in seconds
    :returns: (delays_sec, powers_linear, is_los)
    """
    if model not in TDL_MODELS:
        raise ValueError(f"Unknown TDL model: {model}. Available: {list(TDL_MODELS.keys())}")
    
    m = TDL_MODELS[model]
    delay_ns = m['delay_ns']
    power_dB = m['power_dB']
    is_los = m['is_los']
    
    # Convert to seconds and linear power
    delays_sec = [d * 1e-9 for d in delay_ns]
    powers = [10 ** (p / 10) for p in power_dB]
    total_power = sum(powers)
    powers = [p / total_power for p in powers]
    
    # Compute current RMS delay spread
    tau_mean = sum(p * d for p, d in zip(powers, delays_sec))
    tau_rms_current = math.sqrt(sum(p * (d - tau_mean) ** 2 for p, d in zip(powers, delays_sec)))
    
    # Scale to target delay spread
    if tau_rms_current > 1e-15:
        scale = delay_spread / tau_rms_current
    else:
        scale = 1.0
    delays_sec = [d * scale for d in delays_sec]
    
    return delays_sec, powers, is_los


# =============================================================================
# Channel Covariance Matrix Computation
# =============================================================================

def compute_freq_covariance(
    K: int,
    model: Literal['sinc', 'TDL-A', 'TDL-B', 'TDL-C', 'TDL-D', 'TDL-E'] = 'sinc',
    scs: float = 15e3,
    delay_spread: float = 30e-9,
    norm_delay_spread: Optional[float] = None,
) -> List[List[complex]]:
    """
    Compute frequency-domain channel covariance matrix R_freq [K × K].
    
    For 'sinc' model:
        R_freq[u,v] = sinc(norm_delay_spread × (u - v))
        where norm_delay_spread = scs × delay_spread (or provided directly)
    
    For TDL models:
        R_freq[u,v] = Σ_l P_l × exp(-j2π τ_l Δf (u-v))
    
    :param K: number of subcarriers (matrix size)
    :param model: channel model ('sinc' or TDL variant)
    :param scs: subcarrier spacing in Hz (default 15 kHz)
    :param delay_spread: RMS delay spread in seconds (for TDL models)
    :param norm_delay_spread: normalised delay spread for sinc model (overrides scs×delay_spread)
    :returns: R_freq [K×K] complex matrix
    """
    if model == 'sinc':
        nds = norm_delay_spread if norm_delay_spread is not None else (scs * delay_spread)
        R = [[complex(_sinc(nds * (u - v)), 0.0) for v in range(K)] for u in range(K)]
        return R
    else:
        delays, powers, _ = _load_tdl_model(model, delay_spread)
        # R_freq[u,v] = Σ_l P_l × exp(-j2π τ_l Δf (u-v))
        R = []
        for u in range(K):
            row = []
            for v in range(K):
                delta = u - v
                val = complex(0.0, 0.0)
                for l in range(len(delays)):
                    phase = -2.0 * math.pi * delays[l] * scs * delta
                    val += powers[l] * cmath.exp(1j * phase)
                row.append(val)
            R.append(row)
        return R


def compute_time_covariance(
    N: int,
    model: Literal['sinc', 'TDL-A', 'TDL-B', 'TDL-C', 'TDL-D', 'TDL-E'],
    speed: float,
    carrier_freq: float,
    ofdm_symbol_duration: float,
    delay_spread: float,
    los_angle_of_arrival: float = math.pi / 4,
) -> List[List[complex]]:
    """
    Compute time-domain channel covariance matrix R_time [N × N].
    
    Uses Clarke-Jakes model:
      NLoS: R_time[m,n] = J_0(2π f_d Δt(m-n)) × total_power
      LoS:  R_time[m,n] = P_NLoS × J_0(...) + P_LoS × exp(j2π f_d Δt cos(α))
    
    :param N: number of OFDM symbols (matrix size)
    :param model: channel model
    :param speed: UE speed in m/s
    :param carrier_freq: carrier frequency in Hz
    :param ofdm_symbol_duration: OFDM symbol duration in seconds
    :param delay_spread: RMS delay spread in seconds (for LoS power split)
    :param los_angle_of_arrival: LoS angle of arrival in radians
    :returns: R_time [N×N] complex matrix
    """
    c = 299792458.0  # speed of light, m/s
    f_d = speed * carrier_freq / c  # max Doppler frequency
    
    is_los = False
    los_power = 0.0
    nlos_power = 1.0
    
    if model != 'sinc':
        _, powers, is_los = _load_tdl_model(model, delay_spread)
        total_power = sum(powers)
        if is_los:
            los_power = powers[0]
            nlos_power = sum(powers[1:])
        else:
            nlos_power = total_power
    
    R = []
    for m in range(N):
        row = []
        for n in range(N):
            dt = (m - n) * ofdm_symbol_duration
            doppler_arg = 2.0 * math.pi * f_d * dt
            
            # NLoS component: J_0(2π f_d Δt)
            j0_val = _bessel_j0(doppler_arg)
            
            if is_los:
                # LoS: P_NLoS × J_0(...) + P_LoS × exp(j 2π f_d Δt cos(α))
                val = nlos_power * j0_val + los_power * cmath.exp(1j * doppler_arg * math.cos(los_angle_of_arrival))
            else:
                val = complex(nlos_power * j0_val, 0.0)
            
            row.append(val)
        R.append(row)
    return R


# =============================================================================
# Internal math helpers
# =============================================================================

def _sinc(x: float) -> float:
    """sinc(x) = sin(πx)/(πx), sinc(0) = 1."""
    if abs(x) < 1e-12:
        return 1.0
    return math.sin(math.pi * x) / (math.pi * x)


def _bessel_j0(x: float) -> float:
    """J_0(x) — zero-order Bessel function of the first kind (series expansion)."""
    if abs(x) < 1e-12:
        return 1.0
    s = 0.0
    for k in range(20):
        term = ((-1) ** k) * ((x / 2) ** (2 * k)) / (math.factorial(k) ** 2)
        s += term
    return s


def _mat_mul(A, B, M, N, K):
    """Matrix multiply A[M×N] × B[N×K] → C[M×K] for complex lists-of-lists."""
    C = []
    for i in range(M):
        row = []
        for j in range(K):
            val = sum(A[i][m] * B[m][j] for m in range(N))
            row.append(val)
        C.append(row)
    return C


def _mat_conj_transpose(A, M, N):
    """Hermitian transpose of A[M×N] → A^H[N×M]."""
    return [[A[i][j].conjugate() for i in range(M)] for j in range(N)]


def _diag(A, N):
    """Extract diagonal of N×N matrix."""
    return [A[i][i] for i in range(N)]


# =============================================================================
# Frequency-Domain LMMSE: Optional Sinc (Uniform PDP) Model
# =============================================================================

def _sinc_autocorrelation(delta_k: float, tau_rms_subcarriers: float) -> complex:
    """
    Frequency-domain autocorrelation under uniform PDP (power delay profile).
    
    R_ff(Δk) = sinc(Δk × τ_rms / N_fft)
    
    For a uniform PDP with delay spread τ_rms subcarriers (normalised to
    subcarrier spacing), the frequency-domain correlation is a sinc function.
    
    :param delta_k: subcarrier index difference
    :param tau_rms_subcarriers: RMS delay spread in subcarrier spacings
    :returns: complex correlation value (real for sinc model)
    """
    return complex(_sinc(delta_k * tau_rms_subcarriers), 0.0)


def compute_freq_lmmse_W(
    pilot_re_positions: List[int],
    output_re_positions: List[int],
    LMMSE_P: int,
    tau_rms: float = 3.0,
    snr_linear: float = 100.0,
    R_freq: Optional[List[List[complex]]] = None,
    is_final_stage: bool = False,
) -> List[List[complex]]:
    """
    Compute frequency-domain LMMSE interpolation matrix W.
    
    W = R_cross × (R_pilot + σ² I)^{-1}
    
    When ``R_freq`` is provided, covariance matrices are extracted from it.
    Otherwise the sinc model with ``tau_rms`` is used.
    
    When ``is_final_stage`` is False (default — freq is NOT the last interpolation
    stage), per-subcarrier scaling factors are computed and **absorbed into W**:
        scaling[k] = 2 × R_diag[k] / (R_diag[k] - Σ_n_1[k] + Σ̂_n_1[k])
        W_scaled[k,:] = scaling[k] × W[k,:]
    
    :param pilot_re_positions: pilot RE indices within one RB
    :param output_re_positions: output RE indices within one RB
    :param LMMSE_P: number of RBs in interpolation window
    :param tau_rms: RMS delay spread in subcarrier spacings (sinc model)
    :param snr_linear: linear SNR for regularisation
    :param R_freq: optional [K×K] frequency covariance matrix (overrides sinc model)
    :param is_final_stage: if True, skip scaling factor computation
    :returns: W matrix [N_output × N_pilots], list of lists of complex
    """
    # Expand pilot and output positions across LMMSE_P RBs
    pilot_abs = [rb * 12 + re for rb in range(LMMSE_P) for re in pilot_re_positions]
    output_abs = [rb * 12 + re for rb in range(LMMSE_P) for re in output_re_positions]
    
    N_pilots = len(pilot_abs)
    N_output = len(output_abs)
    K_total = LMMSE_P * 12  # total subcarriers in window
    
    noise_var = 1.0 / snr_linear
    
    if R_freq is not None:
        # Extract sub-matrices from provided R_freq
        # R_freq is [K_total × K_total] or larger; we index into it
        R_pilot = [[R_freq[pilot_abs[i]][pilot_abs[j]] + (noise_var if i == j else 0.0)
                     for j in range(N_pilots)] for i in range(N_pilots)]
        R_cross = [[R_freq[output_abs[k]][pilot_abs[j]]
                     for j in range(N_pilots)] for k in range(N_output)]
    else:
        # Optional sinc covariance model
        R_pilot = [[_sinc_autocorrelation(pilot_abs[i] - pilot_abs[j], tau_rms)
                     + (noise_var if i == j else 0.0)
                     for j in range(N_pilots)] for i in range(N_pilots)]
        R_cross = [[_sinc_autocorrelation(output_abs[k] - pilot_abs[j], tau_rms)
                     for j in range(N_pilots)] for k in range(N_output)]
    
    # Invert R_pilot
    R_pilot_inv = _invert_complex_matrix(R_pilot, N_pilots)
    
    # W = R_cross × R_pilot_inv  [N_output × N_pilots]
    W = _mat_mul(R_cross, R_pilot_inv, N_output, N_pilots, N_pilots)
    
    # ---- Scaling factor computation (freq-first, not final stage) ----
    if not is_final_stage:
        # Build full R_freq for the window if not provided
        if R_freq is not None:
            R_full = [[R_freq[output_abs[k1]][output_abs[k2]]
                        for k2 in range(N_output)] for k1 in range(N_output)]
            R_pilot_full = [[R_freq[pilot_abs[j]][output_abs[k]]
                              for k in range(N_output)] for j in range(N_pilots)]
        else:
            R_full = [[_sinc_autocorrelation(output_abs[k1] - output_abs[k2], tau_rms)
                        for k2 in range(N_output)] for k1 in range(N_output)]
            R_pilot_full = [[_sinc_autocorrelation(pilot_abs[j] - output_abs[k], tau_rms)
                              for k in range(N_output)] for j in range(N_pilots)]
        
        R_diag = _diag(R_full, N_output)
        
        # Σ_n_1 = diag(R_full - W × R_pilot_full)
        WR = _mat_mul(W, R_pilot_full, N_output, N_pilots, N_output)
        sigma_n_1 = [R_full[k][k] - WR[k][k] for k in range(N_output)]
        
        # A_n: zero-padded version of W at non-pilot columns
        # A_n[k, output_idx] = W[k, pilot_j] if output_idx corresponds to a pilot
        # For the scaling calculation, we need:
        # Σ̂_n_1 = diag(A_n × R_full_KxK × A_n^H)
        # Since A_n = W spread into K_total columns (zero-padded), this simplifies:
        # A_n[:, pilot_abs] = W; A_n[:, non-pilot] = 0
        # Σ̂_n_1[k] = Σ_i Σ_j W[k,i] × R_full_KxK[pilot_abs[i], pilot_abs[j]] × conj(W[k,j])
        # which is diag(W × R_pp_no_noise × W^H)
        
        if R_freq is not None:
            R_pp_clean = [[R_freq[pilot_abs[i]][pilot_abs[j]]
                           for j in range(N_pilots)] for i in range(N_pilots)]
        else:
            R_pp_clean = [[_sinc_autocorrelation(pilot_abs[i] - pilot_abs[j], tau_rms)
                           for j in range(N_pilots)] for i in range(N_pilots)]
        
        W_H = _mat_conj_transpose(W, N_output, N_pilots)
        WR_pp = _mat_mul(W, R_pp_clean, N_output, N_pilots, N_pilots)
        WR_ppWH = _mat_mul(WR_pp, W_H, N_output, N_pilots, N_output)
        sigma_n_1_hat = _diag(WR_ppWH, N_output)
        
        # scaling[k] = 2 × R_diag[k] / (R_diag[k] - Σ_n_1[k] + Σ̂_n_1[k])
        for k in range(N_output):
            denom = R_diag[k].real - sigma_n_1[k].real + sigma_n_1_hat[k].real
            if abs(denom) > 1e-12:
                s = 2.0 * R_diag[k].real / denom
            else:
                s = 1.0
            # Absorb scaling into W row
            for j in range(N_pilots):
                W[k][j] *= s
    
    return W


def compute_freq_lmmse_W_from_observations(
    observations: "List[OccObservation] | Tuple[OccObservation, ...]",
    output_positions: List[int],
    K_total: int,
    tau_rms: float = 3.0,
    snr_linear: float = 100.0,
    R_freq: Optional[List[List[complex]]] = None,
    *,
    grid_start_subcarrier: int = 0,
    inter_stage_gain_policy: Literal["none"] = "none",
) -> List[List[complex]]:
    """Compute frequency LMMSE coefficients for unique averaged observations.

    Unlike :func:`compute_freq_lmmse_W`, this function does not interpret one
    coefficient column per pilot-labelled slot.  Each column corresponds to
    one :class:`~observation_model.OccObservation`, and the exact averaging
    operator is used in both channel and noise covariance calculations.

    ``snr_linear`` describes the post-DMRS-normalization, pre-averaging per-RE
    SNR. Consequently the observation-noise covariance is
    ``(1/snr_linear) A A^H``; no caller should divide the variance by an OCC
    length a second time.

    ``output_positions`` and covariance indices are local to the supplied
    ``K_total`` window. ``grid_start_subcarrier`` binds that local window to the
    observations' absolute CRB-referenced coordinates.

    The exact Wiener matrix is unscaled; inter-stage gain is not folded into
    the coefficient rows.
    """

    # Lazy import: observation_model is a research/campaign dependency
    # (architecture_selector), not part of the TOP generation path.
    from observation_model import (
        EXACT_WIENER_GAIN_POLICY,
        GridPoint,
        averaging_matrix,
        lmmse_weights_from_observations,
    )

    if inter_stage_gain_policy != EXACT_WIENER_GAIN_POLICY:
        raise ValueError(
            f"unknown inter-stage gain policy {inter_stage_gain_policy!r}"
        )

    if K_total <= 0:
        raise ValueError(f"K_total must be positive, got {K_total}")
    if grid_start_subcarrier < 0:
        raise ValueError(
            f"grid_start_subcarrier must be non-negative, got {grid_start_subcarrier}"
        )
    if snr_linear <= 0:
        raise ValueError(f"snr_linear must be positive, got {snr_linear}")
    if not observations:
        raise ValueError("observations cannot be empty")
    if any(point.symbol != observations[0].members[0].symbol
           for observation in observations for point in observation.members):
        raise ValueError("frequency LMMSE observations must belong to one effective symbol")
    if any(position < 0 or position >= K_total for position in output_positions):
        raise ValueError("output_positions contain a subcarrier outside K_total")

    grid = [
        GridPoint(
            subcarrier=grid_start_subcarrier + k,
            symbol=observations[0].members[0].symbol,
        )
        for k in range(K_total)
    ]
    operator = averaging_matrix(observations, grid)

    if R_freq is None:
        covariance = [
            [_sinc_autocorrelation(i - j, tau_rms) for j in range(K_total)]
            for i in range(K_total)
        ]
    else:
        if len(R_freq) < K_total or any(len(row) < K_total for row in R_freq[:K_total]):
            raise ValueError(f"R_freq must contain at least a {K_total}x{K_total} matrix")
        covariance = [
            [complex(R_freq[i][j]) for j in range(K_total)]
            for i in range(K_total)
        ]

    W = lmmse_weights_from_observations(
        covariance,
        operator,
        output_positions,
        pre_average_noise_variance=1.0 / snr_linear,
    )

    return W


def _invert_complex_matrix(M: List[List[complex]], n: int) -> List[List[complex]]:
    """Invert an n×n complex matrix via Gauss-Jordan elimination."""
    # Augmented matrix [M | I]
    aug = [[M[i][j] for j in range(n)] + [complex(1.0 if j == i else 0.0) for j in range(n)]
           for i in range(n)]
    
    for col in range(n):
        # Partial pivoting
        max_row = col
        for row in range(col + 1, n):
            if abs(aug[row][col]) > abs(aug[max_row][col]):
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]
        
        pivot = aug[col][col]
        if abs(pivot) < 1e-15:
            # Near-singular: return identity (fallback)
            return [[complex(1.0 if i == j else 0.0) for j in range(n)] for i in range(n)]
        
        for j in range(2 * n):
            aug[col][j] /= pivot
        
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(2 * n):
                aug[row][j] -= factor * aug[col][j]
    
    return [[aug[i][n + j] for j in range(n)] for i in range(n)]


# =============================================================================
# Time-Domain LMMSE: Wiener Filter (Jakes Model)
# =============================================================================

def _jakes_autocorrelation(delta_t: float, f_d_norm: float) -> float:
    """J0(2π f_D Δt) wrapper for _bessel_j0.
    
    :param delta_t: symbol index difference
    :param f_d_norm: normalised Doppler frequency (f_D × T_sym)
    :returns: real autocorrelation value
    """
    return _bessel_j0(2 * math.pi * f_d_norm * delta_t)


def compute_time_lmmse_W(
    pilot_positions: List[float],
    num_symbols: int,
    f_d_norm: float = 0.01,
    snr_linear: float = 100.0,
    R_time: Optional[List[List[complex]]] = None,
) -> List[List[complex]]:
    """
    Compute time-domain LMMSE (Wiener) interpolation matrix W [N_sym × N_occ].
    
    W = R_cross × (R_pilot + σ² I)^{-1}
    
    When ``R_time`` is provided, covariance sub-matrices are extracted from it.
    Otherwise the Jakes model with ``f_d_norm`` is used.
    
    This is always the final interpolation stage — no scaling factors are applied.
    
    :param pilot_positions: effective pilot symbol positions
    :param num_symbols: number of target OFDM symbols
    :param f_d_norm: normalised Doppler frequency (f_D × T_sym)
    :param snr_linear: linear SNR for regularisation
    :param R_time: optional [N_sym × N_sym] time covariance matrix
    :returns: W matrix [N_sym × N_occ], list of lists of complex
    """
    N_occ = len(pilot_positions)
    N_sym = num_symbols
    noise_var = 1.0 / snr_linear
    
    pilot_idx = [int(round(p)) for p in pilot_positions]
    
    if R_time is not None:
        R_pilot = [[R_time[pilot_idx[i]][pilot_idx[j]] + (noise_var if i == j else 0.0)
                     for j in range(N_occ)] for i in range(N_occ)]
    else:
        R_pilot = [[_jakes_autocorrelation(abs(pilot_positions[i] - pilot_positions[j]), f_d_norm)
                     + (noise_var if i == j else 0.0 + 0j)
                     for j in range(N_occ)] for i in range(N_occ)]
    
    R_pilot_inv = _invert_complex_matrix(R_pilot, N_occ)
    
    W = []
    for s in range(N_sym):
        if R_time is not None:
            R_cross_row = [R_time[s][pilot_idx[j]] for j in range(N_occ)]
        else:
            R_cross_row = [complex(_jakes_autocorrelation(abs(s - pilot_positions[j]), f_d_norm), 0.0)
                           for j in range(N_occ)]
        w_row = [sum(R_cross_row[k] * R_pilot_inv[k][j] for k in range(N_occ))
                 for j in range(N_occ)]
        W.append(w_row)
    return W


def _invert_real_matrix(M: List[List[float]], n: int) -> List[List[float]]:
    """Invert an n×n real matrix via Gauss-Jordan elimination."""
    aug = [[M[i][j] for j in range(n)] + [1.0 if j == i else 0.0 for j in range(n)]
           for i in range(n)]
    
    for col in range(n):
        max_row = col
        for row in range(col + 1, n):
            if abs(aug[row][col]) > abs(aug[max_row][col]):
                max_row = row
        aug[col], aug[max_row] = aug[max_row], aug[col]
        
        pivot = aug[col][col]
        if abs(pivot) < 1e-15:
            return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        for j in range(2 * n):
            aug[col][j] /= pivot
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            for j in range(2 * n):
                aug[row][j] -= factor * aug[col][j]
    
    return [[aug[i][n + j] for j in range(n)] for i in range(n)]


# =============================================================================
# Pilot Position Resolution (shared with v_core_time_lmmse_interp.py)
# =============================================================================

def get_pilot_symbol_positions(
    dmrs_typeA_pos: int,
    is_double_dmrs: bool,
    n_additional_dmrs: int,
    pusch_symbol_length: int,
) -> List[float]:
    """
    Resolve effective pilot symbol positions from DMRS configuration.
    
    For double-symbol DMRS, the effective position is the midpoint
    of the two symbols (e.g. l0=2 → effective position 2.5).
    
    :param dmrs_typeA_pos: front-loaded DMRS position (2 or 3)
    :param is_double_dmrs: True for double-symbol DMRS
    :param n_additional_dmrs: number of additional DMRS occasions
    :param pusch_symbol_length: total OFDM symbols in slot
    :returns: list of effective pilot positions
    """
    # Import here to avoid circular dependency at module level
    from v_pilot_symbol_detection import DMRS_POSITION_MAP
    
    symbol_type = 'double' if is_double_dmrs else 'single'
    key = ('A', symbol_type, n_additional_dmrs)
    entries = DMRS_POSITION_MAP.get(key, [])
    
    pos_raw = [0]
    for dur_range, pos_list in entries:
        if pusch_symbol_length in dur_range:
            pos_raw = pos_list
            break
    
    l0 = dmrs_typeA_pos
    positions = [l0 if p == 0 else p for p in pos_raw]
    
    if is_double_dmrs:
        eff_pos = [p + 0.5 for p in positions]
    else:
        eff_pos = [float(p) for p in positions]
    
    return eff_pos
