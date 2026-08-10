#!/bin/bash
# =================================================================
# Calibration Run Script
# =================================================================
#
# DESCRIPTION:
# This script automates the calibration process for multiple climate models.
# Located in the scripts/ directory, it processes each model by:
# 1. Creating model-specific configuration files from templates in config/
# 2. Substituting variables (leadtime, season length, hindcast period)
# 3. Running Python calibration scripts for data processing
#
# ENVIRONMENT VARIABLES (.env):
# This script uses environment variables from the .env file in the project root:
# - PROJECT_ROOT: Base directory of the calibration project
# - DATA_DIR: Directory for input/output data
# - HINDCAST_BASE: Directory containing hindcast data
# - CONFIG_DIR: Directory for configuration files
# - OUTPUT_PREFIX: Prefix for output directory names
#
# USAGE:
# 1. Ensure .env file exists in the project root directory
# 2. Configure the following parameters in the script:
#    - LEADTIME: Forecast lead time (0=none, 1=one month, ..., 11=last month)
#    - LENGTH_OF_SEASON: Number of months in the season
#    - FIRST_HINDCAST_YEAR: Start year of hindcast period
#    - LAST_HINDCAST_YEAR: End year of hindcast period
#    - MODELS: List of models or multi-model combinations to calibrate
# 3. Run from project root: ./scripts/run_calibration_experiment.sh
#    Or from any directory using full path
#
# =================================================================

set -ex  # Exit on error

# Load environment variables from parent directory
if [ -f "$(dirname "$0")/../.env" ]; then
    source "$(dirname "$0")/../.env"
else
    echo "Error: .env file not found in parent directory"
    exit 1
fi

