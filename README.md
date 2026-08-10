# Automated Kharin Seasonal Forecasting Workflow

This repository provides an automated workflow for the **Kharin Seasonal Forecasting Tool**. It streamlines the complete seasonal forecast production process by automating:

- Hindcast and forecast data download
- Seasonal aggregation
- Lead-time dataset preparation
- Calibration
- Forecast generation

The workflow is designed to reduce manual intervention and improve the reproducibility and operational efficiency of seasonal forecast production.

> **Note**
>
> This repository **does not replace** the original Kharin forecasting tool. It provides modified scripts and an automation wrapper around the original workflow.
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

Before using this workflow, make sure you have:

- The original **gcm_preprocessor** repository.
- The original **gcm_calibration** repository.
- Conda environments:
  - `gcm_preprocessor_env`
  - `gcm_calibration_env`

The expected directory structure is:

```
working_directory/
│
├── auto_kharin.sh
├── gcm_preprocessor/
├── gcm_calibration/
```

---

# Installation

## Step 1. Replace the modified scripts

This repository contains updated versions of several scripts used by the original workflow.

### Copy the preprocessing scripts

Copy all scripts from

```
preprocessor_scripts/
```

into

```
gcm_preprocessor/scripts/
```

replacing the original files.

---

### Copy the calibration scripts

Copy all scripts from

```
calibration_scripts/
```

into

```
gcm_calibration/scripts/
```

replacing the original files.

---

## Step 2. Place the automation script

Copy

```
auto_kharin.sh
```

into the directory that contains both repositories:

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

and modify the user configuration section.

Example:

```bash
MODELS=(
    "DWD-GCFS2p2"
    "ECMWF-SEAS51"
    "GFDL-SPEAR"
)

INIT_MONTH="May"
INIT_YEAR="2026"

SEASON_LENGTH=4
LEAD_TIME=1

START_YEAR=1993
END_YEAR=2016

DOWNLOAD_HINDCAST="False"
```

### Configuration Parameters

| Variable | Description |
|-----------|-------------|
| `MODELS` | List of forecasting models to process |
| `INIT_MONTH` | Forecast initialization month |
| `INIT_YEAR` | Forecast initialization year |
| `SEASON_LENGTH` | Number of months in the target season |
| `LEAD_TIME` | Forecast lead time |
| `START_YEAR` | First hindcast year |
| `END_YEAR` | Last hindcast year |
| `DOWNLOAD_HINDCAST` | Set to `"True"` to download hindcasts; otherwise previously downloaded data will be used |

---

# Running the Workflow

Execute

```bash
bash auto_kharin.sh
```

The workflow automatically performs the following steps:

1. Activate the preprocessing environment.
2. Download hindcasts (optional).
3. Download forecasts.
4. Create seasonal hindcast datasets.
5. Create seasonal forecast datasets.
6. Generate lead-specific hindcast files.
7. Generate lead-specific forecast files.
8. Activate the calibration environment.
9. Run calibration.
10. Produce calibrated seasonal forecasts.

---

# Notes

- Hindcast downloading is optional. Once the hindcast datasets have been downloaded, set

```bash
DOWNLOAD_HINDCAST="False"
```

to skip this step in future runs.

- The workflow assumes the directory structure described above. If your installation differs, update the paths in `auto_kharin.sh` accordingly.

---

# Citation

If you use this workflow in your operational forecasting or research, please cite the original Kharin forecasting framework in addition to this repository.

---

# Prepared

IGAD Climate Prediction and Applications Centre (ICPAC)
