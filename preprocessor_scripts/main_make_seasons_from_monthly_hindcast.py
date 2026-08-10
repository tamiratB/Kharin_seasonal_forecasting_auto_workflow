#!/usr/bin/env python3
"""
Main script for creating seasonal averages from monthly hindcast data.

This script sets the parameters and calls the functions from create_seasonal_hindcast.py
to process the data. It processes model directories in the processed hindcast directory.

The script uses environment variables from the .env file to determine the paths:
- HINDCAST_BASE: User defined base directory for downloaded hindcasts (used for output and input by default)
- HINDCAST_BASE_ALTERNATE: Optional alternate base directory for input data, such as from another user

Configuration to be set by the user:
- season_length: Number of months to average for seasonal hindcasts
- use_alternate_source: Whether to use HINDCAST_BASE_ALTERNATE for input data instead of HINDCAST_BASE
- models_to_process: List of specific models to process. If empty or contains only 'ALL',
  all available models will be processed. Otherwise, only the specified models will be processed.

Output:
- Seasonal average hindcast files in HINDCAST_BASE/processed_{season_length}m_seasons/
  (output always goes to HINDCAST_BASE regardless of input source)
"""

# ============= USER CONFIGURATION =============

# ---
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--models", nargs="+", default=[
    "CMCC-SPSv4",
    "COLA-RSMAS-CCSM4", "COLA-RSMAS-CESM1",
    "CanSIPS-IC4.CanESM5", "CanSIPS-IC4.GEM5p2-NEMO",
    "DWD-GCFS2p2", "ECMWF-SEAS51_iri2", "GFDL-SPEAR",
    "JMA-CPS3", "Meteo_France-System9",
    "NASA-GEOSS2S", "NCEP-CFSv2", "UKMO-GloSea6-GC2-System604"
])
parser.add_argument("--season_length", default=None, help="Season length (e.g., 4 or 3)")
args = parser.parse_args()
# Parameters for seasonal averaging
models_to_process = args.models
season_length = int(args.season_length)
# ---

# Whether to use alternate source for downloaded hindcast input data
# Set to True to use HINDCAST_BASE_ALTERNATE for input downloaded hindcasts.
# The default is False, that is for using the user's own downloaded hindcasts.
use_alternate_source = False

# ============= IMPORTS =============
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ============= ENVIRONMENT SETUP =============
# Load environment variables from .env file
load_dotenv()

# Print all environment variables for debugging
print("Environment variables loaded:")
print(f"HINDCAST_BASE: {os.getenv('HINDCAST_BASE')}")
print(f"HINDCAST_BASE_ALTERNATE: {os.getenv('HINDCAST_BASE_ALTERNATE')}")

# Get environment variables
HINDCAST_BASE = os.getenv('HINDCAST_BASE')
HINDCAST_BASE_ALTERNATE = os.getenv('HINDCAST_BASE_ALTERNATE')
PROJECT_ROOT = os.getenv('PROJECT_ROOT')

# Check for required environment variables
if not HINDCAST_BASE:
    print("ERROR: HINDCAST_BASE environment variable is not set.")
    print("Please set this variable in the .env file before running this script.")
    sys.exit(1)

# Check for alternate source if enabled
if use_alternate_source and not HINDCAST_BASE_ALTERNATE:
    print("ERROR: use_alternate_source is enabled but HINDCAST_BASE_ALTERNATE environment variable is not set.")
    print("Please set this variable in the .env file or disable use_alternate_source.")
    sys.exit(1)

# ============= PATH CONFIGURATION =============
# Determine input base directory based on configuration
if use_alternate_source:
    input_base = HINDCAST_BASE_ALTERNATE
    print(f"Using alternate source for input: {input_base}")
else:
    input_base = HINDCAST_BASE

# Define input and output directories
input_base_dir = os.path.join(input_base, "processed")
output_base_dir = os.path.join(HINDCAST_BASE, f"processed_{season_length}m_seasons")

# Print paths for verification
print(f"Input directory: {input_base_dir}")
print(f"Output directory: {output_base_dir}")

# Add project root to Python path
if PROJECT_ROOT and PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
else:
    # Fallback to default if PROJECT_ROOT is not set
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.append(project_root)

