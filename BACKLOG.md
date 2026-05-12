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

## 📊 Phase 3 — Interaction Enhancements

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

* [ ] Selected Day Detail Panel

  * Display:

    * date
    * steps
    * goal hit (yes/no)
    * delta vs 7-day average

* [ ] Persist Selection State

  * Maintain selected day on refresh

---

## 🔗 Phase 4 — Cross-Module Intelligence

### Activity ↔ Glucose Integration

* [ ] Overlay Activity on Glucose Charts

  * Align on timestamp
  * Show step density vs glucose

* [ ] Correlation Metrics

  * Steps vs glucose variability
  * Steps vs time-in-range

---

* [ ] Calories Burned by Meal Event

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

* [ ] Introduce Activity Event Classification

  * Align with glucose event windows:

    * Pre-Breakfast
    * Post-Breakfast
    * etc.

* [ ] Aggregate Steps by Event Window

⚠️ Requires:

* Intraday activity data (see Phase 5)

---

### 🌡️ Environmental Factors → Glucose (Hypothesis)

* Temperature vs Glucose Analysis
  * Hypothesis:
    * Ambient temperature influences glucose behaviour
    * Potential effects:
      * insulin sensitivity changes
      * activity level changes
      * dehydration effects
  * Initial implementation:
    * Ingest daily temperature data (external API or manual import)
    * Align temperature with glucose readings by date
  * Return:
    * Average glucose by temperature bucket (e.g. cold / mild / warm)
    * Time-in-range by temperature bucket
  * Visualisations:
    * Temperature vs average glucose (line or scatter)
    * Temperature vs TIR%
  * Future extensions:
    * Intraday temperature vs glucose (requires intraday weather data)
    * Interaction with activity (steps × temperature × glucose)
    * Lagged effects (temperature today vs glucose next day)
  * Data requirements:
    * External weather API (e.g. location-based historical temperature)
    * Or manual CSV import

---

## 🧱 Phase 5 — Data Layer Expansion

### Activity → Database (`app/db/models.py`)

* [ ] Add `activity_intraday` table

  * Fields:

    * `recorded_at` (datetime)
    * `steps`
    * `source`

* [ ] Add calorie fields to `activity_intraday`

  * Fields:
    * `calories_burned`

---

### Activity → Importer (`app/services/activity/fitbit_importer.py`)

* [ ] Add Intraday Import

  * Pull minute / interval data from Fitbit API
  * Persist to `activity_intraday`

* [ ] Add Calorie Burn Import

  * Pull calorie expenditure from Fitbit API
  * Support:
    * daily total calories (initial)
    * intraday calorie burn (preferred)
  * Persist to database

---

### Activity → Service Layer

* [ ] Intraday Aggregation Functions

  * Steps by hour
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

---

## 🏋️ Phase 7 — Workout Module

### Workout → Database Layer

* [ ] Add workout/session model
  * Fields:
    * date
    * workout_type
    * duration_minutes
    * notes
    * perceived_effort

### Workout → Service Layer

* [ ] Add workout summary metrics
  * total sessions
  * weekly sessions
  * average duration
  * most recent workout

### Workout → UI Layer

* [ ] Build Workout tab
  * Add workout entry form
  * Add workout history table
  * Add summary cards
  * Add basic trend chart

## 🍽️ Phase 8 — Nutrition Module

### Nutrition → Database Layer

* [ ] Add nutrition / meal model
  * Fields:
    * recorded_at
    * meal_event
    * carbs_g
    * calories
    * notes

### Nutrition → Service Layer

* [ ] Add nutrition summary metrics
  * total carbs by day
  * carbs by meal event
  * average daily carbs
  * calorie totals where available

### Nutrition → UI Layer

* [ ] Build Nutrition tab
  * Add meal entry form
  * Add meal history table
  * Add summary cards
  * Add carbs-by-meal-event chart

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

* [ ] Add HomeTab navigation tests
  * Glucose card navigates to Glucose tab
  * Activity card navigates to Activity tab
  * Home cards render live service-layer summaries

### Test Infrastructure

* [ ] Add pytest-qt support for UI interaction tests
  * Provide shared `qapp` / `qtbot` fixtures
  * Mock service-layer calls to avoid database dependency
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

- Package RigLog as a native `.app` bundle
- Allow the app to be launched from Finder and the Applications folder
- Add a proper app icon and bundle metadata
- Ensure bundled assets load correctly, including branding and QSS theme files
- Move writable app data out of the project directory
- Store the SQLite database in a user-safe macOS location, such as:
  - `~/Library/Application Support/RigLog/`
- Confirm Fitbit tokens and future settings persist correctly outside the repo
- Test CSV import, PDF export, charts, and tab navigation from the packaged app
- Document the packaged-app launch workflow in the README

### Notes

This phase should happen after the Glucose, Activity, Workout, and Nutrition panels are functionally complete.
