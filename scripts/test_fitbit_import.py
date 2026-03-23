from app.services.activity.fitbit_importer import FitbitImporter

importer = FitbitImporter()
rows = importer.import_daily_steps("2026-03-01", "2026-03-23")
print(f"Imported/updated {rows} daily activity rows.")
