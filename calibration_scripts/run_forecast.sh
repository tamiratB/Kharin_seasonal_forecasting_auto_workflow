#!/bin/bash
# =================================================================
# Forecast Run Script
# =================================================================
#
# DESCRIPTION:
# This script automates the forecast process for multiple climate models.
# Located in the scripts/ directory, it processes each model by:
# 1. Creating model-specific configuration files from templates in config/
# 2. Substituting variables (leadtime, season length, hindcast period)
# 3. Running Python forecast scripts for data processing
#
# ENVIRONMENT VARIABLES (.env):
# This script uses environment variables from the .env file in the project root:
# - PROJECT_ROOT: Base directory of the calibration project
# - DATA_DIR: Directory for input/output data
# - FORECAST_BASE: Directory containing forecast data to be calibrated 
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
#    - MODELS: List of models or multi-model combinations
# 3. Run from project root: ./scripts/run_forecast_experiment.sh
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
init_month=""
init_year=""

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
        --init_month)
            init_month="$2"
            shift 2
            ;;
        --init_year)
            init_year="$2"
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

declare -A MONTHS=([Jan]=01 [Feb]=02 [Mar]=03 [Apr]=04 [May]=05 [Jun]=06 [Jul]=07 [Aug]=08 [Sep]=09 [Oct]=10 [Nov]=11 [Dec]=12)
FORECAST_INITIALIZATION_DATES=(
  "${init_year}/${MONTHS[$init_month]}"
  )

