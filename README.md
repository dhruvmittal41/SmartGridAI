# ⚡ SmartGrid AI — Full-Stack Monitoring Pipeline

An end-to-end **Machine Learning + Real-Time Dashboard system** for smart grid monitoring, fault detection, and intelligent load management. This project combines **deep learning, physics-based validation, and real-time streaming** to simulate and monitor electrical grid behavior with high accuracy and explainability.

---

## 🚀 Key Features

- 🔍 **Anomaly Detection** — LSTM Autoencoders trained on normal operating data
- ⚡ **Physics Validation** — PINN-inspired layer enforcing Ohm's Law, power balance, and thermal limits
- 🌲 **Fault Classification** — Random Forest with SHAP explainability
- 📡 **Live Telemetry Streaming** — WebSocket-based pipeline at 1 Hz
- 🔔 **Real-Time Alerts** — Synced with Firebase Firestore
- 📊 **Interactive Dashboard** — Built with React + Vite

---

## 🧠 ML Architecture

### 1. LSTM Autoencoder — Anomaly Detection

- Trained **only on normal operating data**
- Uses **reconstruction error (MSE)** as the anomaly score
- Operates on a rolling **48-timestep buffer**

### 2. PINN Constraint Layer — Physics Validation

Validates predictions against real-world electrical laws and returns a normalized **[0, 1] violation score**:

| Constraint | Formula |
|---|---|
| **Ohm's Law** | `\|V_measured − I × R_nominal\| / V_nominal` |
| **Power Balance** | `\|P_active − V × I × pf\| / P_nominal` |
| **Thermal Limit** | `(T_winding − 0.7 × T_rated) / (0.3 × T_rated)` |

### 3. Random Forest Fault Classifier

**Input features (14 total):**
- 3 LSTM anomaly scores
- 5 PINN violation scores
- 6 raw telemetry features

**Output:** Classifies faults into **6 categories**

**Explainability:** SHAP `TreeExplainer` for per-prediction feature attribution

---

## 🔄 System Data Flow

```
[Simulation / Sensors]
         ↓
 [Preprocessing Layer]
         ↓
 [LSTM Autoencoder → Anomaly Score]
         ↓
 [PINN Validator → Physics Score]
         ↓
 [Random Forest → Fault Classification]
         ↓
 ┌───────────────┬──────────────┐
 ↓               ↓              ↓
WebSocket     Firebase        Logs
(Dashboard)    Alerts
```

---

## 🏗️ Project Structure

### Backend (`backend/`)

```
backend/
├── src/
│   ├── preprocess.py
│   ├── lstm_models.py
│   ├── pinn_validator.py
│   ├── fault_classifier_rf.py
│   ├── load_management.py
│   └── model_ensemble.py
├── data/
│   └── raw/
├── models/
│   └── saved/
├── train_all.py
└── requirements.txt
```

### Frontend (`frontend/`)

```
frontend/
├── public/
├── src/
│   ├── assets/
│   ├── charts/
│   ├── components/
│   ├── data/
│   ├── firebase/
│   ├── hooks/
│   ├── pages/
│   ├── services/
│   ├── App.jsx
│   └── main.jsx
├── package.json
└── vite.config.js
```

---

## ⚙️ Getting Started

### 1. Backend — FastAPI + ML

```bash
cd backend
pip install -r requirements.txt

# Start the WebSocket + REST API server
uvicorn main:app --reload
```

### 2. Frontend — React + Vite

```bash
cd frontend
npm install

# Start the development server
npm run dev
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python, FastAPI, TensorFlow/Keras, Scikit-learn, SHAP |
| **Frontend** | React, Vite, Recharts, Firebase |
| **Data & Simulation** | GridLAB-D, Kaggle Smart Meter Dataset |
