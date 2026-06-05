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

    FOODS {
        integer id PK
        string food_key
        string name
        string brand
        string serving_notes
        float calories_per_100g
        float carbs_per_100g
        float protein_per_100g
        float fat_per_100g
        float fibre_per_100g
        float salt_per_100g
        string source
        string notes
    }

    MEAL_TEMPLATES {
        integer id PK
        string name
        string description
        string default_meal_event
        string notes
    }

    MEAL_TEMPLATE_ITEMS {
        integer id PK
        integer meal_template_id FK
        integer food_id FK
        float quantity_g
        integer display_order
        string notes
    }

    MEAL_LOGS {
        integer id PK
        datetime logged_at
        integer meal_template_id FK
        string meal_event
        float portion_multiplier
        string notes
        string source
    }

    MEAL_TEMPLATES ||--o{ MEAL_TEMPLATE_ITEMS : contains
    FOODS ||--o{ MEAL_TEMPLATE_ITEMS : used_in
    MEAL_TEMPLATES ||--o{ MEAL_LOGS : logged_as
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
- Workout calorie analysis is derived in the service layer by aligning `workout_sessions.started_at` / `ended_at` with `activity_intraday.recorded_at`; it is not represented as a physical table relationship.
- Nutrition/glucose analysis is handled in the service layer by aligning `meal_logs.logged_at` with `glucose_readings.recorded_at`; there is no physical foreign-key relationship between meals and glucose readings.
