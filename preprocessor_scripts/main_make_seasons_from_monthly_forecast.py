#!/usr/bin/env python3
"""
Main script for creating seasonal averages from monthly forecast data.

This script sets the parameters and calls the functions from create_seasonal_forecast.py
to process the data. It processes all the model directories in the processed forecast directory.

The script uses environment variables from the .env file to determine the paths:
- FORECAST_BASE: Base directory for downloaded forecasts

Configuration to be set by the user:
- season_length: Number of months to average for seasonal forecasts

Output:
- Seasonal average forecast files in FORECAST_BASE/processed_{season_length}m_seasons/
"""

# ============= USER CONFIGURATION =============
# ---
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--season_length", default=None, help="Season length (e.g., 4 or 3)")
args = parser.parse_args()

# Parameters for seasonal averaging
season_length = int(args.season_length)
# ---

# ============= IMPORTS =============
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ============= ENVIRONMENT SETUP =============
# Load environment variables from .env file
load_dotenv()

# Check for required environment variables
if not os.getenv('FORECAST_BASE'):
    print("ERROR: FORECAST_BASE environment variable is not set.")
    print("Please set this variable in the .env file before running this script.")
    sys.exit(1)

# ============= PATH CONFIGURATION =============
# Define input and output directories
input_base_dir = os.path.join(os.getenv('FORECAST_BASE'), "processed")
output_base_dir = os.path.join(os.getenv('FORECAST_BASE'), f"processed_{season_length}m_seasons")

# Add project root to Python path
project_root = os.getenv('PROJECT_ROOT', str(Path(__file__).resolve().parents[1]))
if project_root not in sys.path:
    sys.path.append(project_root)

# ============= FUNCTION IMPORTS =============
# Import functions from the src module
from src.create_seasonal_forecast import (
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
            # Extract components from input filename (e.g., precAug2024lead11ens20canSipsIC4CanESM5.nc)
            base_name = os.path.splitext(filename)[0]
            # Replace lead time in the filename
            output_filename = base_name.replace(f"lead{metadata['dimensions']['lead']-1}", f"lead{last_lead_time}")
            # Add season length indicator and extension
            output_filename = f"{output_filename}_{season_length}m_seasons.nc"
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
    model_dirs = [d for d in os.listdir(input_base_dir) 
                 if os.path.isdir(os.path.join(input_base_dir, d))]
    total_models = len(model_dirs)
    
    print(f"Found {total_models} model directories to process")
    
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
            print(f"\nError processing model directory {model_dir}: {e}")
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
