# Smart Grid AI — GridLAB-D Simulation Guide

## Quick Start (3 commands)

```bash
cd smartgrid_sim/
chmod +x run_simulations.sh diagnose_glm.sh
./run_simulations.sh
```

---

## What Gets Generated

| File | Source | Rows | Used For |
|---|---|---|---|
| `data/sub_bus_11kV.csv` | substation_sim.glm | 4,320 | LSTM-Sub: substation voltage/current |
| `data/feeder1_bus.csv` | substation_sim.glm | 4,320 | LSTM-Sub: feeder loading |
| `data/feeder2_bus.csv` | substation_sim.glm | 4,320 | LSTM-Sub: feeder loading |
| `data/feeder3_bus.csv` | substation_sim.glm | 4,320 | LSTM-Sub: industrial feeder |
| `data/tx_primary_11kV.csv` | transformer_sim.glm | 4,320 | LSTM-Trans: primary side |
| `data/tx_lv_415V.csv` | transformer_sim.glm | 4,320 | LSTM-Trans: LV bus + thermal |
| `data/meter_01.csv`–`meter_12.csv` | meter_sim.glm | 288 ea | LSTM-Meter: consumption |
| `data/meter_feeder_head.csv` | meter_sim.glm | 288 | LSTM-Meter: injection reference |
| `dataset/dataset_substation.csv` | fault_injector.py | 4,320 | **LSTM-Sub training** |
| `dataset/dataset_transformer.csv` | fault_injector.py | 4,320 | **LSTM-Trans training** |
| `dataset/dataset_meters.csv` | fault_injector.py | 288 | **LSTM-Meter training** |

---

## Fault Labels in the Datasets

| Label | Fault Type | Window | Dataset |
|---|---|---|---|
| 0 | normal | everywhere else | all |
| 1 | feeder_overload | Day 1, 18:00–20:30 | substation |
| 2 | voltage_sag | Day 1, 14:00–14:45 | substation |
| 3 | transformer_overload | Day 2, 19:00–23:00 | transformer |
| 4 | energy_theft | Day 2 22:00 → Day 3 end | meters |
| 5 | undervoltage | Day 3, 17:00–21:00 | meters |

---

## Common GridLAB-D Errors and Fixes

### "property 'measured_voltage_A' not found"
Different GridLAB-D versions use different property names.
**Fix**: Run `./diagnose_glm.sh` then check which names work:
```bash
gridlabd --modhelp powerflow | grep voltage   # list voltage properties
gridlabd --modhelp powerflow | grep current   # list current properties
```

Alternative recorder properties (try these if the named ones fail):
- `voltage_A` instead of `measured_voltage_A`
- `current_A` instead of `measured_current_A`
- `power_A` instead of `measured_real_power`

### "NR solver did not converge"
**Fix**: Reduce the load size in your load objects, or add voltage support:
```glm
// In the offending load object, try reducing power:
constant_power_A 200000+100000j;   // was too high, reduce
// OR add shunt capacitor for reactive support:
object capacitor {
    parent bus_f1_end;
    phases ABCN;
    pt_phase ABCN;
    capacitor_A 0.5 MVAr;
    capacitor_B 0.5 MVAr;
    capacitor_C 0.5 MVAr;
    control MANUAL;
    switchA CLOSED;
    switchB CLOSED;
    switchC CLOSED;
}
```

### "object 'meter' does not exist"
Your GridLAB-D build may not include the meter class.
**Fix**: Replace `object meter` with `object node` everywhere.
Recorders on nodes support: `voltage_A`, `voltage_B`, `voltage_C`
(Current must then be recorded on line objects instead)

### "overhead_line_conductor not found" or spacing errors
**Fix**: Make sure `module powerflow;` is listed BEFORE the conductor objects.
Also confirm your GridLAB-D has the powerflow module:
```bash
gridlabd --modhelp powerflow
```

### Simulation runs but data/ files are empty
Recorder `interval` might be wrong or `limit 0` not supported.
**Fix**: Remove `limit 0;` from recorder objects and try `limit -1;` or leave it out entirely.

### Complex number parsing issues in fault_injector.py
GridLAB-D versions write complex numbers differently:
- v3.x: `+6350.85+0.00j V`
- v4.x: `6350.85+0.00i`
- Some builds: just `6350.85`

The `parse_complex_col()` function in `fault_injector.py` handles all three.
If you still get NaN columns, add a print statement:
```python
print(df.iloc[:3])  # see what the raw strings look like
```

---

## Adjusting Load Sizes

If the NR solver diverges, your loads are probably too large for the line impedance.
Rule of thumb for 11kV ACSR Dog:
- Max load per feeder at 3km: ~1.5 MVA (at 0.85 PF → ~1.3 MW)
- If you need more, either shorten the line or use a thicker conductor

Current GLM loads by feeder:
- Feeder 1 (residential): 2.1 MW peak — borderline, reduce if issues
- Feeder 2 (commercial): 1.5 MW peak — comfortable
- Feeder 3 (industrial): 3.0 MW peak — may need voltage support

To reduce: change the base MW in the load `constant_power_A` lines.

---

## Running Individual Simulations

```bash
# Just substation
gridlabd substation_sim.glm --warn 2>&1 | tee logs/sub.log

# Just transformer  
gridlabd transformer_sim.glm --warn 2>&1 | tee logs/tx.log

# Just meters
gridlabd meter_sim.glm --warn 2>&1 | tee logs/meter.log

# Just fault injection (if GLM already run)
python3 fault_injector.py
```

---

## Extending the Simulation

### Add more fault types
In `fault_injector.py`, add to `FAULT_WINDOWS`:
```python
"capacitor_bank_failure": {
    "start_min": (48 + 10) * 60,
    "end_min":   (48 + 12) * 60,
    "label":     6,
    "fault_type": "capacitor_failure",
},
```
Then inject it by modifying power factor in the relevant function.

### Extend to 7 days
In all GLM files, change:
```glm
stoptime '2024-01-08 00:00:00';  // was 2024-01-04
```

### Add weather-correlated loads
Download hourly temperature data for your region and use a `player` object
to vary load with temperature (critical for AC load correlation):
```glm
object player {
    name temp_player;
    file weather_temperature.csv;
    property temperature;
    loop 0;
}
// Then reference in load schedule...
```
