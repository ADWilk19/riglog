# RigLog Backlog 📋

This backlog is organised by architectural layer and implementation priority.

---

## 🔥 Phase 1 — Activity Module Completion ✅ COMPLETE

### Activity → Service Layer (`app/services/activity/analysis.py`)

* [x] Goal Adherence Metric

  * `% of days hitting target (default: 10k)`
  * Return:

    * `goal_days`
    * `goal_adherence_pct`

---

### Activity → UI Layer (`app/ui/tabs/activity_tab.py`)

* [x] Goal Adherence Card

  * Display:

    * `18 / 30 days`
    * `(60%)`
  * Style:

    * green if ≥ 70%
    * neutral otherwise

* [X] Refactor Summary Cards

  * Home cards now implemented
  * Activity Summary Refactor ✅ COMPLETE
    * Moved summary logic to service layer
    * Introduced shared card contract
    * Integrated HomeTab with service output
  * Glucose Summary Refactor (Next)
    * Align GlucoseTab with service-driven summary cards
    * Remove UI formatting logic
    * Reuse SummaryCard contract

---

### Activity → Chart Layer (`ActivityTrendChart`)

* [x] Weekly Aggregation View

  * Add toggle: `Daily` ↔ `Weekly`
  * Weekly options:

    * total steps OR average steps

* [x] Chart Mode Toggle

  * Toggle:

    * Steps
    * Rolling Average
    * Weekly

### Home → UI Layer

* [x] Summary Cards Navigation
  * Clickable cards navigate to modules

* [x] Live Data Binding
  * Glucose and Activity cards display real metrics

* [x] Auto-refresh on Activity Sync

  * Update Home cards when new activity data is imported
  * Trigger Home refresh from Activity tab `data_updated` signal
  * Ensure Home glucose/activity cards remain current after sync

### System

* [x] Fitbit OAuth token auto-refresh

  * Prevent reauthentication on expiry
  * Persist refreshed tokens automatically

* [x] Background Sync ✅ COMPLETE

  * Scheduled hourly Fitbit sync
  * Startup sync after app launch
  * Updates `last_synced` automatically
  * Refreshes Home activity metrics via `data_updated`

---

## 🧠 Phase 2 — Insight Layer Expansion ✅ COMPLETE

### Activity → Service Layer

* [x] Rolling Goal Adherence

  * e.g. last 7 / 14 days
  * Return:

    * `goal_adherence_last_7`
    * `goal_adherence_last_14`

* [x] Weekly Summary Metrics

  * Return:

    * `best_week_steps`
    * `worst_week_steps`

* [x] Step Consistency Metric

  * Std deviation of daily steps
  * Optional:

    * coefficient of variation (CV)

---

### Activity → UI Layer

* [x] Weekly Summary Card(s)

  * Best week
  * Worst week

* [x] Consistency Indicator

  * Label:

    * “Consistent”
    * “Variable”

---

## 📊 Phase 3 — Interaction Enhancements ✅ COMPLETE

### 🩸 Glucose — UI Layer

> Phase 3 glucose interaction work is ahead of schedule. Return focus to Phase 1–2 Activity completion before expanding further interaction features.

* [x] Range-Based Meal Event Breakdown

  * When a glucose range card is selected:
    * Display horizontal bar chart of readings grouped by meal event
    * Sorted chronologically (Pre → Post events)
  * Bars styled using TIR-aligned colour system
  * Values displayed on bars with proportional spacing
  * Chart only visible when a range filter is active

* [x] Meal Event Drilldown (Chart Interaction)

  * Clicking a bar:
    * Applies meal event filter via dropdown
    * Triggers full UI refresh (charts, stats, table)
  * Clicking same bar again:
    * Resets meal event filter to "All" (toggle behaviour)

* [x] Unified Filter State Display

  * Toolbar label reflects active filters:
    * Range only
    * Meal event only
    * Combined state (e.g. `Low • Pre-Lunch`)
  * Updated centrally via `load_readings()`

* [x] Clear Filters Control

  * Add UI control to reset:
    * range filter
    * meal event filter
  * Option:
    * button or clickable toolbar label

---

### Activity → Chart Layer

* [x] Click-to-Select Day

  * Click event on scatter points
  * Emit selected index/date

---

