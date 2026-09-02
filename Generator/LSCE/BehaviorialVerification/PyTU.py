# PyTU Version 0.0.4
from enum import Enum

class QuMode:

    class TRN(Enum):# Truncate Method
        TCPL = 0 
        SMGN = 1
        
        def cppType(self):
            if self == QuMode.TRN.TCPL:
                return "TRN::TCPL"
            elif self == QuMode.TRN.SMGN:
                return "TRN::SMGN"
            else:
                raise ValueError("Invalid TRN value")
            pass
        
        def __eq__(self, other):
            return str(self) == str(other)  
    
    class RND(Enum):# Round Method
        POS_INF = 0
        NEG_INF = 1
        ZERO = 2
        INF = 3
        CONV = 4
    
        def cppType(self):
            if self == QuMode.RND.POS_INF:
                return "RND::POS_INF"
            elif self == QuMode.RND.NEG_INF:
                return "RND::NEG_INF"
            elif self == QuMode.RND.ZERO:
                return "RND::ZERO"
            elif self == QuMode.RND.INF:
                return "RND::INF"
            elif self == QuMode.RND.CONV:
                return "RND::CONV"
            else:
                raise ValueError("Invalid RND value")
            pass
        
        def __eq__(self, other):
            return str(self) == str(other)

    def __eq__(self, other):
        return str(self) == str(other)

class OfMode:

    class WRP(Enum):
        TCPL = 0
        
        def cppType(self):
            if self == OfMode.WRP.TCPL:
                return "WRP::TCPL"
            else:
                raise ValueError("Invalid WRP value")
            pass
        def __eq__(self, other):
            return str(self) == str(other)
    
    class SAT(Enum):
        TCPL = 0
        SMGN = 1
        ZERO = 2
        def __eq__(self, other):
            return str(self) == str(other)
            
        def cppType(self):
            if self == OfMode.SAT.TCPL:
                return "SAT::TCPL"
            elif self == OfMode.SAT.SMGN:
                return "SAT::SMGN"
            elif self == OfMode.SAT.ZERO:
                return "SAT::ZERO"
            else:
                raise ValueError("Invalid SAT value")
            pass
    
    def __eq__(self, other):
        return str(self) == str(other)


class QuType:
    DWT = 8
    FRAC = 4
    IF_SIGNED = True
    def __init__(self, DWT = 8, FRAC = 4, IF_SIGNED = True):
        self.DWT = DWT
        self.FRAC = FRAC
        self.IF_SIGNED = IF_SIGNED
    def MSB(self):
        return self.DWT - self.FRAC - 1
    def LSB(self):
        return - self.FRAC
    
    def set_dwt_frac(self, msb, lsb):
        self.DWT = msb - lsb + 1
        self.FRAC = - lsb

    def set(self,**kwargs):
        '''
        No conflict will occur even if you write MSB=... and LSB=... in set function.
        '''
        msb_helper = kwargs.get('MSB')
        lsb_helper = kwargs.get('LSB')
        if msb_helper is not None and lsb_helper is not None:
            msb_value = msb_helper() if callable(msb_helper) else msb_helper
            lsb_value = lsb_helper() if callable(lsb_helper) else lsb_helper
            self.set_dwt_frac(msb_value, lsb_value)
        else:
            print("MSB or LSB is missing")
    
    def intBits(self):
        return self.DWT - self.FRAC - int(self.IF_SIGNED)

    def fracBits(self):
        return self.FRAC
        
    def isSigned(self):
        if self.IF_SIGNED:
            return "true"
        else:
            return "false"

    