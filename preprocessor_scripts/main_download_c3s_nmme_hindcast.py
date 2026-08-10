#!/usr/bin/env python3
"""
Main script for downloading and processing C3S and NMME hindcast data.

This script serves as the main entry point for downloading and processing seasonal climate
hindcast data from the Copernicus Climate Change Service (C3S) and North American Multi-Model
Ensemble (NMME) sources from the IRI data library server. 

The script performs the following tasks:
1. Loads model configuration from the specified JSON file
2. Identifies available models, including retired models
3. Validates requested models against available models
4. Downloads and processes hindcast data for specified models and months
5. Logs the process and results to both console and a log file

This script calls the src/download_and_interpolate_c3s_nmme_hindcast.py module, which handles
the actual downloading and interpolation of the data. The main script manages the overall
workflow, model validation, and logging.

Dependency Tree:
    main_download_c3s_nmme_hindcast.py
    ├── src/download_and_interpolate_c3s_nmme_hindcast.py (main data processing)
    │   ├── Reads model configuration from CONFIG_PATH/IRI_model_config/model_config.json
    │   ├── Downloads data from IRI Data Library
    │   └── Saves processed data to HINDCAST_BASE directory
    └── Creates logs in PROJECT_ROOT/logs directory

Configuration:
- Models: Specify the models to process in the MODELS list. Model lists can be generated using
  scripts/TOOLS/generate_hindcast_periods.py or the model list can be found in src/configs/common_hindcast_periods/
- Months: Specify the months to process in the MONTHS list
- REMOVE_RAW_FILES: Set to True to remove raw downloaded files after processing and interpolation
  (default is False, which keeps the raw files in the raw directory)

Environment Variables (from .env file):
- PROJECT_ROOT: Root directory of the project
- CONFIG_PATH: Path to the configuration directory
- HINDCAST_BASE: Base directory for downloaded hindcasts
- DATA_TEMP_DIR: Directory for temporary files during processing

Output:
- Downloaded and processed hindcast data in the HINDCAST_BASE directory
- Log files in the PROJECT_ROOT/logs directory

Example Usage:
    python scripts/main_download_c3s_nmme_hindcast.py

Note: 
- This script requires a properly configured .env file with the necessary environment variables.
- For downloading forecast data instead of hindcast data, use the main_download_c3s_nmme_forecast.py
  script, which follows a similar workflow but targets forecast data.
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
args = parser.parse_args()

MODELS = args.models
# ---

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# Cleanup options
REMOVE_RAW_FILES = False  # Set to True to remove raw downloaded files after processing
                         # Default is False to keep the raw files in the raw directory

# ============= INITIALIZATION =============
# Data validation options
ENABLE_MIN_CHECK = True  # Set to True to enable minimum precipitation threshold check. Should not be changed

# Load environment variables from .env file
load_dotenv()

# Check for required environment variables
required_vars = ['CONFIG_PATH', 'PROJECT_ROOT', 'HINDCAST_BASE', 'DATA_TEMP_DIR']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print("ERROR: The following required environment variables are not set:")
    for var in missing_vars:
        print(f"  - {var}")
    print("\nPlease set these variables in the .env file or environment before running this script.")
    sys.exit(1)

# Add the project root to the Python path
project_root = os.getenv('PROJECT_ROOT')
sys.path.insert(0, project_root)

# Get base directories from environment variables
HINDCAST_BASE = os.getenv('HINDCAST_BASE')

# Set up paths using environment variables
CONFIG_PATH = os.path.join(os.getenv('CONFIG_PATH'), "IRI_model_config", "model_config.json")
LOG_DIR = os.path.join(project_root, "logs")

# Load model configuration
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
        if 'hindcast' in info:
            available_models.append(model)
        elif 'submodels' in info:
            # For models with submodels (like CanSIPS)
            for submodel, submodel_info in info['submodels'].items():
                if 'hindcast' in submodel_info:
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
    print("\nAvailable hindcast models:")
    print("-" * 50)
    print("Regular models:")
    for model in sorted(available_models):
        status = model_config['models'][model].get('status', 'active')
        status_str = f" (status: {status})" if status == 'retired' else ""
        print(f"- {model}{status_str}")
    
    if available_submodels:
        print("\nModels with submodels:")
        for model in sorted(available_submodels):
            parent_model, submodel = model.split('.')
            status = model_config['models'][parent_model].get('status', 'active')
            status_str = f" (status: {status})" if status == 'retired' else ""
            print(f"- {model}{status_str}")
    print("-" * 50)


def validate_models(models):
    """
    Validate that the specified models are available in the configuration.
    
    Parameters
    ----------
    models : list
        List of model names to validate
        
    Raises
    ------
    ValueError
        If any model is not in the list of available models
    """
    for model in models:
        if model not in ALL_AVAILABLE_MODELS:
            raise ValueError(f"Invalid model: {model}")


# Get and print available models
AVAILABLE_MODELS, AVAILABLE_SUBMODELS, ALL_AVAILABLE_MODELS = get_available_models(MODEL_CONFIG)
print_available_models(MODEL_CONFIG, AVAILABLE_MODELS, AVAILABLE_SUBMODELS)

from src.download_and_interpolate_c3s_nmme_hindcast import main

from src.utils.logging_utils import setup_logging as setup_logging_util

def setup_logging():
    """Set up logging to both console and file."""
    return setup_logging_util(LOG_DIR)

if __name__ == "__main__":
    log_file = setup_logging()
    print(f"Starting hindcast download process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Log file: {log_file}\n")
    
    start_time = pd.Timestamp.now()
    
    # Validate models
    try:
        validate_models(MODELS)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Define ANSI color codes
    GREEN = '\033[32m'  # Dark green
    RED = '\033[91m'    # Bright red
    YELLOW = '\033[93m' # Bright yellow
    MAGENTA = '\033[95m' # Magenta
    RESET = '\033[0m'   # Reset color
    
    # Process each model
    total_failed = 0
    total_skipped = 0
    total_completed = 0
    skipped_models = []
    models_with_nan_warnings = []  # Track models with NaN warnings
    
    for model in MODELS:
        if model not in ALL_AVAILABLE_MODELS:
            print(f"Warning: Model {model} is not in the list of available models. Skipping.")
            total_skipped += 1
            skipped_models.append(model)
            continue
            
        result, has_nan_warnings = main(model, MONTHS, enable_min_check=ENABLE_MIN_CHECK, remove_raw_files=REMOVE_RAW_FILES)  # No YEARS parameter for hindcasts
        if result == 0:
            total_completed += 1
        else:
            total_failed += 1
            
        # Track models with NaN warnings
        if has_nan_warnings:
            models_with_nan_warnings.append(model)
    
    # Print overall execution summary
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
            
    # Display models with NaN warnings
    if models_with_nan_warnings:
        print(f"\n{MAGENTA}⚠ Models with NaN ensemble members:{RESET}")
        for model in models_with_nan_warnings:
            print(f"{MAGENTA}- {model}{RESET}")
            # Show the exact path to the warning file for this model
            warning_file_path = os.path.join(HINDCAST_BASE, "processed", model, "README_WARNING_MISSING_MEMBERS.txt")
            if os.path.exists(warning_file_path):
                print(f"{MAGENTA}  Warning file: {warning_file_path}{RESET}")
        
        print(f"\n{MAGENTA}Note: These models have ensemble members with missing data.{RESET}")
    
    print(f"\nTotal execution time: {pd.Timestamp.now() - start_time}")
    
    sys.exit(1 if total_failed > 0 else 0)
