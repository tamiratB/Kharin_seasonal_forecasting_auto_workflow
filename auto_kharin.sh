#!/usr/bin/env bash

###############################################################################
# Automated Kharin Seasonal Forecasting Workflow
#
# Description
# -----------
# This script orchestrates the complete workflow for producing seasonal
# forecasts using the Kharin calibration framework. It automates data
# acquisition, preprocessing, seasonal aggregation, lead-time preparation,
# calibration, and forecast generation with minimal user intervention.
#
# Workflow
# --------
# 1. Activate the gcm_preprocessor environment.
# 2. Download hindcast data from C3S/NMME. You can turn ON/OFF this option
# 3. Download the latest seasonal forecast.
# 4. Aggregate monthly hindcasts into seasonal means.
# 5. Aggregate monthly forecasts into seasonal means.
# 6. Create lead-specific hindcast datasets.
# 7. Create lead-specific forecast datasets.
# 8. Activate the gcm_calibration environment.
# 9. Run calibration for the selected models.
# 10. Generate calibrated seasonal forecasts.
#
# User Configuration
# ------------------
# models             List of forecasting models to process.
# init_month         Forecast initialization month (e.g., Jan, Feb, ..., Dec).
# init_year          Forecast initialization year.
# season_length      Number of months in the target season.
# lead_time          Forecast lead time (1 = first target season, etc.).
# start_year         First hindcast year used for calibration.
# end_year           Last hindcast year used for calibration.
# download_hindcast  Set to "True" to download hindcasts, or "False" to use
#                    previously downloaded datasets.
#
# Requirements
# ------------
# - Conda environments:
#     * gcm_preprocessor_env
#     * gcm_calibration_env
# - The gcm_preprocessor and gcm_calibration repositories must be available
#   under the working directory.
#   Check - https://gitlab.com/climate-prediction-public/gcm_preprocessor_ICPAC
#
# Usage
# -----
# Modify the configuration variables below and execute:
#
#     bash auto_kharin.sh or ./auto_kharin.sh
#
# Developed : @ICPAC
# Date   : August 2026
###############################################################################
set -euo pipefail

###############################################################################
# Environment
###############################################################################

WORKDIR="/home/btamirat/oper"

cd "${WORKDIR}"

source /home/btamirat/miniforge3/etc/profile.d/conda.sh

###############################################################################
# User Configuration
###############################################################################
# one model per line and no need for comma in between
MODELS=(
    "DWD-GCFS2p2"
    "ECMWF-SEAS51_iri2"
    "GFDL-SPEAR"
)

INIT_MONTH="May"
INIT_YEAR="2026"

SEASON_LENGTH=4
LEAD_TIME=1

# Common hindcast period for all models
START_YEAR=1993
END_YEAR=2016

# Set to "True" to download hindcasts
DOWNLOAD_HINDCAST="False"

###############################################################################
# Data Download and Preprocessing
###############################################################################

conda activate gcm_preprocessor_env

if [[ "${DOWNLOAD_HINDCAST}" == "True" ]]; then
    python gcm_preprocessor/scripts/main_download_c3s_nmme_hindcast.py \
        --models "${MODELS[@]}"
fi

python gcm_preprocessor/scripts/main_download_c3s_nmme_forecast.py \
    --models "${MODELS[@]}" \
    --init_month "${INIT_MONTH}" \
    --init_year "${INIT_YEAR}"

python gcm_preprocessor/scripts/main_make_seasons_from_monthly_hindcast.py \
    --models "${MODELS[@]}" \
    --season_length "${SEASON_LENGTH}"

python gcm_preprocessor/scripts/main_make_seasons_from_monthly_forecast.py \
    --season_length "${SEASON_LENGTH}"

python gcm_preprocessor/scripts/main_create_lead_files_for_hindcast.py \
    --models "${MODELS[@]}" \
    --season_length "${SEASON_LENGTH}" \
    --start_year "${START_YEAR}" \
    --end_year "${END_YEAR}"

python gcm_preprocessor/scripts/main_create_lead_files_for_forecast.py \
    --models "${MODELS[@]}" \
    --season_length "${SEASON_LENGTH}" \
    --init_month "${INIT_MONTH}" \
    --init_year "${INIT_YEAR}"

###############################################################################
# Calibration and Forecast Generation
###############################################################################

conda activate gcm_calibration_env

bash gcm_calibration/scripts/run_calibration.sh \
    --season_length "${SEASON_LENGTH}" \
    --lead_time "${LEAD_TIME}" \
    --start_year "${START_YEAR}" \
    --end_year "${END_YEAR}" \
    --models "${MODELS[@]}"

bash gcm_calibration/scripts/run_forecast.sh \
    --season_length "${SEASON_LENGTH}" \
    --lead_time "${LEAD_TIME}" \
    --start_year "${START_YEAR}" \
    --end_year "${END_YEAR}" \
    --init_month "${INIT_MONTH}" \
    --init_year "${INIT_YEAR}" \
    --models "${MODELS[@]}"

echo "======================================================"
echo "Seasonal forecasting workflow completed successfully."
echo "======================================================"
