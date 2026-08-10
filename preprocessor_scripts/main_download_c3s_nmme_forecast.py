#!/usr/bin/env python3
"""
Main script for downloading and processing C3S and NMME forecast data.

This script serves as the main entry point for downloading and processing seasonal climate
forecast data from the Copernicus Climate Change Service (C3S) and North American Multi-Model
Ensemble (NMME) sources from the IRI data library server. 

The script performs the following tasks:
1. Loads model configuration from the specified JSON file
2. Identifies available models, including retired models
3. Validates requested models against available models
4. Downloads and processes forecast data for specified models and dates
5. Logs the process and results to both console and a log file

This script calls the src/download_and_interpolate_c3s_nmme_forecast.py module, which handles
the actual downloading and interpolation of the data. The main script manages the overall
workflow, model validation, and logging.

Dependency Tree:
    main_download_c3s_nmme_forecast.py
    ├── src/download_and_interpolate_c3s_nmme_forecast.py (main data processing)
    │   ├── Reads model configuration from CONFIG_PATH/IRI_model_config/model_config.json
    │   ├── Downloads data from IRI Data Library
    │   └── Saves processed data to FORECAST_BASE directory
    └── Creates logs in PROJECT_ROOT/logs directory

Configuration:
- Models: Specify the models to process in the MODELS list. Model lists can be generated using
  scripts/TOOLS/generate_hindcast_periods.py or the model list can be found in src/configs/common_hindcast_periods/
- Forecast dates: Specify the dates to process in the FORECAST_DATES list as (year, month) tuples
- REMOVE_RAW_FILES: Set to True to remove raw downloaded files after processing and interpolation
  (default is False, which keeps the raw files in the raw directory)

Environment Variables (from .env file):
- PROJECT_ROOT: Root directory of the project
- CONFIG_PATH: Path to the configuration directory
- FORECAST_BASE: Base directory for downloaded forecasts
- DATA_TEMP_DIR: Directory for temporary files during processing

Output:
- Downloaded and processed forecast data in the FORECAST_BASE directory
- Log files in the PROJECT_ROOT/logs directory

Example Usage:
    python scripts/main_download_c3s_nmme_forecast.py

Note: 
- This script requires a properly configured .env file with the necessary environment variables.
- For downloading hindcast data instead of forecast data, use the main_download_c3s_nmme_hindcast.py
  script, which follows a similar workflow but targets hindcast data.
"""

# ============= IMPORTS =============
# Standard library imports
import os
import sys
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import argparse

# ============= USER CONFIGURATION =============
# Set the models, months, and years to process
# ---
parser = argparse.ArgumentParser()
parser.add_argument("--models", nargs="+", default=[
    "CMCC-SPSv4",
    "COLA-RSMAS-CCSM4", "COLA-RSMAS-CESM1",
    "CanSIPS-IC4.CanESM5", "CanSIPS-IC4.GEM5p2-NEMO",
    "DWD-GCFS2p2", "ECMWF-SEAS51_iri2", "GFDL-SPEAR",
    "JMA-CPS3", "Meteo_France-System9",
    "NASA-GEOSS2S", "NCEP-CFSv2", "UKMO-GloSea6-GC2-System604"
])
parser.add_argument("--init_month", default=None, help="Initialization month (e.g., Aug)")
parser.add_argument("--init_year", default=None, help="Initialization year (e.g., 2026)")
args = parser.parse_args()

MODELS = args.models
init_month = str(args.init_month)
init_year = str(args.init_year)

if init_month is None or init_year is None:
    parser.error("--init_month and --init_year must be specified.")

FORECAST_DATES = [
    (init_year, init_month),
]
# ---

# Define forecast dates to process as (year, month)
#
# FORECAST_DATES = [
#     ("2026", "Aug"),
#     #("2026", "May")
# ]

# Cleanup options
REMOVE_RAW_FILES = False  # Set to True to remove raw downloaded files after processing
                         # Default is False to keep the raw files in the raw directory

# ============= INITIALIZATION =============

# ANSI color codes for terminal output
RESET = "\033[0m"        # Reset to default
RED = "\033[31m"         # Red for errors
GREEN = "\033[32m"       # Green for success
MAGENTA = "\033[35m"     # Magenta for warnings
BLUE = "\033[34m"        # Blue for info

# Load environment variables from .env file
load_dotenv()

# Check for required environment variables
required_vars = ['CONFIG_PATH']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print("ERROR: The following required environment variables are not set:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\nPlease set these variables in the .env file or environment before running this script.")
    sys.exit(1)

