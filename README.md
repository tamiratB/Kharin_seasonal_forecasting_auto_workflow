# Automated Kharin Seasonal Forecasting Workflow

This repository provides an automated workflow for the **Kharin Seasonal Forecasting Tool**, simplifying the complete seasonal forecast production process from data acquisition to calibrated forecast generation.

The workflow automates:

- Download of C3S/NMME hindcast and forecast data
- Seasonal aggregation of monthly forecasts
- Lead-time dataset preparation
- Model calibration
- Calibrated forecast generation
- Individual model or multi-model ensemble forecasting

The objective is to minimize manual intervention, improve reproducibility, and increase the efficiency of operational seasonal forecast production.

> **Note**
>
> This repository **does not replace** the original Kharin forecasting tool. Instead, it provides:
>
> - Modified preprocessing and calibration scripts
> - An automation wrapper (`auto_kharin.sh`) for running the complete workflow
>
> The original Kharin forecasting tool is available at:
>
> https://gitlab.com/climate-prediction-public/gcm_preprocessor_ICPAC

---

# Repository Structure

```
.
├── auto_kharin.sh
├── calibration_scripts/
│   ├── run_calibration.sh
│   ├── run_forecast.sh
│   └── ...
├── preprocessor_scripts/
│   ├── main_download_c3s_nmme_forecast.py
│   ├── main_create_lead_files_for_forecast.py
│   └── ...
└── README.md
```

---

# Prerequisites

Before using this workflow, ensure that you have:

- The original **gcm_preprocessor** repository.
- The original **gcm_calibration** repository.
- Conda environments:

```
gcm_preprocessor_env
gcm_calibration_env
```

The recommended directory structure is

```
working_directory/
│
├── auto_kharin.sh
├── gcm_preprocessor/
└── gcm_calibration/
```

---

# Installation

## Step 1. Replace the modified scripts

Copy the modified preprocessing scripts

```
preprocessor_scripts/
```

into

```
gcm_preprocessor/scripts/
```

replacing the existing scripts.

Next, copy the modified calibration scripts

```
calibration_scripts/
```

into

```
gcm_calibration/scripts/
```

again replacing the existing scripts.

---

## Step 2. Place the automation script

Copy

```
auto_kharin.sh
```

into the parent directory containing both repositories.

The final directory structure should look like

```
working_directory/
│
├── auto_kharin.sh
├── gcm_preprocessor/
└── gcm_calibration/
```

---

# Configure the Workflow

Open

```
auto_kharin.sh
```

and modify the **User Configuration** section.

Example:

```bash
MODELS=(
    "ECMWF-SEAS51_iri2"
    "NCEP-CFSv2"
    "GFDL-SPEAR"
)

INIT_MONTH="Aug"
INIT_YEAR="2026"

SEASON_LENGTH=3
LEAD_TIME=2

START_YEAR=1993
END_YEAR=2016

DOWNLOAD_HINDCAST="False"

INDIVIDUAL_MODEL_FORECAST="False"
```

---

## Configuration Parameters

| Variable | Description |
|-----------|-------------|
| `MODELS` | List of forecasting models to process |
| `INIT_MONTH` | Forecast initialization month |
| `INIT_YEAR` | Forecast initialization year |
| `SEASON_LENGTH` | Number of months in the target season |
| `LEAD_TIME` | Forecast lead time |
| `START_YEAR` | First hindcast year |
| `END_YEAR` | Last hindcast year |
| `DOWNLOAD_HINDCAST` | Set to `"True"` to download hindcasts. Set to `"False"` to use existing datasets. |
| `INDIVIDUAL_MODEL_FORECAST` | `"True"` processes each model independently. `"False"` produces a calibrated multi-model ensemble forecast. |

---

# Forecast Modes

The workflow supports two execution modes.

## 1. Individual Model Forecast

Set

```bash
INDIVIDUAL_MODEL_FORECAST="True"
```

Each model is processed independently through the entire workflow:

- Download
- Seasonal aggregation
- Lead file creation
- Calibration
- Forecast generation

This mode is useful for evaluating or generating calibrated forecasts for individual models.

---

## 2. Multi-model Ensemble Forecast (Recommended)

Set

```bash
INDIVIDUAL_MODEL_FORECAST="False"
```

The workflow processes all selected models together and generates a calibrated multi-model ensemble forecast.

---

# Running the Workflow

Execute

```bash
bash auto_kharin.sh
```

The workflow automatically performs the following steps.

1. Activate the preprocessing environment.
2. Download hindcasts (optional).
3. Download forecast data.
4. Generate seasonal hindcast datasets.
5. Generate seasonal forecast datasets.
6. Create lead-specific hindcast datasets.
7. Create lead-specific forecast datasets.
8. Activate the calibration environment.
9. Run calibration.
10. Generate calibrated seasonal forecasts.

---

# Output

The calibrated forecasts are written to

```
gcm_calibration/data/calibrated_forecasts_for_ICPAC/
```

---

# Log Files

The workflow generates log files throughout preprocessing and calibration.

If one or more models are missing from the final forecasts, inspect the log files for errors or warnings.

Logs are located in

```
gcm_preprocessor/logs/
```

These logs can help identify issues such as

- failed data downloads
- unavailable model data
- preprocessing failures

---

# Notes

- Hindcast downloading is usually required only once. After the hindcasts have been downloaded successfully, set

```bash
DOWNLOAD_HINDCAST="False"
```

to skip downloading in future runs.

- The workflow assumes the directory structure described above. If your installation differs, update the paths in `auto_kharin.sh` accordingly.

- Individual model mode is primarily intended for model evaluation and diagnostics.

- Multi-model ensemble mode is recommended for operational seasonal forecasting.

---

# Citation

If you use this workflow in operational forecasting or research, please cite the original Kharin forecasting framework in addition to this repository.

---

# Prepared By:

IGAD Climate Prediction and Applications Centre (ICPAC)