### Activity → UI Layer

* [x] Selected Day Detail Panel

  * Display:

    * date
    * steps
    * goal hit (yes/no)
    * delta vs 7-day average

* [x] Persist Selection State

  * Maintain selected day on refresh

---

## 🔗 Phase 4 — Cross-Module Intelligence ✅ COMPLETE

### Activity ↔ Glucose Integration

* [x] Overlay Activity on Glucose Charts

  * [x] Add daily Activity ↔ Glucose comparison chart
    * Top: daily average glucose
    * Bottom: daily steps
    * Shared date axis
    * Service-backed via daily overlay contract
  * [x] Align activity and glucose on timestamp / intraday grain
  * [x] Show step density vs glucose where visually useful
    * [x] Add intraday Activity ↔ Glucose stacked chart
      * Top: glucose by time bucket
      * Bottom: steps by same time bucket
      * Powered by `get_intraday_activity_glucose_alignment()`
    * [x] Keep chart separate from AGP
    * [x] Avoid dual-axis overlay unless later justified
  * [x] Decide whether intraday overlay belongs in Glucose tab or separate insight view
    * Decision:
      * Keep the first version in the Glucose tab
    * Reason:
      * The chart directly contextualises glucose readings against same-day step density
      * It is service-backed and date-selectable
      * It avoids misleading AGP overlays
    * Future:
      * Consider moving cross-module charts into a dedicated Insights tab if the Glucose tab becomes too crowded

* [x] Correlation Metrics

  * Service-layer contract complete
  * Steps vs average next glucose
  * Calories burned vs average next glucose
  * Steps vs glucose delta
  * Calories burned vs glucose delta
  * Tested with pure-function coverage
  * Future:
    * Steps vs glucose variability
    * Steps vs time-in-range

---

* [x] Calories Burned by Meal Event

  * Aggregate activity calories by glucose meal-event window
  * Compare calories burned against subsequent glucose trajectory
  * Initial version:
    * meal event → calories burned → average next glucose reading
  * Future:
    * correlation between calories burned and glucose change
  * Requires:
    * intraday calorie burn data

---

### Event-Based Activity Analysis (Backlog)

* [x] Introduce Activity Event Classification

  * Align with glucose event windows:

    * Pre-Breakfast
    * Post-Breakfast
    * etc.

* [x] Aggregate Steps by Event Window

⚠️ Requires:

* Intraday activity data (see Phase 5)

---

### 🌡️ Environmental Factors → Glucose (Hypothesis)

* [x] Temperature vs Glucose Analysis — Service Layer

  * Hypothesis:
    * Ambient temperature may influence glucose behaviour
    * Potential effects:
      * insulin sensitivity changes
      * activity level changes
      * dehydration effects

  * Implemented:
    * Added `daily_environment` database model
    * Added manual daily weather CSV importer
    * Added daily temperature ↔ glucose alignment by date
    * Added temperature buckets:
      * cold
      * mild
      * warm
      * hot
    * Added average glucose by temperature bucket
    * Added time-in-range by temperature bucket
    * Added pure service-layer tests
    * Confirmed duplicate-skipping for manual CSV import

  * Current return contract:
    * `temperature_bucket`
    * `temperature_bucket_label`
    * `day_count`
    * `glucose_count`
    * `avg_temperature_c`
    * `avg_glucose`
    * `hypo_pct`
    * `low_pct`
    * `target_pct`
    * `high_pct`
    * `hyper_pct`

* [x] Temperature vs Glucose — UI / Visualisation — Table

  * Implemented:
    * Added read-only Temperature vs Glucose section to the Glucose tab
    * Added temperature bucket summary table
    * Displays:
      * bucket
      * day count
      * glucose reading count
      * average temperature
      * average glucose
      * target %
      * hypo %
      * hyper %
    * Uses existing service-layer contract:
      * `get_temperature_glucose_bucket_summary()`
    * Preserves bucket order:
      * cold
      * mild
      * warm
      * hot
    * Handles empty buckets cleanly with `0` / `-`