# Add the project root to the Python path
project_root = os.getenv('PROJECT_ROOT', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Load model configuration using CONFIG_PATH from .env
CONFIG_PATH = os.path.join(os.getenv('CONFIG_PATH'), "IRI_model_config", "model_config.json")
print(f"\nLoading model configuration from: {os.path.abspath(CONFIG_PATH)}")
with open(CONFIG_PATH) as f:
    MODEL_CONFIG = json.load(f)

def get_available_models(model_config):
    """
    Get list of available models from the configuration, including both regular models
    and models with submodels.
    
    Parameters
    ----------
    model_config : dict
        The model configuration dictionary
        
    Returns
    -------
    tuple
        (regular_models, submodels, all_models) - Lists of available models
    """
    available_models = []
    available_submodels = []
    
    for model, info in model_config['models'].items():
        if 'forecast' in info:
            available_models.append(model)
        elif 'submodels' in info:
            # For models with submodels (like CanSIPS)
            for submodel, submodel_info in info['submodels'].items():
                if 'forecast' in submodel_info:
                    full_model_name = f"{model}.{submodel}"
                    available_submodels.append(full_model_name)
    
    # Combine both lists
    all_available_models = available_models + available_submodels
    
    return available_models, available_submodels, all_available_models


def print_available_models(model_config, available_models, available_submodels):
    """
    Print the list of available models, including their status.
    
    Parameters
    ----------
    model_config : dict
        The model configuration dictionary
    available_models : list
        List of regular available models
    available_submodels : list
        List of available submodels
    """
    print("\nAvailable models:")
    print("-" * 50)
    print("Regular models:")
    for model in sorted(available_models):
        status = model_config['models'][model].get('status', 'active')
        status_str = f" (status: {status})" if status == 'retired' else ""
        print(f"- {model}{status_str}")
    
    print("\nModels with submodels:")
    for model in sorted(available_submodels):
        parent_model, submodel = model.split('.')
        status = model_config['models'][parent_model].get('status', 'active')
        status_str = f" (status: {status})" if status == 'retired' else ""
        print(f"- {model}{status_str}")
    print("-" * 50)


# Get and print available models
AVAILABLE_MODELS, AVAILABLE_SUBMODELS, ALL_AVAILABLE_MODELS = get_available_models(MODEL_CONFIG)
print_available_models(MODEL_CONFIG, AVAILABLE_MODELS, AVAILABLE_SUBMODELS)

# Set up our logging before importing the main module
# This prevents duplicate logging
def setup_logging():
    """Set up logging to both console and file."""
    import logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"download_forecast_{timestamp}.log")
    
    # Create a custom logger
    class Logger:
        def __init__(self, log_file):
            self.terminal = sys.stdout
            self.log = open(log_file, 'w', encoding='utf-8')
        
        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
            self.log.flush()
        
        def flush(self):
            self.terminal.flush()
            self.log.flush()
    
    # Set up the logger
    sys.stdout = Logger(log_file)
    print(f"Starting forecast download process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Log file: {log_file}\n")
    
    return log_file

# Set up logging first, before importing the main module
log_file = setup_logging()

# Now it's safe to import the main module - it will detect that logging is already set up
from src.download_and_interpolate_c3s_nmme_forecast import main

def validate_models(models):
    """Validate that the specified models are available in the configuration."""
    for model in models:
        if model not in ALL_AVAILABLE_MODELS:
            raise ValueError(f"Invalid model: {model}")

if __name__ == "__main__":
    # Track execution time
    start_time = pd.Timestamp.now()
    
    # Initialize counters
    total_completed = 0
    total_failed = 0
    total_skipped = 0
    skipped_models = []  # Track which models were skipped
    
    # Process each model and forecast date
    for model in MODELS:
        if model not in ALL_AVAILABLE_MODELS:
            print(f"{MAGENTA}⚠ Warning: Model {model} is not in the list of available models. Skipping.{RESET}")
            total_skipped += 1
            skipped_models.append(model)
            continue
            
        for year, month in FORECAST_DATES:
            print(f"\nProcessing {model} for {month} {year}")
            try:
                # Pass month and year as lists to match the expected function signature
                result = main(model, [month], [year], remove_raw_files=REMOVE_RAW_FILES)
                if result == 0:
                    total_completed += 1
                else:
                    total_failed += 1
            except Exception as e:
                print(f"Error processing {model} for {month} {year}: {e}")
                total_failed += 1
                # Continue with next combination instead of stopping
    
    # Print summary
    print("\nAll processing complete.")
    print("\nOverall Execution Summary:")
    print("=" * 50)
    print(f"Models processed ({len(MODELS)}):")
    for model in MODELS:
        print(f"- {model}")
    print(f"Total tasks completed: {GREEN}{total_completed}{RESET}")
    if total_failed > 0:
        print(f"Total failed: {RED}{total_failed}{RESET}")
    else:
        print(f"Total failed: {total_failed}")
    print(f"Total skipped (not available): {MAGENTA}{total_skipped}{RESET}")
    if skipped_models:
        print(f"\n{MAGENTA}Skipped models:{RESET}")
        for model in skipped_models:
            print(f"{MAGENTA}- {model}{RESET}")
    
    print(f"\nTotal execution time: {pd.Timestamp.now() - start_time}")
    
    sys.exit(1 if total_failed > 0 else 0)
