# ⚡ SmartGrid AI — Full-Stack Monitoring Pipeline

An end-to-end **Machine Learning + Real-Time Dashboard system** for smart grid monitoring, fault detection, and intelligent load management.

This project combines **deep learning, physics-based validation, and real-time streaming** to simulate and monitor electrical grid behavior with high accuracy and explainability.

---

## 🚀 Key Features

- 🔍 **Anomaly Detection** using LSTM Autoencoders  
- ⚡ **Physics Validation Layer (PINN-inspired)** enforcing electrical laws  
- 🌲 **Fault Classification** using Random Forest + SHAP explainability  
- 📡 **Live Telemetry Streaming** via WebSockets (1 Hz)  
- 🔔 **Real-Time Alerts** synced with Firebase Firestore  
- 📊 **Interactive Dashboard** built with React + Vite  

---

## 🧠 ML Architecture Overview

### 1. LSTM Autoencoder (Anomaly Detection)
- Trained **only on normal operating data**
- Uses reconstruction error (MSE) as anomaly score
- Operates on rolling time windows (48-timestep buffer)

---

### 2. PINN Constraint Layer (Physics-Based Validation)

Ensures predictions obey real-world electrical laws:

**Ohm’s Law**
|V_measured - I × R_nominal| / V_nominal


**Power Balance**

|P_active - V × I × pf| / P_nominal


**Thermal Limit**

(winding_temp - 0.7 × rated) / (0.3 × rated)


Outputs a normalized **[0,1] violation score**

---

### 3. Random Forest Fault Classifier

- **Input Features:**
  - 3 LSTM anomaly scores  
  - 5 PINN violation scores  
  - 6 raw telemetry features  

- **Output:**
  - Classifies into **6 fault types**

- **Explainability:**
  - Uses **SHAP TreeExplainer** for feature attribution

---

## 🏗️ Project Structure

### 🔧 Backend (ML + Simulation)

backend/
├── src/
│ ├── preprocess.py
│ ├── lstm_models.py
│ ├── pinn_validator.py
│ ├── fault_classifier_rf.py
│ ├── load_management.py
│ └── model_ensemble.py
├── data/raw/
├── models/saved/
├── train_all.py
└── requirements.txt


---

### 💻 Frontend (React + Vite Dashboard)

frontend/
├── public/
├── src/
│ ├── assets/
│ ├── charts/
│ ├── components/
│ ├── data/
│ ├── firebase/
│ ├── hooks/
│ ├── pages/
│ ├── services/
│ ├── App.jsx
│ └── main.jsx
├── package.json
└── vite.config.js



---

## ⚙️ Getting Started

### 1️⃣ Backend Setup (FastAPI + ML)

```bash
cd backend
pip install -r requirements.txt

# Start server (WebSocket + API)
uvicorn main:app --reload

cd frontend
npm install

# Start dev server
npm run dev
```

🔄 System Data Flow
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
 ┌───────────────┬────────────────┐
 ↓               ↓                ↓
WebSocket     Firebase        Logs
(Frontend)     Alerts


🛠️ Tech Stack
Backend
Python
FastAPI
TensorFlow / Keras
Scikit-learn
SHAP
Frontend
React
Vite
Recharts
Firebase
Data & Simulation
GridLAB-D
Kaggle Smart Meter Dataset
