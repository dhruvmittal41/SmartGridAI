# SmartGrid AI — ML Pipeline

## Project Structure
```
smartgrid_ai/
├── src/
│   ├── preprocess.py         ← All 4 data formats → numpy arrays
│   ├── lstm_models.py        ← 4 LSTM autoencoders (one per asset type)
│   ├── pinn_validator.py     ← Physics constraint checker (Ohm, KCL, thermal)
│   ├── fault_classifier_rf.py← Random Forest + SHAP explainability
│   ├── load_management.py    ← Demand forecast + operator suggestions
│   └── model_ensemble.py     ← Unified prediction interface
├── tests/
│   └── test_pipeline.py      ← 25+ tests covering all modules
├── train_all.py              ← One-command training pipeline
└── requirements.txt
```

## Setup
```bash
pip install -r requirements.txt
```

## Place your data files
```
data/raw/
  substation_sim.csv      ← GridLAB-D substation output
  transformer_sim.csv     ← GridLAB-D transformer output
  meter_feeder_sim.csv    ← GridLAB-D meter/feeder output
  smart_meter_india.csv   ← Kaggle Bareilly/Mathura dataset
```

## Train all models
```bash
# Full training (50 epochs, ~10-15 min on CPU)
python train_all.py \
  --substation  data/raw/substation_sim.csv \
  --transformer data/raw/transformer_sim.csv \
  --meter_glab  data/raw/meter_feeder_sim.csv \
  --kaggle      data/raw/smart_meter_india.csv

# Quick test run (5 epochs, ~2 min)
python train_all.py --epochs 5 --rf_trees 50 \
  --substation  data/raw/substation_sim.csv \
  --transformer data/raw/transformer_sim.csv \
  --meter_glab  data/raw/meter_feeder_sim.csv \
  --kaggle      data/raw/smart_meter_india.csv
```

## Run tests
```bash
python -m pytest tests/ -v
```

## Run individual module tests
```bash
python src/preprocess.py        # smoke test preprocessor
python src/pinn_validator.py    # physics law validation
python src/lstm_models.py       # model build test
python src/fault_classifier_rf.py  # RF + SHAP
python src/load_management.py   # suggestions + theft
python src/model_ensemble.py    # full ensemble smoke test
```

## Model outputs (after training)
```
models/saved/
  substation_lstm.keras
  transformer_lstm.keras
  meter_lstm.keras
  meter_gridlab_lstm.keras
  rf_classifier.pkl
  rf_label_encoder.pkl
  demand_forecaster.pkl
  scaler_substation.pkl
  scaler_transformer.pkl
  scaler_meter_glab.pkl
  scaler_kaggle_meter.pkl
```

## Architecture Notes

### LSTM Anomaly Detection
- Trained ONLY on normal (fault_label=0) data
- At inference: MSE between input and reconstruction = anomaly score
- High score → sequence deviates from learned normal behaviour
- Threshold at 95th percentile of normal training data errors

### PINN Constraint Layer
- Ohm's Law:     |V_measured - I×R_nominal| / V_nominal
- Power Balance: |P_active - V×I×pf| / P_nominal
- KCL:           (feeder_loss - expected_loss) / expected_loss
- Thermal:       (winding_temp - 0.7×rated) / (0.3×rated)
- Voltage Drop:  |ΔV_actual - I×Z| / V_nominal
- Composite:     weighted sum → single [0,1] physics violation score

### Random Forest Classifier
- Input: 3 LSTM scores + 5 PINN scores + 6 raw features = 14 features
- Output: fault_type (6 classes) + probabilities
- SHAP TreeExplainer → top-3 feature contributions per prediction
- OOB score used as free generalisation estimate

### Load Management Engine
- Rule thresholds: load>95% → P1 shed, load>80% → P2 warn
-                  voltage<0.90pu → P1 capacitor
-                  winding>120°C → P1 thermal
-                  loss_ratio>0.20 → P2 theft investigation
- Demand forecaster: Ridge regression on time + lag features
- 2-hour forecast → included in P1/P2 thresholds
