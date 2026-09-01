import subprocess
import time
import sys
import os
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed


def run_lsce_generation(config_file, gen_root):
    """Function to run LSCE generation in a subprocess"""
    start_time = time.time()
    try:
        if os.path.exists(gen_root):
            shutil.rmtree(gen_root)
        os.makedirs(gen_root, exist_ok=True)
        # Import here to avoid issues with multiprocessing
        from designs.LSCE import GenLSCE
        result = GenLSCE(ConfigFileName=config_file, GenRoot=gen_root)
        end_time = time.time()
        return {
            'config': config_file,
            'gen_root': gen_root,
            'time': end_time - start_time,
            'result': result,
            'success': True
        }
    except Exception as e:
        end_time = time.time()
        return {
            'config': config_file,
            'gen_root': gen_root,
            'time': end_time - start_time,
            'result': None,
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    # Define the standard test cases without deleting unrelated RTL directories
    test_cases = [
        (f"./configs/config_case{i}.json", f"./RTL/Testcase{i}")
        for i in range(1, 6)
    ]
    
    print("Starting LSCE generation for standard test cases in parallel...")
    start_total_time = time.time()
    
    # Use ProcessPoolExecutor to run in parallel subprocesses
    with ProcessPoolExecutor(max_workers=len(test_cases)) as executor:
        # Submit all tasks
        future_to_case = {
            executor.submit(run_lsce_generation, config, gen_root): (config, gen_root)
            for config, gen_root in test_cases
        }
        
        # Collect results as they complete
        results = []
        for future in as_completed(future_to_case):
            config, gen_root = future_to_case[future]
            try:
                result = future.result()
                results.append(result)
                case_num = config.split('_case')[1].split('.')[0]
                if result['success']:
                    print(f"✓ Case {case_num} completed in {result['time']:.2f} seconds")
                else:
                    print(f"✗ Case {case_num} failed after {result['time']:.2f} seconds: {result['error']}")
            except Exception as exc:
                print(f"✗ Case {config} generated an exception: {exc}")
    
    # Sort results by case number for consistent output
    results.sort(key=lambda x: x['config'])
    
    end_total_time = time.time()
    total_time = end_total_time - start_total_time
    
    print(f"\n{'='*50}")
    print("Final Results:")
    print(f"{'='*50}")
    
    for i, result in enumerate(results):
        if result['success']:
            print(f"Time for case {i}: {result['time']:.2f} seconds")
        else:
            print(f"Case {i} failed: {result['error']}")
    
    print(f"\nTotal parallel execution time: {total_time:.2f} seconds")
    print(f"Number of successful cases: {sum(1 for r in results if r['success'])}/{len(test_cases)}")