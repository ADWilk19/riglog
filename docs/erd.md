# 🧭 RigLog Entity Relationship Diagram

This document describes the current RigLog database model and key table relationships.

## 🧱 Database ERD

```mermaid
erDiagram
    GLUCOSE_READINGS {
        integer id PK
        float glucose_value
        datetime recorded_at
        string source
        string notes
        float carbs_g
        float humalog_u
        float tresiba_u
    }

    DAILY_ACTIVITY {
        integer id PK
        date activity_date
        integer steps
        float calories_burned
        float distance_km
        integer active_minutes
        string source
    }

    ACTIVITY_INTRADAY {
        integer id PK
        datetime recorded_at
        integer steps
        float calories_burned
        float distance_km
        string source
    }

    DAILY_ENVIRONMENT {
        integer id PK
        date environment_date
        string location_label
        float latitude
        float longitude
        float avg_temperature_c
        float min_temperature_c
        float max_temperature_c
        string source
        string notes
    }

    EXERCISES {
        integer id PK
        string exercise_key
        string name
        string category
        string primary_muscle
        string equipment
        string notes
    }

    WORKOUT_ROUTINES {
        integer id PK
        string name
        string notes
    }

    WORKOUT_ROUTINE_EXERCISES {
        integer id PK
        integer routine_id FK
        integer exercise_id FK
        integer display_order
    }

    WORKOUT_SESSIONS {
        integer id PK
        datetime started_at
        datetime ended_at
        integer routine_id FK
        string workout_type
        integer perceived_effort
        string notes
        string source
    }

    WORKOUT_SETS {
        integer id PK
        integer session_id FK
        integer exercise_id FK
        integer set_number
        float weight_kg
        integer reps
        string notes
    }

    WORKOUT_ROUTINES ||--o{ WORKOUT_ROUTINE_EXERCISES : contains
    EXERCISES ||--o{ WORKOUT_ROUTINE_EXERCISES : appears_in

    WORKOUT_ROUTINES ||--o{ WORKOUT_SESSIONS : templates
    WORKOUT_SESSIONS ||--o{ WORKOUT_SETS : contains
    EXERCISES ||--o{ WORKOUT_SETS : performed_as
```

## 🔗 Relationship Notes

- `workout_routines` define reusable templates such as Push, Pull, and Legs.
- `workout_routine_exercises` links routines to exercises and preserves display order.
- `workout_sessions` represents completed workout events.
- `workout_sets` stores set-level performance data within each session.
- `exercises` acts as the stable exercise catalogue for both routine templates and completed workout sets.

## 📝 Grain Notes

- Glucose data currently has no direct foreign-key relationship to meals, activity, or workouts.
- Activity/glucose/environment analysis is handled in the service layer by aligning records by date or timestamp.
- `daily_activity` and `activity_intraday` intentionally use separate grains.
- `daily_environment` is location-aware to avoid double-counting glucose readings when multiple weather locations exist for the same date.
- Workout data separates planned structure from completed activity:
  - planned structure: `workout_routines`, `workout_routine_exercises`, `exercises`
  - completed activity: `workout_sessions`, `workout_sets`
