# PCB Design – Concrete Sensor Node System

This directory contains the complete PCB design files for the embedded concrete monitoring system. The design is implemented using KiCad and consists of two separate boards:

1. **MainBoard_PCB1** – Processing + Communication Unit  
2. **SensorNode_PCB2** – Embedded Sensing Unit  

Each subfolder contains:
- Full KiCad project files (.kicad_sch, .kicad_pcb, etc.)
- `/pictures` folder with:
  - Front copper layer
  - Back copper layer
  - 3D render of PCB

---

# 🔧 Overview of System Architecture

The system is divided into two physically separated PCBs:

### 1. MainBoard_PCB1
Handles:
- Data acquisition from sensor node
- Data logging (external flash)
- Processing (maturity calculation)
- Wireless transmission via BLE

### 2. SensorNode_PCB2
Handles:
- Temperature sensing inside concrete
- Signal conditioning and transmission to main board

---

# 🔋 Power System

- **Battery:** 3.7V LiPo (1200 mAh)
- **Regulation:** 3.3V LDO regulator (897xno58)

### Design considerations:
- Low power operation for long-term deployment (~2 months target)
- Local decoupling capacitors placed near IC supply pins
- Separate grounding strategy using ground plane (2-layer PCB)

---

# 🧠 MainBoard_PCB1 – Detailed Description

## Functional Blocks

### 1. Microcontroller + BLE Module
- Central processing unit for:
  - Reading sensor data
  - Performing maturity calculations
  - Managing memory and BLE communication
- BLE used for:
  - Periodic advertising
  - On-demand connection when receiver is nearby

---

### 2. External Flash Memory
- Stores:
  - Raw temperature readings
  - Intermediate computation data
- Interface:
  - SPI communication with MCU

---

### 3. Programming Interface (JTAG)
- Exposed header for:
  - Firmware upload
  - Debugging
- Becomes unused after deployment

---

### 4. Sensor Interface Connector
- Physical connection to SensorNode_PCB2
- Carries:
  - SDA
  - SCL
  - VDD
  - GND
  - ALT (not used)

---

### 5. Power Regulation
- LDO converts 3.7V battery to 3.3V
- Decoupling capacitors placed at:
  - Regulator output
  - MCU supply pins
  - Flash memory supply

---

# 🌡️ SensorNode_PCB2 – Detailed Description

## Functional Blocks

### 1. Temperature Sensor (TMP1075)
- Measures concrete temperature
- Interface:
  - I²C (SCL, SDA)
- Accuracy:
  - ±0.1–0.5°C

---

### 2. Pull-up Network
- I²C lines use 5kΩ pull-up resistors
- Ensures stable communication

---

### 3. Connector Interface
- Connects to main board
- Provides:
  - Power (VDD, GND)
  - I²C communication lines

---

# 📐 PCB Design Specifications

| Parameter | Value |
|----------|------|
| Layers | 2-layer PCB |
| Routing strategy | Top: signals, Bottom: ground plane |
| Trace width | 0.5 mm |
| Clearance | 0.50 mm |
| Via size | 1 mm |

---

# 📡 RF Design Considerations (BLE)

- Antenna region kept **free of copper, vias, and traces**
- Ground plane excluded under antenna
- Ensures minimal signal attenuation

---

# ⚠️ Known Issues and Limitations

### 1. Tight Clearance Near Module Pads
- **Issue:** DRC clearance violations around BLE module pads
- **Cause:** Manufacturer-defined footprint uses smaller spacing than possible by printing lab
- **Workaround:** Changed slightly the shape op copper pads 
- **Impact:** No functional impact expected

---

### 2. No-Net Pads in BLE Module
- **Issue:** Some pads flagged as `<no net>`
- **Cause:** Mechanical or grounding pads in module footprint
- **Workaround:** Assigned to GND or ignored in DRC
- **Impact:** No functional impact

---

### 3. Via Placement Constraints
- **Issue:** Vias flagged near dense routing regions
- **Cause:** Limited routing space on compact board
- **Workaround:** Adjusted via size and placement
- **Impact:** Minor layout complexity, no functional issue

---

### 5. Hand Soldering Constraints
- **Issue:** Small SMD components (0402/0603) may be difficult to solder
- **Workaround:** Selected larger packages where possible (0603/0805)
- **Impact:** Improves manufacturability

---

# 🧩 Design Methodology

Component selection and values were determined using:
- Manufacturer datasheets
- Standard I²C and SPI design guidelines
- Low-power embedded system design principles

---

# 📂 File Organization
```Text
/pcb
│
├── MainBoard_PCB1
│ ├── *.kicad_sch
│ ├── *.kicad_pcb
│ └── pictures/
│ ├── frontcopper.png
│ ├── backcopper.png
│ └── 3d_front.png
│ └── 3d_back.png
│
├── SensorNode_PCB2
│ ├── *.kicad_sch
│ ├── *.kicad_pcb
│ └── pictures/
│ ├── frontcopper.png
│ ├── backcopper.png
│ └── 3d_front.png
│ └── 3d_back.png
```


---

# 📌 Summary

This PCB system implements a **low-power embedded sensing solution** for monitoring concrete curing conditions using:

- Distributed sensing (sensor node)
- Centralized processing (main board)
- BLE-based wireless data retrieval
- On-board data logging

The design emphasizes:
- Low power consumption
- Reliable communication
- Manufacturability
- Modular architecture

---