* [x] Location-Aware Environmental Data

  * Implemented:
    * Extended `daily_environment` to support multiple locations
    * Added:
      * `location_label`
      * `latitude`
      * `longitude`
    * Updated uniqueness rule to:
      * date + location + source
    * Updated manual CSV importer to support optional location fields
    * Preserved backwards compatibility:
      * missing location defaults to `default`
    * Updated service-layer functions to accept `location_label`
    * Prevents double-counting glucose readings when weather exists for multiple locations on the same date
    * Added importer test coverage for multiple locations

* [x] Temperature vs Glucose — Chart Visualisation

  * Implemented:
    * Added stacked Temperature vs Glucose chart to the Glucose tab
    * Displays average glucose by temperature bucket
    * Displays target % by temperature bucket
    * Reuses `get_temperature_glucose_bucket_summary()`
    * Uses `DEFAULT_ENVIRONMENT_LOCATION_LABEL` for the current default location

  * Visualisations:
    * Temperature bucket vs average glucose chart
    * Temperature bucket vs TIR% chart

* [x] Temperature Import Hardening — Initial

  * Implemented:
    * Added importer tests with isolated SQLite test database
    * Confirmed duplicate-skipping behaviour
    * Confirmed optional fields default cleanly
    * Confirmed same-date imports are allowed for different locations

* [x] Weather Data Expansion

  * [x] Add Open-Meteo parser/normaliser tests using static sample JSON
    * Proves JSON → DailyEnvironment-shaped row contract
    * No live API dependency
    * Handles:
      * required date + mean temperature
      * missing required values by skipping incomplete rows
      * missing optional min/max values as `None`
  * [x] Add Open-Meteo historical weather import
  * [x] Fetch daily weather by:
    * location label
    * latitude
    * longitude
    * start date
    * end date
  * [x] Persist:
    * mean daily temperature
    * min daily temperature
    * max daily temperature
    * source = `open_meteo`
  * [x] Support two primary user locations without storing coordinates in Git
  * [x] Load location config from environment variables
  * Implemented:
    * Added environment-backed Open-Meteo location config
    * Supports named locations such as `home` and `partner-home`
    * Keeps real coordinates in local `.env`
    * Added tests for config loading, label normalisation, missing config, and import delegation

* [ ] Future Environmental Extensions — Deferred

  * Intraday temperature vs glucose
    * Requires intraday weather data
  * Interaction with activity:
    * steps × temperature × glucose
  * Lagged effects:
    * temperature today vs glucose next day
  * Additional environmental variables:
    * humidity
    * pollen
    * air pressure
    * weather condition

### Architecture Documentation

* [x] Add data dictionary
  * Document each database table
  * Include:
    * column name
    * data type
    * nullable status
    * meaning / business definition
    * source system
    * notes on grain

* [x] Add ERD for database models
  * Include:
    * glucose_readings
    * daily_activity
    * activity_intraday
    * daily_environment
    * exercises
    * workout_routines
    * workout_routine_exercises
    * workout_sessions
    * workout_sets
  * Show primary keys, foreign keys, and relationship cardinality
  * Store diagram source in the repo, e.g. Mermaid or dbdiagram format

* [x] Add code reference documentation
  * Document key classes, methods, and functions across the app
  * Include:
    * name
    * type: class / method / function
    * file path
    * responsibility
    * key inputs
    * key outputs / side effects
    * notes for debugging
  * Initial scope:
    * database models
    * service-layer functions
    * importers
    * UI tab classes
    * chart classes
    * shared widgets

* [x] Use emoji-led section headings where helpful
  * Keep documentation readable and pleasant to scan
  * Avoid overusing emojis inside technical tables or function definitions

---

## 🧱 Phase 5 — Data Layer Expansion ✅ COMPLETE

### Activity → Database (`app/db/models.py`)

* [x] Add `activity_intraday` table

  * Fields:

    * `recorded_at` (datetime)
    * `steps`
    * `source`

* [x] Add calorie fields to `activity_intraday`

  * Fields:
    * `calories_burned`

---

### Activity → Importer (`app/services/activity/fitbit_importer.py`)

* [x] Add Intraday Import

  * Pull minute / interval data from Fitbit API
  * Persist to `activity_intraday`

* [x] Add Calorie Burn Import

  * Pull calorie expenditure from Fitbit API
  * Support:
    * daily total calories (initial)
    * intraday calorie burn (preferred)
  * Persist to database

---

### Activity → Service Layer

