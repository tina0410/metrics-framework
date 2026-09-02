import json
from polar_bp_decoder import Moduletop
import pytv
import time
from pytv import convert
from pytv import moduleloader
def GenBPDecoder(ConfigFileName="./config.json", GenRoot="./RTL"):
    # Load Configuration
    import json
    
    try:
        with open(ConfigFileName, 'r') as f:
            config = json.load(f)
        
        archi = config.get("Hardware Architecture", "TypeI")
        algo = config.get("Decoding Algorithm", "MS")
        N = config.get("Code Length", 1024)
        M = config.get("Parallelism", 1024)
        width = config.get("Data Width",5)
        
    except FileNotFoundError:
        print(f"Warning: Config file {ConfigFileName} not found. Using default parameters.")
        archi = "TypeI"
        algo = "MS"
        N = 1024
        M = 1024
        width = 5
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file {ConfigFileName}: {e}")
        return
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # Generate Module
    moduleloader.set_root_dir(GenRoot)
    moduleloader.set_naming_mode("SEQUENTIAL")
    # moduleloader.saveParams()
    moduleloader.disEnableWarning()
    start_gen_time = time.perf_counter()
    Moduletop(archi=archi, algo=algo, N=N, M=M, width=width)
    end_gen_time = time.perf_counter()
    print(f"Generated {archi} {algo} decoder with Code Length N={N} and Parallelism M={M} in {end_gen_time - start_gen_time:.2f} seconds.\n")
    return end_gen_time - start_gen_time
    pass
