# 🗂️ RigLog Data Dictionary

This document describes RigLog’s database tables, their grain, and the meaning of each field.

---

## Table of Contents

- [Glucose Readings](#-glucose_readings)
- [Daily Activity](#-daily_activity)
- [Intraday Activity](#-activity_intraday)
- [Daily Environment](#️-daily_environment)
- [Exercises](#️-exercises)
- [Workout Routines](#️-workout_routines)
- [Workout Routine Exercises](#️-workout_routine_exercises)
- [Workout Sessions](#️-workout_sessions)
- [Workout Sets](#️-workout_sets)
- [Foods](#️-foods)
- [Meal Templates](#️-meal_templates)
- [Meal Template Items](#️-meal_template_items)
- [Meal Logs](#️-meal_logs)
- [Grain Notes](#-grain-notes)

---

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

| Column | Type | Nullable | Default | Meaning |
| --- | --- | ---: | ---: | --- |
| `id` | Integer | No | — | Primary key |
| `environment_date` | Date | No | — | Environment or weather date |
| `location_label` | String | No | `"default"` | Logical location label, e.g. `home` |
| `latitude` | Float | Yes | — | Latitude for the weather source |
| `longitude` | Float | Yes | — | Longitude for the weather source |
| `avg_temperature_c` | Float | No | — | Mean daily temperature in Celsius |
| `min_temperature_c` | Float | Yes | — | Minimum daily temperature in Celsius |
| `max_temperature_c` | Float | Yes | — | Maximum daily temperature in Celsius |
| `source` | String | Yes | — | Source system, e.g. `manual_csv` or `open_meteo` |
| `notes` | String | Yes | — | Free-text notes |

**Unique rule:** `environment_date` + `location_label` + `source`

**Indexes:**

- `id`
- `environment_date`

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

**Timing note:** `ended_at` enables workout duration, average duration metrics, and activity-calorie alignment for workout insight analysis.

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

## 🍽️ `foods`

**Grain:** One reusable food item.

| Column | Type | Nullable | Default | Meaning |
| --- | --- | ---: | ---: | --- |
| `id` | Integer | No | — | Primary key |
| `name` | String | No | — | Human-readable food name |
| `brand` | String | Yes | — | Brand or manufacturer |
| `serving_notes` | Text | Yes | — | Serving-size notes from the label or source |
| `calories_per_100g` | Float | No | `0.0` | Calories per 100g |
| `carbs_per_100g` | Float | No | `0.0` | Carbohydrates per 100g |
| `protein_per_100g` | Float | No | `0.0` | Protein per 100g |
| `fat_per_100g` | Float | No | `0.0` | Fat per 100g |
| `fibre_per_100g` | Float | No | `0.0` | Fibre per 100g |
| `salt_per_100g` | Float | No | `0.0` | Salt per 100g |
| `source` | String | Yes | — | Source system, e.g. `manual`, `csv`, `demo`, or `cofid` |
| `notes` | Text | Yes | — | Free-text notes |

**Indexes:**

- `id`
- `name`

---

## 🍽️ `meal_templates`

**Grain:** One reusable meal definition or template.

| Column | Type | Nullable | Meaning |
| --- | --- | ---: | --- |
| `id` | Integer | No | Primary key |
| `name` | String | No | Human-readable meal-template name |
| `description` | Text | Yes | Description of the meal |
| `default_meal_event` | String | Yes | Default meal-event classification used when logging the meal |
| `notes` | Text | Yes | Free-text notes |

**Indexes:**

- `id`
- `name`

---

## 🍽️ `meal_template_items`

**Grain:** One food assigned to one meal template.

| Column | Type | Nullable | Default | Meaning |
| --- | --- | ---: | ---: | --- |
| `id` | Integer | No | — | Primary key |
| `meal_template_id` | Integer | No | — | Foreign key to `meal_templates.id` |
| `food_id` | Integer | No | — | Foreign key to `foods.id` |
| `quantity_g` | Float | No | — | Quantity of the food in grams |
| `display_order` | Integer | No | `0` | Order in which the food appears in the meal template |
| `notes` | Text | Yes | — | Free-text notes |

**Indexes:**

- `id`
- `meal_template_id`
- `food_id`

---

## 🍽️ `meal_logs`

**Grain:** One logged meal occurrence.

| Column | Type | Nullable | Default | Meaning |
| --- | --- | ---: | ---: | --- |
| `id` | Integer | No | — | Primary key |
| `logged_at` | DateTime | No | — | Timestamp of the logged meal |
| `meal_template_id` | Integer | No | — | Foreign key to `meal_templates.id` |
| `meal_event` | String | Yes | — | Meal-event classification used in glucose/nutrition analysis |
| `portion_multiplier` | Float | No | `1.0` | Multiplier applied to the meal-template nutrition totals |
| `notes` | Text | Yes | — | Free-text notes |
| `source` | String | Yes | — | Source system, e.g. `manual`, `demo`, or `csv` |

**Indexes:**

- `id`
- `logged_at`
- `meal_template_id`
- `meal_event`

---

## 📝 Grain Notes

- `workout_sessions` stores the workout-level event.
- `workout_sets` stores the performed set-level detail.
- `exercises` stores reusable catalogue metadata.
- `workout_routines` and `workout_routine_exercises` define templates, not completed workouts.
- Activity and environment tables are separated by grain: daily summaries versus intraday/activity buckets.
- `foods` stores reusable nutrition metadata with nutrient values expressed per 100g.
- `meal_templates` defines reusable named meals.
- `meal_template_items` links foods to meal templates and records the quantity in grams.
- `meal_logs` stores completed meal occurrences and must reference an existing meal template.
- Nutrition and glucose are linked analytically by meal-log timestamps and meal-event classifications; there is no direct foreign key from `meal_logs` to `glucose_readings`.

---
