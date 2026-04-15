# Future Work and Unimplemented Features

## Overview

While the current system successfully demonstrates temperature-based concrete maturity estimation, several planned features and improvements were not completed within the course timeline. These represent realistic and technically feasible extensions of the project.

---

## Unimplemented Features

### 1. Mobile Application Interface
- Currently, data is accessed using a generic BLE scanning app (nRF Connect)
- No dedicated user interface exists

**Future Implementation:**
- Develop a custom mobile app using Flutter or Android Studio
- Use BLE GATT services to:
  - display real-time strength values
  - log historical data
- Implement user-friendly visualization (graphs, alerts)

---

### 2. Corrosion Monitoring (pH Sensor)

**Goal:**
- Detect internal corrosion conditions within concrete

**Implementation Approach:**
- Integrate an embedded pH sensor
- Interface with MCU using analog or digital input
- Calibrate sensor against known pH standards
- Combine with temperature data for enhanced analysis

---

### 3. Crack Detection System

**Goal:**
- Detect structural cracks or stress development

**Implementation Approach:**
- Use strain gauges or piezoelectric sensors
- Measure deformation or vibration changes
- Interface via ADC channels on MCU
- Apply threshold-based or signal-processing methods

---

## System-Level Improvements

### 4. Improved Power Management
- Optimize sleep cycles of MCU and BLE module
- Implement deeper low-power modes
- Reduce advertising duty cycle further

---

### 5. Robust Encapsulation

**Problem Observed:**
- System failure after prolonged exposure in concrete

**Solution:**
- Use waterproof epoxy or industrial-grade encapsulation
- Add conformal coating to PCB
- Improve sealing of casing

---

### 6. Fault Detection and Recovery

**Current Limitation:**
- No way to diagnose system failure remotely

**Future Approach:**
- Implement watchdog timers
- Add error flags in BLE transmission
- Store fault logs in flash memory

---

### 7. Multi-Sensor Integration

- Combine:
  - temperature
  - pH
  - strain
- Provide a more comprehensive structural health profile

---

## Scalability and Deployment

### 8. Multi-Node Network

- Deploy multiple sensor nodes across a structure
- Use BLE mesh or gateway-based architecture
- Centralize data collection

---

## Conclusion

The current system forms a strong foundation for a full-scale structural health monitoring solution. The proposed extensions are practical and build directly on the existing hardware and firmware architecture.
