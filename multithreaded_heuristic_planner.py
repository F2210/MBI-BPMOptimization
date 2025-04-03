#!/usr/bin/env python3
"""
Business Process Management (BPM) Optimization Simulator with Parallelization

This script runs multiple instances of a healthcare business process simulation in parallel
to gather statistically significant results and analyze performance metrics. It leverages
Python's multiprocessing to distribute the computational load across multiple CPU cores.

The simulation focuses on optimizing resource allocation in a healthcare setting, evaluating
metrics like waiting times, patient nervousness, and personnel costs against baseline values.

Usage:
    ./multithread_run --processes N --days D --resource-index R

Where:
    N = Number of parallel simulations (default: 6)
    D = Number of days to simulate (default: 365)
    R = Index of resource schedule configuration to use (default: 0)
"""
import multiprocessing
import os
import json
import statistics
import argparse
import sys
from heuristic_planner import HeuristicPlanner
from simulator import Simulator
from problems import HealthcareProblem
from resource_logistics import regular_resource_allocation

def run_planner(process_id, results_dict, resource_schedule_index=0, simulation_days=365):
    """
    Run a single instance of the heuristic planner in its own process.
    
    Each process simulates a healthcare environment for the specified number of days,
    using a predetermined resource schedule. Results are collected in a shared dictionary
    for later aggregation and analysis.
    
    Args:
        process_id (int): Unique identifier for this simulation process
        results_dict (dict): Shared dictionary to store simulation results
        resource_schedule_index (int): Index of resource schedule to use from predefined options
        simulation_days (int): Number of days to simulate (converted to hours internally)
    
    Notes:
        - Each process writes its event log to a separate file to prevent I/O conflicts
        - Results are written to individual files and also stored in the shared dictionary
        - Cost metric is calculated with personnel costs weighted 3x to reflect their importance
    """
    try:
        # Select the resource schedule based on provided index
        # This allows testing different resource allocation strategies
        optimized_resource_schedule = regular_resource_allocation[resource_schedule_index]
        
        # Create process-specific event log file to avoid concurrent access issues
        event_log_file = f"./temp/event_log_{process_id}.csv"
        
        # Initialize planner with the resource schedule
        # The planner handles resource allocation and scheduling within the simulation
        planner = HeuristicPlanner(
            event_log_file, ["diagnosis"], optimized_resource_schedule
        )
        problem = HealthcareProblem()  # Defines the healthcare-specific simulation parameters
        simulator = Simulator(planner, problem)  # Combines the planner with the problem domain

        # Run simulation for specified number of days (converted to hours)
        # The simulator tracks events at hourly intervals
        result = simulator.run(simulation_days * 24)
        
        # Calculate cost metric with weighted components
        # Personnel costs are weighted more heavily (3x) as they represent the most
        # significant and controllable expense in healthcare settings
        cost = (
            result["waiting_time_for_admission"]
            + result["waiting_time_in_hospital"]
            + result["nervousness"]
            + result["personnel_cost"] * 3
        )
        
        # Store calculated metrics in the results
        result["total_cost"] = cost
        results_dict[process_id] = result  # Add to shared dictionary for later analysis
        
        # Write individual run results to separate files for detailed inspection if needed
        os.makedirs("runs", exist_ok=True)
        with open(f"runs/run_{process_id}.txt", "w") as file:
            file.write(f"Result: {result}\n")
            file.write(f"TOTAL COST = {cost}\n")
            
        print(f"Process {process_id} completed successfully")
    except Exception as e:
        # Robust error handling ensures one failed simulation doesn't affect others
        print(f"Error in process {process_id}: {str(e)}")
        results_dict[process_id] = {"error": str(e)}  # Store error for analysis