* [x] Intraday Aggregation Functions

  * Steps by hour

* [x] Event Window Aggregation Functions

  * Steps by event window

---

## 🎨 Phase 6 — UI / UX Polish

### Activity → UI Layer

* [ ] Card Iconography

  * Add icons for:

    * streak
    * trend
    * goal

* [ ] Theme Refinement

  * Align:

    * card colours
    * tooltip styling
    * chart palette

---

### Chart Layer

* [ ] Animation on Refresh

  * Smooth transitions for:

    * lines
    * points


* [ ] Restore Daily Selection After Weekly Toggle

  * When a daily activity point is selected:
    * Preserve the selected date internally when switching to Weekly view
    * Hide or clear the visible selected-day panel while Weekly view is active
    * Restore the selected-day panel when switching back to Daily view, if the date is still present in the current filtered dataset
  * If the selected date is excluded by the active time range:
    * Clear the stored selection
  * Goal:
    * Improve chart-mode toggle UX without confusing daily selection with weekly aggregation

---

### Glucose → Chart Layer

* [ ] Add Chart Tooltips

  * Add hover tooltips for glucose charts:
    * Daily Average Glucose
    * Daily Glucose vs Steps
    * Time-of-Day Profile
    * Meal Event Boxplot, if feasible
  * Tooltip content:
    * date / time bucket
    * glucose value or average
    * reading count where relevant
    * steps for activity overlay chart
  * Keep tooltip styling aligned with dark theme
  * Avoid adding tooltips to AGP unless a clear interaction model emerges

---

## 🏋️ Phase 7 — Workout Module

### Workout → Database Layer

* [x] Replace placeholder workout model with normalized workout schema
  * Add `Exercise`
    * exercise_key
    * name
    * category
    * primary_muscle
    * equipment
  * Add `WorkoutRoutine`
    * name
    * notes
  * Add `WorkoutRoutineExercise`
    * routine_id
    * exercise_id
    * display_order
  * Refactor `WorkoutSession`
    * started_at
    * ended_at
    * workout_type / routine_id
    * perceived_effort
    * notes
    * source
  * Add `WorkoutSet`
    * session_id
    * exercise_id
    * set_number
    * weight_kg
    * reps
    * notes

### Workout → Import / Seed Layer

* [x] Seed exercise catalogue from curated Push/Pull/Legs exercise list
* [x] Seed routine-to-exercise mappings
* [x] Add manual workout-set import path from spreadsheet-style CSV
  * Import `WorkoutSession` rows grouped by date/workout
  * Import `WorkoutSet` rows from set-level CSV records
  * Resolve exercises by stable `exercise_key`
  * Skip duplicate sets idempotently

### Workout → Service Layer

* [x] Add workout summary metrics
  * total sessions
  * weekly sessions
  * average duration
  * most recent workout
  * total sets
  * total volume kg
  * volume by exercise
  * volume by workout type

### Workout → UI Layer

* [x] Build read-only Workout tab foundation
  * Add spreadsheet / CSV import button
  * Add workout history table
  * Add summary cards
  * Add volume-by-exercise table
  * Add recent sessions table
  * Defer manual workout entry until later

* [x] Add workout volume chart
  * Display top exercises by total training volume
  * Reuse `get_volume_by_exercise()`
  * Keep volume-by-exercise detail table underneath

* [x] Add clear imported workout data action
  * Delete imported `WorkoutSession` and `WorkoutSet` records
  * Preserve seeded exercises and workout routines
  * Require confirmation before deleting
  * Intended for replacing demo workout data with real imported data

### Workout → Chart Layer

* [x] Add exercise progression chart
  * Add exercise dropdown populated from workout data
  * Plot selected exercise progression over time
  * Initial metric:
    * highest weight lifted per workout date
  * Include contextual fields:
    * workout type
    * reps achieved at highest weight
    * total exercise volume for that date
  * Future extensions:
    * estimated 1RM
    * best weight by rep count
    * total volume trend
    * rep-range selector

### Workout → Insight Layer

