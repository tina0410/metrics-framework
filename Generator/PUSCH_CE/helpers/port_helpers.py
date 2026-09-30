###################################################################################################
# Module Name: port_helpers
# Description: Pure Python helper functions for building PORTS dictionaries
#   used in PyTV module instantiation. Eliminates repetitive boilerplate
#   for clock/reset port injection.
#
# Author: Auto-generated (refactoring)
# Date: 2026.3.15
# Version: V0.1.0
###################################################################################################
from typing import Dict, Optional


def delay_ports(
    i_data: str,
    o_data: str,
    clk: str = 'clk',
    rst_n: str = 'rst_n',
    if_rst_n: bool = True,
    n_clk: int = 1,
) -> Dict[str, str]:
    """Build PORTS dict for ModuleDelay instantiation.

    Adds ``i_clk`` when ``n_clk > 0`` and ``i_rst_n`` when ``if_rst_n``
    is True (matching PyTV conditional port convention from spec §0).

    Parameters
    ----------
    i_data : str
        Input data signal name.
    o_data : str
        Output data signal name.
    clk : str
        Clock signal name (default ``'clk'``).
    rst_n : str
        Active-low reset signal name (default ``'rst_n'``).
    if_rst_n : bool
        Whether the delay register uses asynchronous reset.
    n_clk : int
        Number of pipeline stages.  When 0, no clock port is added.

    Returns
    -------
    dict
        PORTS dictionary ready for ``ModuleDelay(..., PORTS=result)``.
    """
    ports: Dict[str, str] = {'i_data': i_data, 'o_data': o_data}
    if n_clk > 0:
        ports['i_clk'] = clk
        if if_rst_n:
            ports['i_rst_n'] = rst_n
    return ports


def arith_ports(
    i_data_1: str,
    i_data_2: str,
    o_data: str,
    clk: str = 'clk',
    rst_n: str = 'rst_n',
    if_rst_n: bool = False,
    n_clk: int = 0,
) -> Dict[str, str]:
    """Build PORTS dict for ModuleAdd / ModuleSub / ModuleMul instantiation.

    Parameters
    ----------
    i_data_1, i_data_2 : str
        Input operand signal names.
    o_data : str
        Output result signal name.
    clk : str
        Clock signal name (default ``'clk'``).
    rst_n : str
        Active-low reset signal name (default ``'rst_n'``).
    if_rst_n : bool
        Whether pipeline registers use asynchronous reset.
    n_clk : int
        Number of pipeline stages.  When 0, no clock port is added.

    Returns
    -------
    dict
        PORTS dictionary ready for ``ModuleAdd/Sub/Mul(..., PORTS=result)``.
    """
    ports: Dict[str, str] = {
        'i_data_1': i_data_1,
        'i_data_2': i_data_2,
        'o_data': o_data,
    }
    if n_clk > 0:
        ports['i_clk'] = clk
        if if_rst_n:
            ports['i_rst_n'] = rst_n
    return ports


def fxmatch_ports(
    i_data: str,
    o_data: str,
    clk: str = 'clk',
    rst_n: str = 'rst_n',
    if_rst_n: bool = False,
    n_clk: int = 0,
) -> Dict[str, str]:
    """Build PORTS dict for ModuleFxMatch instantiation.

    Parameters
    ----------
    i_data : str
        Input data signal name.
    o_data : str
        Output data signal name.
    clk : str
        Clock signal name (default ``'clk'``).
    rst_n : str
        Active-low reset signal name (default ``'rst_n'``).
    if_rst_n : bool
        Whether pipeline registers use asynchronous reset.
    n_clk : int
        Number of pipeline stages.  When 0, no clock port is added.

    Returns
    -------
    dict
        PORTS dictionary ready for ``ModuleFxMatch(..., PORTS=result)``.
    """
    ports: Dict[str, str] = {'i_data': i_data, 'o_data': o_data}
    if n_clk > 0:
        ports['i_clk'] = clk
        if if_rst_n:
            ports['i_rst_n'] = rst_n
    return ports


def seq_ports(
    base: Dict[str, str],
    clk: str = 'clk',
    rst_n: str = 'rst_n',
    if_rst_n: bool = True,
    n_clk: int = 1,
) -> Dict[str, str]:
    """Append clock/reset ports to an existing PORTS dict.

    Returns a *new* dict (does not mutate ``base``).  Useful for modules
    whose data port mapping is not covered by ``delay_ports`` or
    ``arith_ports`` (e.g. ComplexMul, AdderTree).

    Parameters
    ----------
    base : dict
        Data-port mapping (e.g. ``{'i_data_1': 'a', 'i_data_2': 'b', 'o_data': 'c'}``).
    clk, rst_n, if_rst_n, n_clk : same as ``delay_ports``.

    Returns
    -------
    dict
        Copy of *base* with ``i_clk`` / ``i_rst_n`` appended when applicable.
    """
    ports = dict(base)
    if n_clk > 0:
        ports['i_clk'] = clk
        if if_rst_n:
            ports['i_rst_n'] = rst_n
    return ports