# ============= FUNCTION IMPORTS =============
# Import functions from the src module
from src.create_seasonal_hindcast import (
    load_and_validate_data, 
    validate_season_length,
    create_seasonal_average
)

# ============= PROCESSING FUNCTIONS =============
def process_model_files(input_dir: str, output_dir: str, season_length: int) -> None:
    """
    Process all files in a model directory.
    
    Args:
        input_dir: Input directory containing NetCDF files
        output_dir: Output directory for seasonal averages
        season_length: Number of months to average
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get list of all NetCDF files
    nc_files = [f for f in os.listdir(input_dir) if f.endswith('.nc')]
    total_files = len(nc_files)
    
    print(f"Found {total_files} NetCDF files to process")
    
    # Process each file in the directory
    for i, filename in enumerate(nc_files, 1):
        input_file = os.path.join(input_dir, filename)
        
        print(f"\nProcessing file {i}/{total_files}: {filename}")
        
        try:
            # Load and validate data
            ds, metadata = load_and_validate_data(input_file)
            print("Dataset dimensions:", metadata['dimensions'])
            
            # Validate season length
            max_lead_time = metadata['dimensions']['lead'] - 1
            validate_season_length(season_length, max_lead_time)
            
            # Create seasonal averages
            print("Creating seasonal averages...")
            seasonal_ds = create_seasonal_average(ds, season_length)
            print(f"New lead time dimension: {len(seasonal_ds.lead)}")
            
            # Construct output filename
            last_lead_time = len(seasonal_ds.lead) - 1  # Get last lead time index
            name_parts = filename.split('_')
            model_info = name_parts[0].replace(f"lead{metadata['dimensions']['lead']-1}", f"lead{last_lead_time}")
            years_info = '_'.join(name_parts[1:])
            output_filename = f"{model_info}_{season_length}m_seasons_{years_info}"
            output_file = os.path.join(output_dir, output_filename)
            
            # Save to netCDF file
            seasonal_ds.to_netcdf(output_file)
            print(f"Successfully saved to: {output_file}")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue

# ============= MAIN EXECUTION =============
def main():
    # Get list of all model directories
    all_model_dirs = [d for d in os.listdir(input_base_dir) 
                     if os.path.isdir(os.path.join(input_base_dir, d))]
    
    # Determine which models to process based on user configuration
    if not models_to_process or models_to_process == ['ALL']:
        # Process all available models
        model_dirs = all_model_dirs
        print(f"Processing ALL {len(model_dirs)} available model directories")
    else:
        # Process only the specified models
        model_dirs = [d for d in all_model_dirs if d in models_to_process]
        print(f"Processing {len(model_dirs)} of {len(all_model_dirs)} available model directories")
        print(f"Models to process: {', '.join(model_dirs)}")
        
        # Check if any specified models are not found
        missing_models = [m for m in models_to_process if m not in all_model_dirs]
        if missing_models:
            print(f"WARNING: The following specified models were not found: {', '.join(missing_models)}")
    
    if not model_dirs:
        print("No models to process. Exiting.")
        return
    
    total_models = len(model_dirs)
    
    # Process each model directory
    for i, model_dir in enumerate(sorted(model_dirs), 1):
        print(f"\n{'='*80}")
        print(f"Processing model {i}/{total_models}: {model_dir}")
        print(f"{'='*80}")
        
        input_dir = os.path.join(input_base_dir, model_dir)
        output_dir = os.path.join(output_base_dir, model_dir)
        
        print(f"Input directory: {input_dir}")
        print(f"Output directory: {output_dir}")
        
        try:
            process_model_files(input_dir, output_dir, season_length)
            print(f"\nSuccessfully processed all files in {model_dir}")
        except Exception as e:
            print(f"ERROR processing model {model_dir}: {str(e)}")
            print("Continuing with next model...")
            continue
    
    print("\nAll model directories processed!")
    print(f"\n{'='*80}")
    print(f"RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"Seasonal averages ({season_length}-month) have been created successfully.")
    print(f"\nResults can be found in:")
    print(f"  {output_base_dir}")
    print(f"\nEach model has its own subdirectory with the processed files.")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