* [x] Add workout session calorie analysis
  * Estimate or import calories burned per workout session
  * Preferred first version:
    * use `activity_intraday.calories_burned`
    * sum calories between `WorkoutSession.started_at` and `WorkoutSession.ended_at`
  * Requires workout session duration or end time
  * Compare calorie burn against lifting style:
    * heavy weight / low reps
    * lighter weight / higher reps
  * Return:
    * session_id
    * workout_type
    * started_at
    * duration_minutes
    * total_sets
    * total_reps
    * total_volume_kg
    * average_load_per_rep
    * max_weight_kg
    * calories_burned
    * calories_per_minute
    * calories_per_kg_lifted
  * Future extensions:
    * MET-based fallback estimate
    * heart-rate-informed calorie estimate
    * session intensity classification

* [ ] Add workout intensity classification
  * Compare heavy weight / low reps vs lighter weight / higher reps
  * Add session labels based on average load per rep, total reps, and volume
  * Consider charting calories per minute and calories per kg lifted

### Home → UI Layer

* [x] Add live Workout summary card
  * Display total workout sessions
  * Display weekly sessions and total volume
  * Navigate to Workout tab

## 🍽️ Phase 8 — Nutrition Module

### Slice 1 — Nutrition Model Foundation ✅ COMPLETE

#### Nutrition → Database Layer (`app/db/models.py`)

* [x] Add `Food`
  * Grain:
    * one reusable food item
  * Fields:
    * name
    * brand
    * serving_notes
    * calories_per_100g
    * carbs_per_100g
    * protein_per_100g
    * fat_per_100g
    * fibre_per_100g
    * salt_per_100g
    * source
    * notes

* [x] Add `MealTemplate`
  * Grain:
    * one reusable meal definition
  * Fields:
    * name
    * description
    * default_meal_event
    * notes

* [x] Add `MealTemplateItem`
  * Grain:
    * one food within one reusable meal template
  * Fields:
    * meal_template_id
    * food_id
    * quantity_g
    * display_order
    * notes

* [x] Add `MealLog`
  * Grain:
    * one logged meal event
  * Fields:
    * logged_at
    * meal_template_id
    * meal_event
    * portion_multiplier
    * notes
    * source

* [x] Add model relationships
  * `MealTemplate` → many `MealTemplateItem`
  * `Food` → many `MealTemplateItem`
  * `MealTemplate` → many `MealLog`

---

### Slice 2 — Nutrition Calculation Service ✅ COMPLETE

#### Nutrition → Service Layer (`app/services/nutrition/analysis.py`)

* [x] Add food total calculation
  * Calculate nutrition totals for a food by quantity in grams
  * Return:
    * calories
    * carbs_g
    * protein_g
    * fat_g
    * fibre_g
    * salt_g

* [x] Add meal template total calculation
  * Sum all `MealTemplateItem` rows for a meal template
  * Apply each item quantity in grams
  * Return total calories and macros

* [x] Add logged meal total calculation
  * Calculate totals for a `MealLog`
  * Apply `portion_multiplier`
  * Return logged meal nutrition totals

* [x] Add database-backed total helpers
  * meal template totals by ID
  * logged meal totals by ID

* [x] Add nutrition summary metrics
  * total meals logged
  * total carbs by day
  * carbs by meal event
  * average daily carbs
  * calorie totals where available

* [x] Add display helpers for the Nutrition tab
  * recent meal logs
  * meal template totals rows
  * food selector options
  * meal template selector options

---

### Slice 3 — Seed / Demo Nutrition Data ✅ COMPLETE

#### Nutrition → Import / Seed Layer

* [x] Add sample foods under `data/demo`
  * Examples:
    * porridge oats
    * semi-skimmed milk
    * banana
    * Greek yoghurt
    * rice
    * chicken breast
    * olive oil

* [x] Add sample meal templates under `data/demo`
  * Examples:
    * porridge breakfast
    * chicken rice bowl
    * yoghurt and banana snack

* [x] Add sample meal logs under `data/demo`
  * Use realistic timestamps
  * Include meal events
  * Include portion multipliers

* [x] Add demo seed loader
  * Reads Nutrition demo CSV files
  * Inserts foods, meal templates, template items, and meal logs
  * Keeps demo seeding idempotent
  * Tested with isolated SQLite database

---

### Slice 4 — Read-Only Nutrition Tab ✅ COMPLETE

#### Nutrition → UI Layer (`app/ui/tabs/nutrition_tab.py`)

