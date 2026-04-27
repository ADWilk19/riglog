# RigLog Backlog 📋

This backlog is organised by architectural layer and implementation priority.

---

## 🔥 Phase 1 — Activity Module Completion (High Impact, Low Effort)

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

* [~] Refactor Summary Cards

  * Home cards now implemented
  * Activity tab cards pending full alignment with service layer

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

* [ ] Auto-refresh on Activity Sync
  * Update Home cards when new data is imported

### System

* [x] Fitbit OAuth token auto-refresh

  * Prevent reauthentication on expiry
  * Persist refreshed tokens automatically

* [ ] Background Sync

  * Scheduled Fitbit sync
  * Update `last_synced` automatically

---

## 🧠 Phase 2 — Insight Layer Expansion

### Activity → Service Layer

* [ ] Rolling Goal Adherence

  * e.g. last 7 / 14 days
  * Return:

    * `goal_adherence_last_7`
    * `goal_adherence_last_14`

* [ ] Weekly Summary Metrics

  * Return:

    * `best_week_steps`
    * `worst_week_steps`

* [ ] Step Consistency Metric

  * Std deviation of daily steps
  * Optional:

    * coefficient of variation (CV)

---

### Activity → UI Layer

* [ ] Weekly Summary Card(s)

  * Best week
  * Worst week

* [ ] Consistency Indicator

  * Label:

    * “Consistent”
    * “Variable”

---

## 📊 Phase 3 — Interaction Enhancements

### 🩸 Glucose — UI Layer

* [ ] Range-Based Meal Event Breakdown

  * When a glucose range card is selected (e.g. Low, High, Hyper):
    * Display count of readings grouped by meal event
    * Sorted chronologically (Pre → Post events)
  * Only visible when a range filter is active
  * Initial version:
    * simple table (meal event → count)
  * Future:
    * percentage breakdown by meal event

---

### Activity → Chart Layer

* [ ] Click-to-Select Day

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

## 🧪 Phase 7 — Advanced Features

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

## 🧭 Notes

* Prioritise features that:

  * reuse existing service-layer outputs
  * avoid expanding data model prematurely

* Intraday analysis should only be implemented once:

  * Activity module is feature-complete at daily level

* Maintain separation of concerns:

  * Importers → data ingestion
  * Services → calculations
  * UI → rendering only
