# RigLog 🩸💪

![RigLog Logo](assets/branding/logo_full.png)

> One app. Multiple health signals. Clearer decisions.

RigLog is a personal health analytics desktop application built in Python,
designed to turn raw health data into actionable insights.

It currently supports glucose and activity analysis, with future modules planned for nutrition and training.

The goal is to combine multiple health data sources into a single application for analysis and visualisation, including:

- Glucose data
- Activity data
- Workout data
- Nutrition data

## Features

- Import glucose data from Diabetes:M (CSV)
- Interactive glucose dashboard with:
  - Ambulatory Glucose Profile (AGP)
  - Time-in-range metrics
  - Clickable glucose range filters
  - Meal-event drilldown chart
  - Unified active-filter state display
  - Daily average trends
  - Meal-event glucose distribution
- Glucose variability metrics:
  - Mean, SD, CV, GMI
- Insulin dose effectiveness analysis:
  - Standard vs actual carb ratios
  - Outcome-based recommendations
- Time-based improvement tracking (7-day comparison)
- Editable fields:
  - Carbohydrates (g)
  - Humalog (u)
  - Tresiba (u)
  - Notes
- Export professional PDF reports with charts
- Activity tracking via Fitbit integration:
  - Daily step import and sync
  - 7-day rolling averages
  - Goal adherence tracking (10k steps)
  - Streak and trend analysis
  - Daily and weekly charts with hover insights
- Unified home dashboard:
  - Live summary cards for glucose and activity
  - Quick navigation between modules

## Why RigLog?

RigLog was built to centralise and analyse personal health data,
starting with glucose monitoring.

The goal is to move beyond raw readings and provide:

- actionable insights
- trend analysis
- decision support for insulin dosing

Future modules will expand into nutrition, training, and cross-metric insights.

## Tech Stack

- Python
- PySide6 (desktop UI)
- Pandas (data analysis)
- Matplotlib (visualisation)
- SQLite (local database)
- ReportLab (PDF export)

## Architecture Overview

High-level flow of data and responsibilities across UI, service, and data layers.

![Architecture Diagram](assets/docs/architecture.png)

<details>

<summary>View Mermaid source</summary>

```mermaid
flowchart TD
    main["app/main.py"]
    window["app/ui/main_window.py"]

    subgraph ui["app/ui"]
        home["tabs/home_tab.py"]
        glucose_ui["tabs/glucose_tab.py"]
        activity_ui["tabs/activity_tab.py"]
        card["widgets/summary_card.py"]
    end

    subgraph services["app/services"]
        glucose_analysis["glucose/analysis.py"]
        glucose_importer["glucose/importer.py"]
        activity_analysis["activity/analysis.py"]
        fitbit_importer["activity/fitbit_importer.py"]
        fitbit_client["activity/fitbit_client.py"]
        fitbit_auth["activity/fitbit_auth.py"]
    end

    subgraph db["app/db"]
        models["models.py"]
        database["database.py"]
        base["base.py"]
    end

    diabetes["Diabetes:M CSV"]
    fitbit["Fitbit API"]
    sqlite["data/riglog.db"]

    main --> window
    main --> database
    main --> base

    window --> home
    window --> glucose_ui
    window --> activity_ui

    home --> card
    glucose_ui --> card
    activity_ui --> card

    diabetes --> glucose_importer
    glucose_ui --> glucose_importer
    glucose_ui --> glucose_analysis
    glucose_importer --> database
    glucose_analysis --> database

    fitbit --> fitbit_client
    fitbit_auth --> fitbit_client
    fitbit_client --> fitbit_importer
    activity_ui --> fitbit_importer
    activity_ui --> activity_analysis
    home --> activity_analysis
    fitbit_importer --> database
    activity_analysis --> database

    models --> database
    database --> sqlite
```

</details>


## Project Status

RigLog is currently in active development, with two core modules implemented:

### 🩸 Glucose Module (v1 — Complete)

- End-to-end data pipeline (Diabetes:M CSV → SQLite)
- Interactive dashboard:
  - AGP (Ambulatory Glucose Profile)
  - Time-in-range analysis
  - Meal-event drilldowns
  - Range-based filtering
- Variability metrics (SD, CV, GMI)
- Insulin effectiveness analysis
- PDF report generation

---

### 🚶 Activity Module (MVP — Complete)

- Fitbit API integration (OAuth + sync)
- Daily activity ingestion
- 7-day rolling averages and trends
- Goal adherence tracking (10k steps)
- Streak analysis
- Interactive charts (daily + weekly)

---

### 🏠 Home Dashboard

- Unified summary view across modules
- Live summary cards powered by shared service layer
- Navigation entry point into each module

## Getting Started

```bash
pip install -r requirements.txt
python -m app.main
```