* [x] Build read-only Nutrition tab foundation
  * Add summary cards
  * Add recent meal logs table
  * Add meal template totals table

* [x] Add summary cards
  * Meals logged
  * Calories
  * Carbs
  * Protein
  * Fat
  * Average daily carbs

* [x] Add recent meal logs table
  * Display:
    * logged at
    * meal name
    * meal event
    * portion multiplier
    * calories
    * carbs
    * protein
    * fat
    * notes

* [x] Add meal template totals table
  * Display:
    * template name
    * default meal event
    * calories
    * carbs
    * protein
    * fat
    * fibre
    * salt

* [x] Add Home tab integration
  * Add live Nutrition summary card
  * Navigate from Home card to Nutrition tab
  * Refresh Home Nutrition card after nutrition updates
  * Clarify Home card uses 7-day nutrition summary

---

### Slice 5 — Manual Nutrition Entry ✅ COMPLETE

#### Nutrition → Manual Entry Service Layer

* [x] Add manual food creation service
  * Validate required food name
  * Reject negative nutrition values
  * Strip whitespace from text fields
  * Store source as `manual`

* [x] Add manual meal template creation service
  * Select existing foods
  * Store food quantities in grams
  * Validate at least one food item
  * Reject zero / negative quantities
  * Resolve missing food IDs safely

* [x] Add manual meal log creation service
  * Select existing meal template
  * Store logged timestamp
  * Store meal event
  * Apply portion multiplier
  * Validate positive portion multiplier
  * Store optional notes

#### Nutrition → Manual Entry UI Layer

* [x] Add Food form
  * Enter food label values per 100g
  * Save reusable food records
  * Refresh food selector after save

* [x] Build Meal form
  * Select foods from stored food database
  * Enter food quantities in grams
  * Add selected foods to pending meal
  * Save reusable meal template
  * Refresh meal template totals table after save

* [x] Log Meal form
  * Select saved meal template
  * Select logged-at timestamp
  * Auto-fill meal event from template default where possible
  * Apply portion multiplier
  * Save logged meal
  * Refresh Nutrition summary cards and Recent Meal Logs table

---

### Slice 6 — Nutrition CSV Import and External Dataset Conversion ✅ COMPLETE

#### Nutrition → CSV Import Layer

* [x] Add Nutrition tab food CSV import action
  * Select CSV file from the UI
  * Import reusable foods
  * Show imported count
  * Refresh food selector after import
  * Preserve duplicate-skipping behaviour

Future / Deferred:

* Meal template CSV import, if bulk migration becomes useful
* Meal log CSV import, if importing historical meal diaries becomes useful

---

#### Nutrition → External Dataset Converter

* [x] Add external food dataset converter
  * Converts normalised external nutrition CSVs into RigLog-compatible food CSV format
  * Supports optional food group filtering
  * Validates required source columns
  * Validates numeric values
  * Writes reviewable CSV output
  * Does not write directly to the database

* [x] Add provider-specific adapter
  * Initial candidate:
    * CoFID / UK food composition dataset
  * Convert raw provider export into normalised converter input
  * Keep provider-specific parsing separate from RigLog food import

* [x] Add converter output contract
  * Output CSV should match RigLog food import format:
    * food_key
    * name
    * brand
    * serving_notes
    * calories_per_100g
    * carbs_per_100g
    * protein_per_100g
    * fat_per_100g
    * fibre_per_100g
    * salt_per_100g
    * source
    * notes

* [x] Add review step before import
  * Generated CSV should be manually inspectable before being imported
  * Avoid writing external data directly into the database without review

* [ ] Future:
  * Add branded food support via API/export source
  * Add barcode-based lookup if a reliable data source is chosen
  * Add food-label photo extraction with user confirmation

* Prefer dataset/API conversion over web scraping for nutrition data.
  * External converters should produce CSV files.
  * RigLog should import reviewed CSVs rather than scrape websites directly.

---

### Slice 7 — Nutrition ↔ Glucose Analysis

#### Nutrition ↔ Glucose Service Layer

* [x] Add post-meal glucose response analysis
  * For each logged meal, calculate:
    * pre-meal / nearest prior glucose
    * average glucose 1–3 hours after meal
    * peak glucose 1–3 hours after meal
    * glucose delta
    * reading count

