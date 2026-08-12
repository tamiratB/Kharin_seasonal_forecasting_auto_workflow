#!/usr/bin/env bash

###############################################################################
# Automated Kharin Seasonal Forecasting Workflow
#
# Description
# -----------
# This script automates the complete seasonal forecasting workflow using the
# Kharin calibration framework. Depending on the configuration, it can produce
# either:
#
#   1. Individual model forecasts
#      - Each model is processed independently from data download through
#        calibration and forecast generation.
#
#   2. Multi-model (ensemble) forecast
#      - All selected models are preprocessed together and subsequently passed
#        to the calibration workflow as a single multi-model ensemble.
#
# Developed: @ICPAC
###############################################################################

set -euo pipefail

WORKDIR="/home/btamirat/oper"

cd "${WORKDIR}"

source /home/btamirat/miniforge3/etc/profile.d/conda.sh

MODELS=(
    "CMCC-SPSv4"
    "COLA-RSMAS-CCSM4"
    "COLA-RSMAS-CESM1"
    "CanSIPS-IC4.CanESM5"
    "CanSIPS-IC4.GEM5p2-NEMO"
    "DWD-GCFS2p2"
    "ECMWF-SEAS51_iri2"
    "GFDL-SPEAR"
    "JMA-CPS3"
    "Meteo_France-System9"
    "NASA-GEOSS2S"
    "NCEP-CFSv2"
    "UKMO-GloSea6-GC2-System604"
)

INIT_MONTH="Aug"
INIT_YEAR="2026"

SEASON_LENGTH=3
LEAD_TIME=2

START_YEAR=1993
END_YEAR=2016

DOWNLOAD_HINDCAST="False"
INDIVIDUAL_MODEL_FORECAST="False"

# individual model forecasts

if [[ "${INDIVIDUAL_MODEL_FORECAST}" == "True" ]]; then

    for MODEL in "${MODELS[@]}"; do

        conda activate gcm_preprocessor_env

        if [[ "${DOWNLOAD_HINDCAST}" == "True" ]]; then
            python gcm_preprocessor/scripts/main_download_c3s_nmme_hindcast.py \
                --models "${MODEL}"
        fi

        python gcm_preprocessor/scripts/main_download_c3s_nmme_forecast.py \
            --models "${MODEL}" \
            --init_month "${INIT_MONTH}" \
            --init_year "${INIT_YEAR}"

        python gcm_preprocessor/scripts/main_make_seasons_from_monthly_hindcast.py \
            --models "${MODEL}" \
            --season_length "${SEASON_LENGTH}"

        python gcm_preprocessor/scripts/main_make_seasons_from_monthly_forecast.py \
            --season_length "${SEASON_LENGTH}"

        python gcm_preprocessor/scripts/main_create_lead_files_for_hindcast.py \
            --models "${MODEL}" \
            --season_length "${SEASON_LENGTH}" \
            --start_year "${START_YEAR}" \
            --end_year "${END_YEAR}"

        python gcm_preprocessor/scripts/main_create_lead_files_for_forecast.py \
            --models "${MODEL}" \
            --season_length "${SEASON_LENGTH}" \
            --init_month "${INIT_MONTH}" \
            --init_year "${INIT_YEAR}"

        conda activate gcm_calibration_env

        bash gcm_calibration/scripts/run_calibration.sh \
            --season_length "${SEASON_LENGTH}" \
            --lead_time "${LEAD_TIME}" \
            --start_year "${START_YEAR}" \
            --end_year "${END_YEAR}" \
            --models "${MODEL}"

        bash gcm_calibration/scripts/run_forecast.sh \
            --season_length "${SEASON_LENGTH}" \
            --lead_time "${LEAD_TIME}" \
            --start_year "${START_YEAR}" \
            --end_year "${END_YEAR}" \
            --init_month "${INIT_MONTH}" \
            --init_year "${INIT_YEAR}" \
            --models "${MODEL}"

    done

else

# multi-model ensemble forecast

    if [[ ${#MODELS[@]} -eq 0 ]]; then
        echo "No models specified."
        exit 1
    fi

    conda activate gcm_preprocessor_env

    JOINED_MODELS=$(IFS=_; echo "${MODELS[*]}")

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

    conda activate gcm_calibration_env

    bash gcm_calibration/scripts/run_calibration.sh \
        --season_length "${SEASON_LENGTH}" \
        --lead_time "${LEAD_TIME}" \
        --start_year "${START_YEAR}" \
        --end_year "${END_YEAR}" \
        --models "${JOINED_MODELS}"

    bash gcm_calibration/scripts/run_forecast.sh \
        --season_length "${SEASON_LENGTH}" \
        --lead_time "${LEAD_TIME}" \
        --start_year "${START_YEAR}" \
        --end_year "${END_YEAR}" \
        --init_month "${INIT_MONTH}" \
        --init_year "${INIT_YEAR}" \
        --models "${JOINED_MODELS}"

fi

echo
echo "============================================================"
echo "Seasonal forecasting workflow completed successfully."
echo "============================================================"