# -------------- Configuration parameters to be set by user in the script --------------
# Processing parameters
# --
MODELS=()
LENGTH_OF_SEASON=""
LEADTIME=""
FIRST_HINDCAST_YEAR=""
LAST_HINDCAST_YEAR=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --season_length)
            LENGTH_OF_SEASON="$2"
            shift 2
            ;;
        --lead_time)
            LEADTIME="$2"
            shift 2
            ;;
        --start_year)
            FIRST_HINDCAST_YEAR="$2"
            shift 2
            ;;
        --end_year)
            LAST_HINDCAST_YEAR="$2"
            shift 2
            ;;
        --models)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                MODELS+=("$1")
                shift
            done
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# sanity check
[[ -z "$LENGTH_OF_SEASON" ]] && { echo "Missing --season_length"; exit 1; }
[[ -z "$LEADTIME" ]] && { echo "Missing --lead_time"; exit 1; }
[[ -z "$FIRST_HINDCAST_YEAR" ]] && { echo "Missing --start_year"; exit 1; }
[[ -z "$LAST_HINDCAST_YEAR" ]] && { echo "Missing --end_year"; exit 1; }
[[ ${#MODELS[@]} -eq 0 ]] && { echo "Missing --models"; exit 1; }
# ---

#OBSERVATION DATASET. Currently defined in the .env file. 
OBS_DATASET="${PROCESSED_OBSERVATIONS_FILE}"

# Output directory configuration
OUTPUT_SUFFIX=""   # Optional: Suffix for all output directories. It is an option that add a tag when doing tests. Leave empty for no suffix.

# Dask configuration for parallel processing. Users should not need to change these parameters.
# Dask Memory limit PER WORKER. Increase it if you run into memory error.
# You may need to increase it if you process many more models, or larger grids. See also the same parameter in run_forecast.sh
DASK_MEMORY_LIMIT="6GB"  

# --------------- Configuration Section End ---------------

# Base directories (using environment variables)
BASE_DIR="$PROJECT_ROOT"
CONFIG_TEMPLATE="${CONFIG_DIR}/config_template_GHA.yml"
OUTPUT_BASE="${DATA_DIR}"

# Global variable for current output directory - initialized before processing models
output_dir=""

# Python environment - uncomment and set if using virtual environment
# PYTHON_ENV="${BASE_DIR}/.venv/bin/activate"

# Function to substitute variables in the config file
substitute_variables() {
  local config_file=$1
  local model_name=$2
  local leadtime=$3
  
  # Set the global output directory name
  local hindcast_period="${FIRST_HINDCAST_YEAR}-${LAST_HINDCAST_YEAR}"
  output_dir="${OUTPUT_PREFIX}_${hindcast_period}_${LENGTH_OF_SEASON}m_lead${leadtime}_${model_name}${OUTPUT_SUFFIX:+_}${OUTPUT_SUFFIX}"
  
  # Detect OS type to use appropriate sed syntax
  if [[ "$(uname)" == "Darwin" ]]; then
    # macOS (BSD) sed requires an extension argument for -i
    # Using an array is safer for commands with arguments
    SED_CMD=(sed -i '')
  else
    # Linux (GNU) sed doesn't use an extension argument
    SED_CMD=(sed -i)
  fi
  
  # Substitute variables using sed
  "${SED_CMD[@]}" "s|__DATA_DIR__|${DATA_DIR}|g" "$config_file"
  "${SED_CMD[@]}" "s|__OUTPUT_DIR__|${output_dir}|g" "$config_file"
  "${SED_CMD[@]}" "s|__OBS_PATH__|${OBS_DATASET}|g" "$config_file"
  "${SED_CMD[@]}" "s|__LEADTIME__|${leadtime}|g" "$config_file"
  "${SED_CMD[@]}" "s|__LENGTH_OF_SEASON__|${LENGTH_OF_SEASON}|g" "$config_file"
  "${SED_CMD[@]}" "s|__FIRST_HINDCAST_YEAR__|${FIRST_HINDCAST_YEAR}|g" "$config_file"
  "${SED_CMD[@]}" "s|__LAST_HINDCAST_YEAR__|${LAST_HINDCAST_YEAR}|g" "$config_file"
  
  # Dask configuration substitutions
  "${SED_CMD[@]}" "s|__DASK_MEMORY_LIMIT__|${DASK_MEMORY_LIMIT}|g" "$config_file"
  
  # Additional substitutions can be added here
  # For example:
  # sed -i '' "s|variable_name_fcst:.*|variable_name_fcst: '${variable_name}'|g" "$config_file"
}


# Function to process a single model
process_model() {
  local model_info=$1
  
  # Get model name (leadtime is defined globally)
  model_name="$model_info"
  
  echo "=============================================="
  echo "Processing model: $model_name (Leadtime: $LEADTIME)"
  echo "=============================================="
  
  # Create directory for this model if it doesn't exist
  model_dir="${BASE_DIR}/config/model_configs/${model_name}"
  mkdir -p "$model_dir"
  
  # Create config file for this model
  config_file="${model_dir}/config_lead${LEADTIME}.yml"
  cp "$CONFIG_TEMPLATE" "$config_file"
  
  echo "Copied template to: $config_file"
  
  # Substitute variables in the config file
  substitute_variables "$config_file" "$model_name" "$LEADTIME"
  
  echo "Substituted variables in config file"
  
  # Run the Python script with this config
  echo "Running Python script for $model_name (Leadtime: $LEADTIME)"
  
  # Virtual environment is already activated at the start of the script

  # Create output directory
  # remove output directory if it exists
  rm -rf "${OUTPUT_BASE}/${output_dir}"
  mkdir -p "${OUTPUT_BASE}/${output_dir}/Data"

  # copy the X_lead?.nc files to calibration output directory for that model and leadtime
  cp "${HINDCAST_BASE}/prep_for_calib_${LENGTH_OF_SEASON}m_SEASONS/prep_for_calib_${FIRST_HINDCAST_YEAR}-${LAST_HINDCAST_YEAR}_${LENGTH_OF_SEASON}m_seasons_${model_name}/X_lead${LEADTIME}.nc" \
     "${OUTPUT_BASE}/${output_dir}/Data/"

  # Run the Python script with retry logic
  cd "${BASE_DIR}"
  
  local max_retries=3
  local retry_count=0
  local success=false
  
  while [ $retry_count -lt $max_retries ] && [ "$success" = false ]; do
    if [ $retry_count -gt 0 ]; then
      echo "Retry attempt $retry_count of $max_retries for $model_name (Leadtime: $LEADTIME)"
      # Add a delay before retrying
      sleep 5
    fi
    
    # Run the Python script and capture exit code
    time s2d-calibrate --calibrate --verbose --config "$config_file" 

    exit_code=$?
    
    # Check for errors in the log file
    log_file="${OUTPUT_BASE}/${output_dir}/Data/logfile.log"
    
    if [ $exit_code -ne 0 ] || grep -q -i "error" "$log_file"; then
      echo "Error detected in run or log file. Exit code: $exit_code"
      retry_count=$((retry_count + 1))
      
      if [ $retry_count -lt $max_retries ]; then
        echo "Will retry..."
        # mv the log file to a backup
        mv "${OUTPUT_BASE}/${output_dir}/Data/logfile.log" "${OUTPUT_BASE}/${output_dir}/Data/logfile.log.$(date +%Y%m%d%H%M%S)"
      else
        echo "Maximum retries reached. Giving up on $model_name (Leadtime: $LEADTIME)"
        return 1  # Return error code to indicate failure
      fi
    else
      success=true
      echo "Successfully processed $model_name (Leadtime: $LEADTIME)"
    fi
  done
  
  if [ "$success" = true ]; then
    echo "Finished processing $model_name (Leadtime: $LEADTIME)"
    echo ""
    return 0
  else
    echo "Failed to process $model_name (Leadtime: $LEADTIME) after $max_retries attempts"
    echo ""
    return 1
  fi
}

# Main execution
main() {
  # Create necessary directories
  mkdir -p "${BASE_DIR}/config/models"
  
  echo "Starting batch processing of models"
  echo "====================================" 
  
  # Process each model with error handling
  local failed_models=()
  
  for model_info in "${MODELS[@]}"; do
    if ! process_model "$model_info"; then
      echo "WARNING: Failed to process $model_info after multiple attempts"
      failed_models+=("$model_info")
      # Continue with other models
    fi
  done
  
  # Report on any failed models
  if [ ${#failed_models[@]} -gt 0 ]; then
    echo "\nThe following models failed to process:"
    for failed in "${failed_models[@]}"; do
      echo "  - $failed"
    done
    echo "\nCheck logs for details."
    return 1
  fi
  
  echo "All models processed successfully!"
}

# Run the main function
main