* [x] Add carbs / macros by glucose meal event
  * Group logged meals by meal event
  * Compare carbs, calories, protein, fat, and fibre against post-meal glucose response

* [x] Add meal template glucose response summary
  * Compare reusable meal templates against typical post-meal glucose outcomes
  * Return:
    * meal template
    * logged count
    * average carbs
    * average post-meal glucose
    * average glucose delta
    * peak post-meal glucose

* [ ] Future:
  * Identify meals associated with stable glucose response
  * Identify meals associated with elevated post-meal glucose
  * Add nutrition insights to a future dedicated Insights tab

### Future Nutrition ↔ Activity Energy Balance

* [ ] Add daily calorie intake vs calorie burn analysis
  * Compare logged nutrition calories against activity calories burned
  * Use:
    * logged meal calories from Nutrition module
    * daily calories burned from Activity / Fitbit data
  * Return:
    * date
    * total calories consumed
    * total activity calories burned
    * net calorie balance
    * meal count
  * Future:
    * show weekly calorie balance trend
    * flag low-fuel or high-surplus days
    * compare workout days vs rest days

---

## 🧪 Phase 9 — Testing & Quality Assurance

### UI Layer

* [ ] Add lightweight GlucoseTab interaction tests
  * Clear Filters resets range filter and meal-event dropdown
  * Range card click toggles selected range state
  * Meal-event breakdown click updates dropdown selection

* [ ] Add lightweight ActivityTab interaction tests
  * Chart mode toggle updates visible chart state
  * Refresh action updates summary cards
  * Selected-day interaction updates detail panel once implemented

* [ ] Add lightweight WorkoutTab interaction tests
  * Workout tab renders without crashing
  * Refresh action updates summary cards
  * Recent sessions table populates from mocked service-layer output
  * Volume-by-exercise table populates from mocked service-layer output
  * CSV import success refreshes workout data
  * CSV import failure shows an error message

* [ ] Add HomeTab navigation tests
  * Glucose card navigates to Glucose tab
  * Activity card navigates to Activity tab
  * Home cards render live service-layer summaries

* [ ] Add lightweight NutritionTab interaction tests
  * Nutrition tab renders without crashing
  * Add Food form validates required name
  * Build Meal form adds selected foods to pending meal
  * Log Meal form saves a meal log from a selected template
  * Refresh action updates summary cards and tables
  * Nutrition `data_updated` signal refreshes Home card

### Test Infrastructure

* [ ] Add pytest-qt support for UI interaction tests
  * Provide shared `qapp` / `qtbot` fixtures
  * Mock service-layer calls to avoid database dependency
  * Cover HomeTab, ActivityTab, GlucoseTab, WorkoutTab, and NutritionTab
  * Keep tests focused on widget state and signal behaviour

---

## 🧠 Phase 10 — Advanced Features

### Export / Reporting

* [ ] Activity Report Export

  * CSV / PDF
  * Include:

    * summary metrics
    * trends

---

### Personalisation

* [ ] Configurable Step Target

  * Replace fixed 10k with user setting

---

### Analytics

* [ ] Anomaly Detection

  * Flag unusually high/low days

---

## 🧭 Implementation Notes

* Prioritise features that:

  * reuse existing service-layer outputs
  * avoid expanding data model prematurely

* Intraday analysis should only be implemented once:

  * Activity module is feature-complete at daily level

* Maintain separation of concerns:

  * Importers → data ingestion
  * Services → calculations
  * UI → rendering only

---

## 🚀 Final Phase: macOS App Packaging & Distribution

Package RigLog as a double-clickable macOS application once the core modules are complete.

### Goals

* Package RigLog as a native `.app` bundle
* Allow the app to be launched from Finder and the Applications folder
* Add a proper app icon and bundle metadata
* Ensure bundled assets load correctly, including branding and QSS theme files
* Move writable app data out of the project directory
* Store the SQLite database in a user-safe macOS location, such as:
  * `~/Library/Application Support/RigLog/`
* Confirm Fitbit tokens and future settings persist correctly outside the repo
* Test CSV import, PDF export, charts, and tab navigation from the packaged app
* Document the packaged-app launch workflow in the README

### Notes

This phase should happen after the Glucose, Activity, Workout, and Nutrition panels are functionally complete.
