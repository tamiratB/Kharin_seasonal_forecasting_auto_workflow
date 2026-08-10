#!/usr/bin/env python3
"""
Main script to create lead time files for calibration from forecast data.

This script configures and initiates the process of creating lead time-specific NetCDF files
from processed forecast data for specific initialization months and years. These files
are used for calibration and verification of seasonal forecasts.

Module Dependencies:
- src.create_lead_files_for_forecast: Core module that provides the functions for processing
  lead time files (setup_logging, test_get_model_files, process_lead_time)

Data Dependency Tree:
1. Raw downloaded forecast data (from main_download_c3s_nmme_forecast.py)
2. Processed seasonal forecast data (from main_make_seasons_from_monthly_forecast.py)
3. Lead time files for calibration (this script)
4. Calibrated forecast data (used by other scripts)

The script uses environment variables from the .env file to determine paths:
- PROJECT_ROOT: Root directory of the project
- FORECAST_BASE: Base directory for forecast data
- LOG_DIR: Directory for log files (defaults to PROJECT_ROOT/logs)

Configuration to be set by the user:
- MODELS: List of models to process
- FORECAST_DATES: List of initialization dates to process
- SEASON_LENGTH: Number of months in the seasonal average

Output:
- Lead time-specific NetCDF files in FORECAST_BASE/prepared_for_forecast_{SEASON_LENGTH}m_SEASONS/
  with naming format: X_lead{lead_time}.nc
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
parser.add_argument("--init_month", default=None, help="Initialization month (e.g., Aug)")
parser.add_argument("--init_year", default=None, help="Initialization year (e.g., 2026)")
args = parser.parse_args()

MODELS = args.models
SEASON_LENGTH = int(args.season_length)
init_month = str(args.init_month)
init_year = str(args.init_year)

if init_month is None or init_year is None:
    parser.error("--init_month and --init_year must be specified.")

FORECAST_DATES = [
    (init_year, init_month),
]
# ---

# ============= IMPORTS =============
# Standard library imports
import os
import sys
import logging
from datetime import datetime
from typing import List

# Third-party imports
from dotenv import load_dotenv

# ============= ENVIRONMENT SETUP =============
# Load environment variables
load_dotenv()

# Get environment variables with defaults
PROJECT_ROOT = os.getenv('PROJECT_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  
FORECAST_BASE = os.getenv('FORECAST_BASE', os.path.join(PROJECT_ROOT, 'data', 'downloaded_forecasts'))
LOG_DIR = os.getenv('LOG_DIR', os.path.join(PROJECT_ROOT, 'logs'))

# Check for required environment variables
if not os.path.exists(FORECAST_BASE):
    print(f"WARNING: FORECAST_BASE directory does not exist: {FORECAST_BASE}")
    print("Please check your .env file or create the directory.")

# Prioritize local source files over installed packages
sys.path.insert(0, str(PROJECT_ROOT))

# ============= FUNCTION IMPORTS =============
from src.create_lead_files_for_forecast import (
    setup_logging, test_get_model_files, process_lead_time
)

# ============= CONSTANTS =============
# Month name to number mapping
MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}

# ============= HELPER FUNCTIONS =============
def setup_configuration(year, month):
    """Set up processing configuration including models, directories, and initialization parameters."""
    # Format month as two digits
    month_num = str(MONTH_MAP[month]).zfill(2)
    
    # Create model names string for directory
    model_names_str = "_".join(MODELS)
    
    # Set up directory paths using environment variables
    input_dir = os.path.join(FORECAST_BASE, f"processed_{SEASON_LENGTH}m_seasons")
    output_base = os.path.join(FORECAST_BASE, f"prepared_for_forecast_{SEASON_LENGTH}m_SEASONS")
    output_dir = os.path.join(output_base, f"{year}_{month_num}_{SEASON_LENGTH}m_seasons_{model_names_str}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    return {
        'models': MODELS,
        'input_dir': input_dir,
        'output_dir': output_dir,
        'init_month': month,
        'init_year': year,
        'season_length': SEASON_LENGTH
    }

def validate_configuration(config):
    """
    Validate the configuration parameters.
    
    Args:
        config (dict): Configuration dictionary containing models and directories
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    # Check if models list is not empty
    if not config['models']:
        print("Error: No models specified")
        return False
    else:
        print("INFO: Models list is valid.")
        print(f"Models: {config['models']}")
    
    # Check input directory
    if not os.path.isdir(config['input_dir']):
        print(f"Error: Input directory not found: {config['input_dir']}")
        return False
    else:
        print("INFO: Input directory exists.")
        print(f"Input directory used: {config['input_dir']}")

    # Create output directory if it doesn't exist
    os.makedirs(config['output_dir'], exist_ok=True)
    print("INFO: Output directory is ready.")
    print(f"Output directory: {config['output_dir']}")
    
    return True

