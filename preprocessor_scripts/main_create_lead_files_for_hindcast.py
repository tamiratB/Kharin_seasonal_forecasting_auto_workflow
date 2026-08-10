#!/usr/bin/env python3
"""
Main script to create lead time files for calibration from hindcast data.

This script configures and initiates the process of creating lead time-specific NetCDF files
from processed hindcast data for a specific year range. These files are used for calibration
of seasonal hindcasts.

Module Dependencies:
- src.create_lead_files_for_hindcast: Core module that provides the functions for processing
  lead time files (setup_logging, test_get_model_files, process_lead_time)

Data Dependency Tree:
1. Raw downloaded hindcast data (from main_download_c3s_nmme_hindcast.py)
2. Processed seasonal hindcast data (from main_make_seasons_from_monthly_hindcast.py)
3. Lead time files for calibration (this script)

The script uses environment variables from the .env file to determine paths:
- PROJECT_ROOT: Root directory of the project
- HINDCAST_BASE: Base directory for hindcast data
- LOG_DIR: Directory for log files (defaults to PROJECT_ROOT/logs)

Configuration to be set by the user:
- MODELS: List of models to process
- YEAR_start and YEAR_end: Year range for hindcast data
- SEASON_LENGTH: Number of months in the seasonal average

Output:
- Lead time-specific NetCDF files in HINDCAST_BASE/prep_for_calib_{SEASON_LENGTH}m_SEASONS/
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
parser.add_argument("--start_year", default=None, help="Hindcast start year (e.g., 1981)")
parser.add_argument("--end_year", default=None, help="Hindcast end year (e.g., 2020)")
args = parser.parse_args()

MODELS = args.models
SEASON_LENGTH = int(args.season_length)
YEAR_start = int(args.start_year)
YEAR_end = int(args.end_year)
# ---

# ============= IMPORTS =============
# Standard library imports
import os
import sys
import logging
from datetime import datetime
from typing import List
from dotenv import load_dotenv

# ============= ENVIRONMENT SETUP =============
# Load environment variables
load_dotenv()

# Get environment variables with defaults
PROJECT_ROOT = os.getenv('PROJECT_ROOT', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  
HINDCAST_BASE = os.getenv('HINDCAST_BASE', os.path.join(PROJECT_ROOT, 'data', 'downloaded_hindcasts'))
LOG_DIR = os.getenv('LOG_DIR', os.path.join(PROJECT_ROOT, 'logs'))

# Check for required environment variables
if not os.path.exists(HINDCAST_BASE):
    print(f"WARNING: HINDCAST_BASE directory does not exist: {HINDCAST_BASE}")
    print("Please check your .env file or create the directory.")

# Add the src directory to the Python path
sys.path.append(str(PROJECT_ROOT))

# ============= FUNCTION IMPORTS =============
from src.create_lead_files_for_hindcast import (
    setup_logging, test_get_model_files, process_lead_time
)

# ============= CONSTANTS =============
# Month name to number mapping (if needed)
MONTH_MAP = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
    'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}

# ============= PATH CONFIGURATION =============
# Create model names string for directory
model_dir_suffix = '_'.join(MODELS)

# Set up directory paths using environment variables
INPUT_DIR = os.path.join(HINDCAST_BASE, f"processed_{SEASON_LENGTH}m_seasons")
OUTPUT_DIR = os.path.join(HINDCAST_BASE, 
                        f"prep_for_calib_{SEASON_LENGTH}m_SEASONS", 
                        f"prep_for_calib_{YEAR_start}-{YEAR_end}_{SEASON_LENGTH}m_seasons_{model_dir_suffix}")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============= HELPER FUNCTIONS =============
def setup_configuration():
    """Set up processing configuration including models, year range, and directories."""
    return {
        'models': MODELS,
        'year_start': YEAR_start,
        'year_end': YEAR_end,
        'input_dir': INPUT_DIR,
        'output_dir': OUTPUT_DIR
    }

def validate_configuration(config):
    """
    Validate the configuration parameters.
    
    Args:
        config (dict): Configuration dictionary containing models, year range, and directories
    
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
    
    # Verify year range
    if not (1980 <= config['year_start'] <= config['year_end'] <= 2100):
        print("Error: Invalid year range")
        print(f"The request year range is: {config['year_start']} to {config['year_end']}")
        return False
    else:
        print("INFO: Year range is valid.")
        print(f"The request year range is: {config['year_start']} to {config['year_end']}")

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
    """Main function to control the lead time file creation process."""
    # Set up logging
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f'create_lead_files_hindcast_processing_{timestamp}.log')
    setup_logging(LOG_DIR)  # Initialize logging system
    logger = logging.getLogger('hindcast_processing')
    
    # Define models to process
    models = MODELS
    
    try:
        # Test file availability and quality
        logger.info("Testing file availability and quality...")
        model_configs = test_get_model_files(INPUT_DIR, models)
        
        # Find common lead times and year range across models
        min_lead_time = min(cfg['lead_times'] for cfg in model_configs.values())
        logger.info(f"Using minimum common lead time: {min_lead_time}")
        
        # Find most restrictive year range considering both model data and configuration
        max_start_year = max(max(YEAR_start, cfg['year_start']) for cfg in model_configs.values())
        min_end_year = min(min(YEAR_end, cfg['year_end']) for cfg in model_configs.values())
        
        if max_start_year > min_end_year:
            logger.error(f"No common year range available: {max_start_year}-{min_end_year}")
            return
        
        logger.info(f"Using year range {max_start_year}-{min_end_year} based on model limitations and configuration")
        
        # Ensure the output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Process each lead time up to the minimum common lead time
        for lead_time in range(min_lead_time):
            logger.info(f"\nProcessing lead time {lead_time}")
            try:
                process_lead_time(
                    lead_time=lead_time,
                    model_list=models,
                    year_start=max_start_year,
                    year_end=min_end_year,
                    input_dir=INPUT_DIR,
                    output_dir=OUTPUT_DIR
                )
                logger.info(f"Successfully created X_lead{lead_time}.nc")
            except Exception as e:
                logger.error(f"Error processing lead time {lead_time}: {str(e)}")
                raise
        
        # Print a summary of results
        logger.info("\n" + "=" * 50)
        logger.info("PROCESSING COMPLETE")
        logger.info(f"Results saved to: {OUTPUT_DIR}")
        logger.info(f"Year range: {max_start_year}-{min_end_year}")
        logger.info(f"Models processed: {', '.join(models)}")
        logger.info(f"Lead times processed: 0-{min_lead_time-1}")
        logger.info("=" * 50)
        
        print("\n" + "=" * 50)
        print("PROCESSING COMPLETE")
        print(f"Results saved to: {OUTPUT_DIR}")
        print(f"Year range: {max_start_year}-{min_end_year}")
        print(f"Models processed: {', '.join(models)}")
        print(f"Lead times processed: 0-{min_lead_time-1}")
        print("=" * 50 + "\n")
                
    except Exception as e:
        logger.error(f"Fatal error in processing: {str(e)}")
        raise

if __name__ == '__main__':
    main()
