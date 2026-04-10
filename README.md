⚡ SmartGrid AI — Full-Stack Monitoring Pipeline
An end-to-end Machine Learning pipeline and real-time dashboard for smart grid monitoring, fault detection, and load management.

This project utilizes a multi-model ML architecture (LSTM Autoencoders + PINN Constraints + Random Forest) on the backend, streaming live telemetry via WebSockets to a React/Vite frontend, with high-priority alerts synced instantly via Firebase Firestore.

📂 Project Structure
Backend (Machine Learning & Simulator)
Plaintext
backend/
├── src/
│   ├── preprocess.py            # Data formatting → numpy arrays
│   ├── lstm_models.py           # LSTM autoencoders (per asset type)
│   ├── pinn_validator.py        # Physics constraint checker (Ohm, KCL)
│   ├── fault_classifier_rf.py   # Random Forest + SHAP explainability
│   ├── load_management.py       # Demand forecast + operator suggestions
│   └── model_ensemble.py        # Unified prediction interface
├── data/raw/                    # Training datasets (GridLAB-D & Kaggle)
├── models/saved/                # Compiled .keras and .pkl models
├── train_all.py                 # One-command training pipeline
└── requirements.txt
Frontend (React + Vite Dashboard)
Plaintext
frontend/
├── public/
├── src/
│   ├── assets/                  # Static images and SVGs
│   ├── charts/                  # Recharts components (EnergyChart.jsx)
│   ├── components/              # UI Panels (AlertsPanel, MetricsPanel, Maps)
│   ├── data/                    # Static topology and mapping data
│   ├── firebase/                # Firebase config.js
│   ├── hooks/                   # useGridStream (WS) & useFirebaseAlerts
│   ├── pages/                   # Main views (Dashboard, Landing, CityView)
│   ├── services/                # Backend API controllers
│   ├── App.jsx                  # Main application router
│   └── main.jsx                 # React DOM entry
├── package.json
└── vite.config.js
🚀 Getting Started
1. Backend Setup (Python)
Navigate to your backend directory, install the dependencies, and start the FastAPI server:

Bash
pip install -r requirements.txt

# Run the live simulation & WebSocket server (port 8000)
uvicorn main:app --reload
2. Frontend Setup (React)
Open a new terminal, navigate to your frontend directory, and install the NPM packages:

Bash
npm install

# Start the Vite development server
npm run dev
3. Firebase Configuration
Ensure your src/firebase/config.js is populated with your Firebase Web App credentials to enable real-time alert syncing.

🧠 ML Model Training
You can retrain the entire model suite across the pipeline using a single command in the backend directory.

Full Training (50 epochs, ~10-15 min on CPU):

Bash
python train_all.py \
  --substation  data/raw/substation_sim.csv \
  --transformer data/raw/transformer_sim.csv \
  --meter_glab  data/raw/meter_feeder_sim.csv \
  --kaggle      data/raw/smart_meter_india.csv
🏗️ Architecture Notes
The Data Flow
Simulation: The Python backend generates realistic grid telemetry or reads from hardware.

Prediction: Data passes through the GridPredictor (LSTM + Random Forest).

Telemetry Stream: Live metrics (Voltage, Current, Power) are blasted to the React frontend at 1Hz via WebSockets (useGridStream.js).

Alerts: If an anomaly is verified, the backend writes a critical alert to Firebase Firestore.

Dashboard UI: The React app listens to Firestore (useFirebaseAlerts.js) and instantly displays the fault in the Alerts Panel.

LSTM Anomaly Detection
Training Strategy: Models are trained only on normal data (fault_label=0).

Inference: The Mean Squared Error (MSE) between the input sequence (rolling 48-tick buffer) and the reconstructed sequence acts as the anomaly score.

PINN (Physics-Informed) Constraint Layer
This layer calculates a composite [0,1] physics violation score based on real-world electrical laws:

Ohm's Law: |V_measured - I × R_nominal| / V_nominal

Power Balance: |P_active - V × I × pf| / P_nominal

Thermal Limit: (winding_temp - 0.7 × rated) / (0.3 × rated)

Random Forest Classifier
Input Vector: 14 total features (3 LSTM scores + 5 PINN scores + 6 raw metrics).

Output: Classifies into 6 distinct fault_type categories.

Explainability: Utilizes SHAP TreeExplainer to extract the top feature contributions for every prediction.
