# 🗂️ RigLog Data Dictionary

This document describes RigLog’s database tables, their grain, and the meaning of each field.

## 🩸 `glucose_readings`

**Grain:** One glucose reading.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `glucose_value` | Float | No | Glucose value in mmol/L |
| `recorded_at` | DateTime | No | Timestamp of the reading |
| `source` | String | Yes | Source system, e.g. `diabetes_m` |
| `notes` | String | Yes | Free-text contextual notes |
| `carbs_g` | Float | Yes | Carbohydrates associated with the reading |
| `humalog_u` | Float | Yes | Humalog dose in units |
| `tresiba_u` | Float | Yes | Tresiba dose in units |

---

## 🚶 `daily_activity`

**Grain:** One daily activity summary per date and source.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `activity_date` | Date | No | Activity date |
| `steps` | Integer | Yes | Total daily steps |
| `calories_burned` | Float | Yes | Total daily calories burned |
| `distance_km` | Float | Yes | Distance travelled in kilometres |
| `active_minutes` | Integer | Yes | Active minutes |
| `source` | String | Yes | Source system, e.g. `fitbit` |

**Unique rule:** `activity_date` + `source`

---

## 🚶 `activity_intraday`

**Grain:** One intraday activity bucket per timestamp and source.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `recorded_at` | DateTime | No | Timestamp of the intraday activity record |
| `steps` | Integer | Yes | Steps in the interval |
| `calories_burned` | Float | Yes | Calories burned in the interval |
| `distance_km` | Float | Yes | Distance in kilometres for the interval |
| `source` | String | Yes | Source system, e.g. `fitbit` |

**Unique rule:** `recorded_at` + `source`

---

## 🌡️ `daily_environment`

**Grain:** One daily environment record per date, location, and source.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `environment_date` | Date | No | Environment/weather date |
| `location_label` | String | No | Logical location label, e.g. `home` |
| `latitude` | Float | Yes | Latitude for the weather source |
| `longitude` | Float | Yes | Longitude for the weather source |
| `avg_temperature_c` | Float | No | Mean daily temperature in Celsius |
| `min_temperature_c` | Float | Yes | Minimum daily temperature in Celsius |
| `max_temperature_c` | Float | Yes | Maximum daily temperature in Celsius |
| `source` | String | Yes | Source system, e.g. `manual_csv` or `open_meteo` |
| `notes` | String | Yes | Free-text notes |

**Unique rule:** `environment_date` + `location_label` + `source`

---

## 🏋️ `exercises`

**Grain:** One reusable exercise catalogue item.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `exercise_key` | String | Yes | Stable exercise identifier used by imports |
| `name` | String | No | Human-readable exercise name |
| `category` | String | Yes | Exercise category, e.g. `Compound` or `Accessory` |
| `primary_muscle` | String | Yes | Main target muscle group |
| `equipment` | String | Yes | Primary equipment used |
| `notes` | String | Yes | Free-text notes |

**Unique rules:**

- `exercise_key`
- `name`

---

## 🏋️ `workout_routines`

**Grain:** One workout routine/template.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `name` | String | No | Routine name, e.g. `Push`, `Pull`, `Legs` |
| `notes` | String | Yes | Free-text notes |

**Unique rule:** `name`

---

## 🏋️ `workout_routine_exercises`

**Grain:** One exercise assigned to one workout routine.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `routine_id` | Integer | No | Foreign key to `workout_routines.id` |
| `exercise_id` | Integer | No | Foreign key to `exercises.id` |
| `display_order` | Integer | Yes | Order in which the exercise appears in the routine |

**Unique rule:** `routine_id` + `exercise_id`

---

## 🏋️ `workout_sessions`

**Grain:** One workout occurrence.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `started_at` | DateTime | No | Workout start timestamp |
| `ended_at` | DateTime | Yes | Workout end timestamp |
| `routine_id` | Integer | Yes | Foreign key to `workout_routines.id` |
| `workout_type` | String | Yes | Workout label, e.g. `Push`, `Pull`, `Legs` |
| `perceived_effort` | Integer | Yes | Subjective effort rating |
| `notes` | String | Yes | Free-text notes |
| `source` | String | Yes | Source system, e.g. `workout_csv` |

---

## 🏋️ `workout_sets`

**Grain:** One performed set within a workout session.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `session_id` | Integer | No | Foreign key to `workout_sessions.id` |
| `exercise_id` | Integer | No | Foreign key to `exercises.id` |
| `set_number` | Integer | No | Set number for the exercise within the session |
| `weight_kg` | Float | Yes | Weight used in kilograms |
| `reps` | Integer | Yes | Repetitions performed |
| `notes` | String | Yes | Free-text notes |

**Unique rule:** `session_id` + `exercise_id` + `set_number`

---

## 📝 Grain Notes

- `workout_sessions` stores the workout-level event.
- `workout_sets` stores the performed set-level detail.
- `exercises` stores reusable catalogue metadata.
- `workout_routines` and `workout_routine_exercises` define templates, not completed workouts.
- Activity and environment tables are separated by grain: daily summaries versus intraday/activity buckets.