# sanity check
[[ -z "$LENGTH_OF_SEASON" ]] && { echo "Missing --season_length"; exit 1; }
[[ -z "$LEADTIME" ]] && { echo "Missing --lead_time"; exit 1; }
[[ -z "$FIRST_HINDCAST_YEAR" ]] && { echo "Missing --start_year"; exit 1; }
[[ -z "$LAST_HINDCAST_YEAR" ]] && { echo "Missing --end_year"; exit 1; }
[[ -z "$init_month" ]] && { echo "Missing --init_month"; exit 1; }
[[ -z "$init_year" ]] && { echo "Missing --init_year"; exit 1; }
[[ ${#MODELS[@]} -eq 0 ]] && { echo "Missing --models"; exit 1; }
# ---

### Observation dataset to use. Currently defined in the .env file. 

OBS_DATASET="${PROCESSED_OBSERVATIONS_FILE}"

# Output directory configuration
OUTPUT_SUFFIX=""   # Optional: Suffix for all output directories. It is an option that add a tag when doing tests. Leave empty for no suffix.

# Dask configuration for parallel processing. Users should not need to change these parameters.
# Dask Memory limit PER WORKER. Increase it if you run into memory error. You may need to increase it if you process many more models, or larger grids.
DASK_MEMORY_LIMIT="6GB"  

# --------------- Configuration Section End ---------------

# Base directories (using environment variables)
BASE_DIR="$PROJECT_ROOT"
SCRIPT_DIR="$BASE_DIR/scripts"
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
  local fcst_initial_yr=$4
  local fcst_initial_mth=$5
  
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
  
  # Substitute variables in the config file
  "${SED_CMD[@]}" "s|__DATA_DIR__|${DATA_DIR}|g" "$config_file"
  "${SED_CMD[@]}" "s|__OUTPUT_DIR__|${output_dir}|g" "$config_file"
  "${SED_CMD[@]}" "s|__OBS_PATH__|${OBS_DATASET}|g" "$config_file"
  "${SED_CMD[@]}" "s|__MODEL_NAME__|${model_name}|g" "$config_file"
  "${SED_CMD[@]}" "s|__LEADTIME__|${leadtime}|g" "$config_file"
  "${SED_CMD[@]}" "s|__LENGTH_OF_SEASON__|${LENGTH_OF_SEASON}|g" "$config_file"
  "${SED_CMD[@]}" "s|__FIRST_HINDCAST_YEAR__|${FIRST_HINDCAST_YEAR}|g" "$config_file"
  "${SED_CMD[@]}" "s|__LAST_HINDCAST_YEAR__|${LAST_HINDCAST_YEAR}|g" "$config_file"
  "${SED_CMD[@]}" "s|__FCST_INITIAL_YR__|${fcst_initial_yr}|g" "$config_file"
  "${SED_CMD[@]}" "s|__FCST_INITIAL_MTH__|${fcst_initial_mth}|g" "$config_file"
  
  # Dask configuration substitutions
  "${SED_CMD[@]}" "s|__DASK_MEMORY_LIMIT__|${DASK_MEMORY_LIMIT}|g" "$config_file"
  
  # Additional substitutions can be added here
  # For example:
  # sed -i '' "s|variable_name_fcst:.*|variable_name_fcst: '${variable_name}'|g" "$config_file"
}


# Function to process a single model for a specific forecast date
process_model() {
  local model_name=$1
  local fcst_initial_yr=$2
  local fcst_initial_mth=$3
  
  echo "=============================================="
  echo "Processing model: $model_name (Leadtime: $LEADTIME)"
  echo "Forecast date: $fcst_initial_yr-$fcst_initial_mth"
  echo "=============================================="
  
  # Create directory for this model if it doesn't exist
  model_dir="${BASE_DIR}/config/model_configs/${model_name}"
  mkdir -p "$model_dir"
  
  # Create config file for this model and forecast date
  config_file="${model_dir}/config_lead${LEADTIME}_${fcst_initial_yr}_${fcst_initial_mth}.yml"
  cp "$CONFIG_TEMPLATE" "$config_file"
  
  echo "Copied template to: $config_file"
  
  # Substitute variables in the config file
  substitute_variables "$config_file" "$model_name" "$LEADTIME" "$fcst_initial_yr" "$fcst_initial_mth"
  
  echo "Substituted variables in config file"
  
  # Run the Python script with this config
  echo "Running Python script for $model_name (Leadtime: $LEADTIME, Date: $fcst_initial_yr-$fcst_initial_mth)"
  
  # Virtual environment is already activated at the start of the script

  # Set the output directory name
  output_dir="Precipitation_CHIRPS_GHA_${FIRST_HINDCAST_YEAR}-${LAST_HINDCAST_YEAR}_${LENGTH_OF_SEASON}m_lead${LEADTIME}_${model_name}"

  # Check if the output directory exists
  if [ ! -d "${OUTPUT_BASE}/${output_dir}" ]; then
    echo "ERROR: Output directory ${OUTPUT_BASE}/${output_dir} does not exist"
    echo "Please ensure the calibration has been run for this model and leadtime first"
    return 1
  fi
  
  # Check if the Data subdirectory exists
  if [ ! -d "${OUTPUT_BASE}/${output_dir}/Data" ]; then
    echo "ERROR: Data directory ${OUTPUT_BASE}/${output_dir}/Data does not exist"
    echo "Please ensure the calibration has been run for this model and leadtime first"
    return 1
  fi

  # copy the forecast X_lead?.nc files to calibration output directory for that model and leadtime
  cp "${FORECAST_BASE}/prepared_for_forecast_${LENGTH_OF_SEASON}m_SEASONS/${fcst_initial_yr}_${fcst_initial_mth}_${LENGTH_OF_SEASON}m_seasons_${model_name}/X_lead${LEADTIME}_${fcst_initial_yr}-${fcst_initial_mth}.nc" \
     "${OUTPUT_BASE}/${output_dir}/Data/X_lead${LEADTIME}_${fcst_initial_yr}-${fcst_initial_mth}.nc"
   
  # Run the Python script
  cd "${BASE_DIR}"
  time s2d-calibrate --forecast --verbose --config "$config_file"
  echo "Finished processing $model_name (Leadtime: $LEADTIME)"
  echo ""
}

# Function to check for errors in log file
check_log_errors() {
  local log_file="$1"
  local model_name="$2"
  
  if [ -f "$log_file" ]; then
    if grep -i "error" "$log_file" > /dev/null; then
      echo "Found errors in log file for model $model_name:"
      grep -i "error" "$log_file" | while read -r line; do
        echo "$model_name: $line" >> "${BASE_DIR}/error_summary.log"
      done
    fi
  fi
}

# Main execution
main() {
  # Create necessary directories
  mkdir -p "${BASE_DIR}/config/models"
  
  # Create temporary files for summaries
  error_temp="${BASE_DIR}/error_summary_temp.log"
  touch "$error_temp"
  
  echo "Starting batch processing of forecasts"
  echo "===================================="
  
  # Check if MODELS array is empty
  if [ ${#MODELS[@]} -eq 0 ]; then
    echo "⚠️  WARNING: No models specified in the MODELS array! ⚠️"
    echo "Please uncomment or add at least one model in the MODELS array in the script."
    echo "Processing will continue but no model forecasts will be generated."
    echo "===================================="
  fi
  
  # Process each date and model combination
  for date_str in "${FORECAST_INITIALIZATION_DATES[@]}"; do
    # Split the date string into year and month
    fcst_initial_yr=$(echo "$date_str" | cut -d'/' -f1)
    fcst_initial_mth=$(echo "$date_str" | cut -d'/' -f2)
    
    echo "Processing forecast date: $fcst_initial_yr-$fcst_initial_mth"
    
    # Process each model for this date
    for model_info in "${MODELS[@]}"; do
      process_model "$model_info" "$fcst_initial_yr" "$fcst_initial_mth"
      
      # After processing, check for errors
      output_dir="Precipitation_CHIRPS_GHA_${FIRST_HINDCAST_YEAR}-${LAST_HINDCAST_YEAR}_${LENGTH_OF_SEASON}m_lead${LEADTIME}_${model_info}"
      
      # Redirect error outputs to temporary files
      check_log_errors "${output_dir}/logfile.log" "$model_info" >> "$error_temp"
      
      # Run post-processing to transform forecast files into ICPAC content and format (calibrated)
      python "$SCRIPT_DIR/TOOLS/postprocess_forecasts_for_ICPAC.py" \
        --init_year "$fcst_initial_yr" \
        --init_month "$fcst_initial_mth" \
        --lead "$LEADTIME" \
        --model "$model_info" \
        --hindcast_start "$FIRST_HINDCAST_YEAR" \
        --hindcast_end "$LAST_HINDCAST_YEAR" \
        --calib "seasonally" \
        --process_ensemble_mean \
        --process_percent_anomaly \
        --input_dir "${OUTPUT_BASE}/${output_dir}/Data" \
        --output_dir "${CALIBRATED_FORECAST_BASE}"
      
      # Run post-processing for uncalibrated data
      python "$SCRIPT_DIR/TOOLS/postprocess_forecasts_for_ICPAC.py" \
        --init_year "$fcst_initial_yr" \
        --init_month "$fcst_initial_mth" \
        --lead "$LEADTIME" \
        --model "$model_info" \
        --hindcast_start "$FIRST_HINDCAST_YEAR" \
        --hindcast_end "$LAST_HINDCAST_YEAR" \
        --calib "uncalibrated" \
        --process_ensemble_mean \
        --process_percent_anomaly \
        --input_dir "${OUTPUT_BASE}/${output_dir}/Data" \
        --output_dir "${CALIBRATED_FORECAST_BASE}"
      
      # Check for errors in post-processing
      if [ $? -ne 0 ]; then
        echo "Error: Post-processing failed for $model_info, date $fcst_initial_yr-$fcst_initial_mth" >> "$error_temp"
      fi

    done
  done
  
  # Only create summary files if there are actual issues
  has_errors=false
  
  if [ -s "$error_temp" ]; then
    has_errors=true
    echo "Error Summary - $(date)" > "${BASE_DIR}/error_summary.log"
    cat "$error_temp" >> "${BASE_DIR}/error_summary.log"
  fi
  
  # Display warning banner only if there were actual issues
  if $has_errors; then
    echo ""
    echo "⚠️  WARNING: Issues were detected during processing ⚠️"
    echo "===================================================="
    echo "Errors found in log files:"
    cat "${BASE_DIR}/error_summary.log"
    echo "===================================================="
  fi
  
  # Clean up temporary files
  rm -f "$error_temp"
  
  echo "All models processing completed!"
}

# Run the main function
main