# ============= MAIN EXECUTION =============
def main():
    """Main function to control the lead time file creation process for multiple initialization dates."""
    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f'create_lead_files_forecast_processing_{timestamp}.log')
    setup_logging(LOG_DIR)
    logger = logging.getLogger('forecast_processing')
    
    try:
        for year, month in FORECAST_DATES:
            logger.info(f"\nProcessing forecast for {month} {year}")
            
            # Set up configuration for this initialization date
            config = setup_configuration(year, month)
            
            # Log initialization parameters
            logger.info(f"Processing forecast data for initialization: {config['init_year']}-{config['init_month']}")
            logger.info(f"Season length: {config['season_length']} months")
            
            # Test file availability and quality
            logger.info("Testing file availability and quality...")
            model_configs = test_get_model_files(config['input_dir'], config['models'], config['season_length'])
            
            # Debug prints for lead time calculation
            print(f"\nProcessing {month} {year}:")
            print("Available lead times per model:")
            for model, cfg in model_configs.items():
                print(f"  {model}: {cfg['lead_times']} lead times (0-{cfg['lead_times']-1})")
            
            # Find minimum lead time across all models
            min_lead_time = min(cfg['lead_times'] for cfg in model_configs.values())
            print(f"\nMinimum lead times across models: {min_lead_time}")
            print(f"Season length: {SEASON_LENGTH} months")
            
            # Process each lead time up to the minimum common lead time (like hindcast script)
            max_lead_time = min_lead_time - 1
            print(f"Will process lead times: 0-{max_lead_time}\n")
            
            # Process each lead time
            for lead_time in range(max_lead_time + 1):
                logger.info(f"\nProcessing lead time {lead_time}...")
                try:
                    process_lead_time(
                        lead_time=lead_time,
                        model_list=config['models'],
                        input_dir=config['input_dir'],
                        output_dir=config['output_dir'],
                        init_year=year,
                        init_month=month,
                        season_length=config['season_length']
                    )
                    month_num = str(MONTH_MAP[month]).zfill(2)
                    logger.info(f"Successfully created X_lead{lead_time}_{year}-{month_num}.nc")
                except Exception as e:
                    logger.error(f"Error processing lead time {lead_time}: {str(e)}")
                    continue
            
            logger.info(f"Completed processing for {month} {year}\n")
        
        # Print a summary of results
        logger.info("\n" + "=" * 50)
        logger.info("PROCESSING COMPLETE")
        logger.info(f"Forecast dates processed: {', '.join([f'{m} {y}' for y, m in FORECAST_DATES])}")
        logger.info(f"Models processed: {', '.join(MODELS)}")
        logger.info(f"Season length: {SEASON_LENGTH} months")
        logger.info(f"Results saved to: {os.path.dirname(config['output_dir'])}")
        logger.info("=" * 50)
        
        print("\n" + "=" * 50)
        print("PROCESSING COMPLETE")
        print(f"Forecast dates processed: {', '.join([f'{m} {y}' for y, m in FORECAST_DATES])}")
        print(f"Models processed: {', '.join(MODELS)}")
        print(f"Season length: {SEASON_LENGTH} months")
        print(f"Results saved to: {os.path.dirname(config['output_dir'])}")
        print("=" * 50 + "\n")
                
    except Exception as e:
        logger.error(f"Fatal error in processing: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
