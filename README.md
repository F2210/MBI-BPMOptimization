# BPM Optimization

This repository contains tools for business process optimization, including a heuristic planner and a multithreaded variant focused on healthcare resource scheduling.

## Running the Heuristic Planner

The `heuristic_planner.py` implements a heuristic-based scheduler that optimizes healthcare resource allocation to reduce waiting times and costs.

### Basic Usage

```bash
python heuristic_planner.py
```

When run directly, the script:
- Executes a simulation run
- Outputs results to the "runs" directory
- Generates resource usage visualization for weeks 2-8

### Implementation Details

- Optimizes resources across different time slots (morning, afternoon, evening, night)
- Handles patient admission planning based on intaker availability
- Tracks metrics like waiting time, nervousness, and personnel costs
- Generates event logs and resource utilization reports

## Running the Multithreaded Heuristic Planner

The `multithreaded_heuristic_planner.py` runs multiple simulations in parallel to gather a more complete insight and results.

### Prerequisites

- Python 3.13.x
- run: pip install -r requirements.txt
- Multiprocessing support

### Basic Usage

```bash
python multithreaded_heuristic_planner.py [options]
```

### Command Line Options

- `--processes N`: Number of parallel simulations (default: 6)
- `--days D`: Number of days to simulate (default: 365)
- `--resource-index R`: Index of resource schedule configuration to use (default: 0)

### Example

```bash
python multithreaded_heuristic_planner.py --processes 12 --days 365
```

### Output

The multithreaded planner:
- Creates individual event logs for each process
- Saves individual run results to the "runs" directory
- Calculates aggregated statistics (mean, min, max)
- Compares results against baseline values (computed based on 5 __example__.py runs and averaged)
- Outputs a formatted results table
- Saves aggregated results to "runs/aggregated_results.json"

### Performance Metrics

Both planners track key performance indicators:
- Waiting time for admission
- Waiting time in hospital
- Patient nervousness levels
- Personnel costs
- Total weighted cost (personnel costs weighted 3x)
