# AIR-SHIELD dashboard

Interactive Streamlit dashboard for the AIR-SHIELD city air-quality project. It connects the cleaned daily dataset and Person 2 hotspot outputs included in the supplied ZIP.

## Run locally (Windows PowerShell)

Open a terminal in the project root (the folder containing `requirements.txt`), then run:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py
```

In VS Code, select `.venv\Scripts\python.exe` as the Python interpreter if you want to run or debug the app from the editor. Installing packages into a different interpreter will not fix a `ModuleNotFoundError` in the interpreter currently selected by VS Code.

## Integrated project files

- `data/processed/cleaned_air_quality.csv` — city/day pollutant and AQI data.
- `data/processed/city_hotspot_results.csv` — Person 2 city ranking and risk labels.
- `data/processed/pollution_hotspots.csv` — Person 2 ranked hotspot list.

The Hotspots page uses Person 2's saved rankings. The Forecast page currently displays observed history and looks for a Person 3 forecast CSV under `results/` with `forecast` in its filename. No forecast output was present in the supplied archives. Put the forecast output there and share its column names so it can be mapped without altering the model.

## Intervention priority score

The demo score is 0–100: 40% normalized mean AQI severity + 30% share of days with AQI ≥ 201 + 20% recent spike score + 10% population exposure. The recent spike compares the latest 30-day mean AQI with the preceding 90-day mean and caps increases at 100. Population was not provided; its score is set to a neutral 50 for every city, so it cannot change the relative ranking. Replace that neutral value with a documented population/exposure measure before using the ranking for real-world resource allocation.

## Data scope

All observations in this project are historical. The dashboard does not claim to show live measurements or official alerts. Driver charts show statistical associations, not causal effects.
