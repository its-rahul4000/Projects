# User Manual – Concrete Monitoring System

## 1. Introduction

This system is designed to monitor the curing of concrete by measuring temperature and calculating compressive strength using the maturity method.

The device is embedded inside concrete and wirelessly transmits data using Bluetooth Low Energy (BLE).

---

## 2. Target Audience

- Civil engineers
- Construction site personnel
- Researchers monitoring concrete curing

---

## 3. System Components

- Sensor Node (temperature sensing unit)
- Main Board (processing + BLE transmission)
- Battery (3.7V LiPo)
- Embedded firmware

---

## 4. Prerequisites

- Smartphone with Bluetooth capability
- BLE scanning application (recommended: nRF Connect)

---

## 5. Setup Instructions

### Step 1: Assembly
- Ensure the device is fully assembled and battery is connected
- Verify that connections between sensor and main board are secure

---

### Step 2: Embedding in Concrete
- Place the device inside wet concrete during pouring
- Ensure proper orientation and full embedding

---

### Step 3: Power On
- The system powers on automatically when the battery is connected

---

## 6. Operation

### Step 1: Open BLE App
- Install and open **nRF Connect**

---

### Step 2: Scan for Device
- Start scanning for nearby BLE devices
- Look for device name: "Comp Strength"


---

### Step 3: Connect
- Select the device from the list
- Establish BLE connection

---

### Step 4: Read Data
- Navigate to available services
- Read transmitted value:
- Concrete compressive strength (in MPa)

---

## 7. Expected Output

- Real-time strength value based on temperature data
- Stable readings after sufficient curing time

---

## 8. Troubleshooting

| Problem | Possible Cause | Solution |
|--------|--------------|---------|
| Device not visible | BLE not advertising | Move closer |
| No data received | Connection issue | Reconnect |
| Sudden failure | Environmental damage | Inspect hardware |

---

## 9. Safety Notes

- Device is not waterproof unless properly sealed
- Avoid mechanical stress during embedding
- Ensure battery is handled safely

---

## 10. Summary

This system provides a wireless and embedded solution for monitoring concrete curing in real-time. Users can easily access structural strength data using a smartphone without requiring physical access to the embedded device.