def main():
    """
    Main function to coordinate multiple parallel simulation runs.
    
    This function:
    1. Parses command-line arguments to configure the simulation
    2. Sets up the multiprocessing environment
    3. Launches multiple simulation processes
    4. Collects and aggregates results
    5. Computes statistical measures (mean, median, etc.)
    6. Compares results against baseline values
    7. Outputs formatted results and saves them to disk
    
    The parallel approach allows for more statistically robust results by running
    multiple simulations and aggregating their outcomes, while also utilizing
    available CPU resources effectively.
    """
    # Parse command line arguments for flexible configuration without code changes
    parser = argparse.ArgumentParser(description='Run multiple BPM optimization simulations in parallel')
    parser.add_argument('--processes', type=int, default=6, help='Number of parallel simulations to run')
    parser.add_argument('--days', type=int, default=365, help='Number of days to simulate')
    parser.add_argument('--resource-index', type=int, default=0, help='Index of resource schedule to use')
    args = parser.parse_args()
    
    # Create required directories for storing temporary and results data
    # Using exist_ok=True prevents errors if directories already exist
    os.makedirs("./temp", exist_ok=True)
    os.makedirs("./runs", exist_ok=True)
    
    # Initialize multiprocessing resources
    # Manager provides a way to create data structures that can be shared between processes
    manager = multiprocessing.Manager()
    results_dict = manager.dict()  # Shared dictionary to collect results from all processes
    processes = []
    
    print(f"Starting {args.processes} planner instances simulating {args.days} days each...")
    print(f"Using resource schedule at index {args.resource_index}")
    
    # Create and start processes
    # Each process will run independently with its own interpreter and memory space (while resuing the same python interpreter)
    python_interpreter_path = sys.executable
    for i in range(args.processes):
        process = multiprocessing.Process(
            target=run_planner, 
            args=(i, results_dict, args.resource_index, args.days)
        )
        process._config = {'python_executable': python_interpreter_path}  # Ensure the correct interpreter is used
        processes.append(process)
        process.start()
    
    # Wait for all processes to complete
    for process in processes:
        process.join()
    
    # Convert the shared dict to a list
    results = [results_dict[i] for i in range(args.processes) if i in results_dict]
    
    # Filter out any failed runs
    valid_results = [r for r in results if isinstance(r, dict) and "error" not in r]
    
    if not valid_results:
        print("All simulation runs failed. Check the error logs.")
        return
    
    print(f"Completed {len(valid_results)} successful simulations. Calculating statistics...")
    
    # Rest of the function remains the same
    # Define baseline averages
    baseline_values = {
        "waiting_time_for_admission": 286588.8,
        "waiting_time_in_hospital": 3482504.4, 
        "nervousness": 2959006,
        "personnel_cost": 733611.6
    }

    baseline_values['total_cost'] = (
        baseline_values["waiting_time_for_admission"]
        + baseline_values["waiting_time_in_hospital"]
        + baseline_values["nervousness"]
        + baseline_values["personnel_cost"] * 3
    )
    
    # Calculate statistics for each metric
    aggregated_results = {}
    for key in valid_results[0].keys():
        values = [result[key] for result in valid_results]
        
        # Check if values are numeric before calculating statistics
        if all(isinstance(val, (int, float)) for val in values):
            aggregated_results[key] = {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values)
            }
            
            # Add comparison to baseline if available
            if key in baseline_values:
                mean_value = aggregated_results[key]["mean"]
                baseline = baseline_values[key]
                # Avoid division by zero
                if baseline != 0:
                    percent_diff = ((mean_value - baseline) / baseline) * 100
                else:
                    percent_diff = float('inf') if mean_value > 0 else 0.0
                aggregated_results[key]["baseline_value"] = baseline
                aggregated_results[key]["percent_diff"] = percent_diff
        else:
            # Handle non-numeric values
            aggregated_results[key] = {
                "mean": "N/A",
                "min": "N/A",
                "max": "N/A"
            }
    
    # Print results table
    print("\nAggregated Results:")
    print("=" * 80)
    print(f"{'KPI':<30} {'Mean':>10} {'Min':>10} {'Max':>10} {'Baseline':>10} {'% Diff':>10}")
    print("-" * 80)
    
    for key, stats in aggregated_results.items():
        # Format output based on data types
        mean_val = f"{stats['mean']:.2f}" if isinstance(stats['mean'], (int, float)) else stats['mean']
        min_val = f"{stats['min']:.2f}" if isinstance(stats['min'], (int, float)) else stats['min']
        max_val = f"{stats['max']:.2f}" if isinstance(stats['max'], (int, float)) else stats['max']
        baseline_val = f"{stats.get('baseline_value')}" if 'baseline_value' in stats else 'N/A'
        percent_val = f"{stats.get('percent_diff'):.0f}" if 'percent_diff' in stats and isinstance(stats.get('percent_diff'), (int, float)) else 'N/A'
        
        print(f"{key:<30} {mean_val:>10} {min_val:>10} {max_val:>10} {baseline_val:>10} {percent_val:>10}")
    
    # Save results to JSON
    with open("runs/aggregated_results.json", "w") as file:
        json.dump(aggregated_results, file, indent=4)
    
    print("\nAggregated results saved to 'runs/aggregated_results.json'")

if __name__ == "__main__":
    main()
