# PyTU Version 0.0.2
from enum import Enum
from typing import Optional, Any

class QuMode:

    class TRN(Enum):# Truncate Method
        TCPL = 0 
        SMGN = 1
    
    class RND(Enum):# Round Method
        POS_INF = 0
        NEG_INF = 1
        ZERO = 2
        INF = 3
        CONV = 4

class OfMode:

    class WRP(Enum):
        TCPL = 0
    
    class SAT(Enum):
        TCPL = 0
        SMGN = 1
        ZERO = 2


class QuType:
    DWT: int
    FRAC: int
    IF_SIGNED: bool
    
    def __init__(self, DWT: int, FRAC: int, IF_SIGNED: bool) -> None:
        self.DWT = DWT
        self.FRAC = FRAC
        self.IF_SIGNED = IF_SIGNED
    def MSB(self) -> int:
        return self.DWT - self.FRAC - 1
    
    def LSB(self) -> int:
        return - self.FRAC
    
    def set_dwt_frac(self, msb: int, lsb: int) -> None:
        '''
        True set function.
        '''
        self.DWT = msb - lsb + 1
        self.FRAC = - lsb

    def set(self, **kwargs: Any) -> None:
        '''
        No conflict will occur even if you write MSB=... and LSB=... in set function.
        '''
        msb_helper: Optional[Any] = kwargs.get('MSB')
        lsb_helper: Optional[Any] = kwargs.get('LSB')
        if msb_helper is not None and lsb_helper is not None:
            msb_value: int = msb_helper() if callable(msb_helper) else msb_helper # type: ignore
            lsb_value: int = lsb_helper() if callable(lsb_helper) else lsb_helper # type: ignore
            self.set_dwt_frac(msb_value, lsb_value)
        else:
            print("MSB or LSB is missing")
