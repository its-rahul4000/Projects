# 🏗️ Concrete Maturity Meter  
### *“Stethoscope for your Building”*  


## 👥 Team Members

| Name | Roll Number |
|------|------------|
| Rahul Kumar | 23B1212 |
| Khyati Singh | 23B1220 |
| S. Monica | 23B1243 |
| Khushi Chandak | 23B3920 |
| Arnav Ramteke | 23B1281 |

## 📂 Repository Structure

The project is organized into the following directories for clear separation of hardware, firmware, and documentation:

```text
├── 3d_models/          # 3D enclosure designs, STL files, and mechanical components
├── others/             # Additional supporting files and miscellaneous resources
├── pcb/                # PCB design files (KiCad project, schematics, layouts, renders)
├── reports/            # Project reports, presentations, and documentation
├── src/
│   └── CC2650/         # Firmware source code for CC2650 (BLE + sensing + flash)
├── bom.xls             # Bill of Materials (components, cost, and sourcing details)
```

## 📌 Problem Statement

- Concrete strength development depends strongly on **curing temperature and time**
- Existing monitoring methods are **slow, inefficient, and not real-time**

### ❌ Limitations of Current Methods

**Cylinder Compression Testing:**
- Destructive  
- Time-consuming  
- Not suitable for on-site decision making  

**Manual Temperature Logging:**
- Labor-intensive  
- Error-prone  
- Lacks continuous monitoring  

- No effective solution exists for **real-time, in-situ strength tracking**


## 💡 Proposed Solution

A **low-power embedded system** that:

- 🌡️ Measures internal concrete temperature  
- 🧠 Computes maturity index on MCU  
- 💾 Stores data in flash memory  
- 📡 Transmits strength (% maturity) via BLE  

👉 Enables **real-time, in-situ strength estimation** without destroying concrete.


## 🚀 Key Features

- Non-destructive monitoring  
- Real-time strength estimation  
- Ultra-low power operation (~3 months battery life)  
- Wireless BLE communication  
- Embedded inside concrete  


## ⚙️ System Architecture

### 🔄 Working Flow

1. System wakes from low-power sleep  
2. Temperature is measured using TMP1075 **every 10 minutes**  
3. Data is logged continuously over a **1-hour operational cycle**  
4. Data is stored in external flash (SPI)  
5. MCU computes maturity index  
6. BLE transmits data periodically:
   - **ON for 12 seconds**
   - **OFF (sleep) for 5 minutes**  
7. System returns to low-power sleep  


## 🧱 Hardware Overview

### 🔧 Components Used

| Component | Description |
|----------|------------|
| MCU + BLE | CC2650MODA |
| Temperature Sensor | TMP1075 |
| Flash Memory | W25Q32JV |
| Battery | 3.7V LiPo |
| LDO | 897xno58 |


## 📊 Block Diagram

- Sensor → MCU → Flash → BLE → Mobile App  

**Interfaces Used:**
- I2C → Temperature Sensor  
- SPI → Flash Memory  
- BLE → Wireless Communication  


## 🔋 Power Optimization

- Sleep-based operation  
- Event-driven firmware  
- Reduced BLE duty cycle  
- Optimized battery: 1200 mAh  

## 📡 BLE Communication Strategy

- Periodic advertising:
  - **12 sec ON**
  - **5 min OFF**
- Low duty cycle transmission  
- Automatic connection when receiver is nearby  




## 💻 SOURCE CODE (/src)

👉 Refer: `/src/README.md`

Includes:
- Installation steps  
- Build & flash instructions  
- BLE setup  
- Communication protocols (I2C, SPI, BLE)  
- Firmware architecture  


## 🖥️ PCB DESIGN (/pcb)

👉 Refer: `/pcb/README.md`

Includes:
- KiCad files  
- Schematic + layout  
- 3D renders  
- Hardware explanation  
- Known issues  


## 🧊 3D MODELS (/3d_models)

👉 Refer: `/3d_models/README.md`

Includes:
- STL/design files  
- Enclosure purpose  
- Assembly instructions  

## 📄 Methodology

Temperature data of concrete was recorded at **10-minute intervals** using an embedded sensor. The maturity index was calculated using the:

**Nurse-Saul equation**: M = Σ (T - T₀) × Δt

where `T₀ = -10°C` and `Δt = 1` hour and `T is the average temperature of all 6 readings per hour`

The maturity values were aggregated **hourly** and transformed using `ln(M)` to establish a linear relationship with compressive strength.

**Compressive Strength (MPa)**: Y = a + b · ln(M), 
Where a=−35.4926 and b= 7.5004

A **linear regression model** was developed using experimental strength values at **1, 3, and 7 days**

The model was then used to estimate strength development, and the results were compared with **hourly strength data** for validation.

## 🧪 Testing & Validation

### Temperature Testing
- High temperature: 40–110°C  
- Low temperature: ~0°C  

### BLE Testing
- Works up to ~8–9 cm inside concrete  

### System Testing
- Fully tested in embedded environment  


## ⚠️ Challenges & Solutions

| Challenge | Solution |
|----------|--------|
| High power consumption due to BLE and sensing | Optimized duty cycle, sleep modes, and event-driven firmware |
| Water ingress and harsh concrete environment | Epoxy sealing and protective casing |
| Size constraints for embedded deployment | Compact PCB design and component integration |
| BLE communication delay | Optimized advertising interval and transmission strategy |
| Sensor accuracy in extreme temperatures | Calibration and validation using controlled experiments |
| Reliable long-term data logging | Integrated external SPI flash memory |
| Power budget limitations | Recalculated and optimized battery capacity and components |
| Hardware durability under pressure | Reinforced casing and secure enclosure design |


## ⚠️ Key Risks

- BLE signal attenuation may reduce communication range in dense concrete  
- Inaccurate maturity estimation due to improper calibration curve  
- Long-term hardware degradation due to moisture, pressure, and alkaline environment  
- Battery depletion before expected operational lifetime  
- Data loss risk due to flash memory failure or corruption  
- Improper sealing may lead to system failure inside concrete  
- Environmental temperature variations affecting sensor readings  

## ⭐ Final Note

This project integrates hardware, firmware, and wireless systems to deliver a **real-world smart construction solution**.

