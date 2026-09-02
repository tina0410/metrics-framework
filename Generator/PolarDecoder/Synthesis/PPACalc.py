from PyTU import QuType
import math

class Decoder:
    @staticmethod
    def CalcTP(period:float, N:int, M:int, iter:float):
        # period in ns
        # N: code length
        # M: parallelism
        # iter: average iteration count
        # Return TP in Gbps
        # Latency = N * math.log2(N) * iter / M + 2
        Latency = (2*(math.log2(N)-1) * iter + 1) * N / M + 2 # Type I
        # Latency = 18 * iter + 3
        K = N / 2 # Information Bits
        return K / period / Latency

    @staticmethod
    def CalcAE(TP:float, Area:float):
        # TP in Gbps
        # Area in um^2
        # Return AE in Gbps/mm^2
        return TP / Area * 1e6
        
    @staticmethod
    def CalcEE(TP:float, Power:float):
        # TP in Gbps
        # Power in mW
        # Return EE in pJ/b
        return Power/TP
       
        
        
if __name__ == "__main__":
    Decoder_N = 1024
    Decoder_M = 1024
    Decoder_iter = 5.63
    Decoder_period = 1.5
    
    Decoder_Area = 930661.569934
    Decoder_Power = 514.3270
    
    Decoder_TP = Decoder.CalcTP(period=Decoder_period, N=Decoder_N, M=Decoder_M, iter=Decoder_iter)
    Decoder_AE = Decoder.CalcAE(TP=Decoder_TP, Area=Decoder_Area)
    Decoder_EE = Decoder.CalcEE(TP=Decoder_TP, Power=Decoder_Power)

    print(f"Decoder Throughput: {Decoder_TP:.2f} Gbps, Area Efficiency: {Decoder_AE:.2f} Gbps/mm2, Power Efficiency: {Decoder_EE:.2f} pJ/b")

    COMP_Decoder_TP = 2.633
    COMP_Decoder_AE = 1.793
    COMP_Decoder_EE = 198.2

    Decoder_TP_Improvement = (Decoder_TP - COMP_Decoder_TP) / COMP_Decoder_TP
    Decoder_AE_Improvement = (Decoder_AE - COMP_Decoder_AE) / COMP_Decoder_AE
    Decoder_EE_Improvement =  - (Decoder_EE - COMP_Decoder_EE) / Decoder_EE
    print(f"Decoder TP Improvement: {Decoder_TP_Improvement:.2%}, AE Improvement: {Decoder_AE_Improvement:.2%}, EE Improvement: {Decoder_EE_Improvement:.2%}")
