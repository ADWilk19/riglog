# RigLog 🩸💪

![RigLog Logo](assets/branding/logo_full.png)

> One app. Multiple health signals. Clearer decisions.

RigLog is a personal health analytics desktop application built in Python,
designed to turn raw health data into actionable insights.

It currently focuses on glucose analysis, with future support planned for activity, nutrition, and training data.

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

## Why RigLog?

RigLog was built to centralise and analyse personal health data,
starting with glucose monitoring.

The goal is to move beyond raw readings and provide:
- actionable insights
- trend analysis
- decision support for insulin dosing

Future modules will integrate activity, nutrition, and training data.

## Tech Stack

- Python
- PySide6 (desktop UI)
- Pandas (data analysis)
- Matplotlib (visualisation)
- SQLite (local database)
- ReportLab (PDF export)

## Project Status

Glucose module complete (v1)

Current capabilities:
- Full glucose data ingestion pipeline
- Advanced analytics (AGP, variability, dose effectiveness)
- Interactive desktop dashboard
- PDF report generation with charts

Next focus:
- Idempotent imports
- Activity module integration

## Roadmap

- Activity integration (steps, workouts)
- Idempotent data imports
- Food tracking
- Enhanced PDF reporting (tables, trends)
- Cross-metric insights (glucose vs activity)

## Getting Started

```bash
pip install -r requirements.txt
python -m app.main
```
