# Uber Demand Prediction Platform

A full-stack FastAPI + MongoDB (Motor) + Bootstrap 5 + Leaflet.js + Chart.js
application that serves real-time ride demand, fare, and cancellation-risk
predictions from a pre-trained ML model bundle (`uber_demand_model.joblib`).

## 1. Place your trained model

Copy your trained model artifact to:

```
trained_models/uber_demand_model.joblib
```

It must be a `joblib`-dumped Python dict with the keys:
`preprocessor`, `demand_model`, `value_model`, `cancel_model`,
`feature_names`, `demand_mapping`.

The `feature_names` list must match, in order, the raw columns produced by
the feature engineering step in `backend/app/ml/predictor.py`:

```
Vehicle_Type, Pickup_Location, Drop_Location, Payment_Method,
Ride_Distance, Avg_VTAT, Avg_CTAT, Driver_Ratings, Customer_Rating,
Hour, Day, Month, Weekday, Is_Weekend, Is_Peak_Hour, Distance_Category
```

If your training pipeline used different column names, rename them in
`engineer_features()` inside `backend/app/ml/predictor.py` to match exactly.

## 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configure environment

Copy `.env.example` to `.env` and set your own values:

```
MONGO_URI=mongodb://localhost:27017          # or your MongoDB Atlas URI
MONGO_DB_NAME=uber_demand_db
JWT_SECRET_KEY=replace-with-a-long-random-string
```

## 4. Run the app

```bash
uvicorn backend.app.main:app --reload --app-dir .
```

Or, from inside `backend/`:

```bash
cd backend
uvicorn app.main:app --reload
```

Visit:
- `http://127.0.0.1:8000/login` — sign in / register
- `http://127.0.0.1:8000/dashboard` — analytics dashboard
- `http://127.0.0.1:8000/predict` — run predictions
- `http://127.0.0.1:8000/docs` — interactive API docs (Swagger)

## 5. Package into a zip

```bash
python create_zip.py
```

This produces `UberDemandPrediction.zip` containing the full project
(excluding virtual environments, `__pycache__`, and any local `.env` file).

## Notes

- The model is loaded exactly once at startup inside the FastAPI `lifespan`
  handler (`backend/app/main.py` → `ModelBundle.instance().load(...)`). It is
  never retrained.
- Passwords are hashed with bcrypt (`passlib`); sessions use JWT bearer
  tokens stored in `localStorage` on the client and sent via the
  `Authorization: Bearer <token>` header.
- All predictions are persisted to the `predictions` collection in MongoDB
  and power both `/api/v1/history` and `/api/v1/analytics/stats`.
