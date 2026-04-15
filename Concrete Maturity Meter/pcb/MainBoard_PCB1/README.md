# MainBoard PCB – Layout and Electrical Design

## Board Specifications

- Dimensions: 38.5 mm × 23.76 mm  
- Layers: 2-layer PCB  
- Stackup: Top (signal + components), Bottom (ground plane dominant)  

---

## Layout Strategy

The board is designed around a dense central module (CC2650MODA), with peripheral components arranged to minimize trace length and routing congestion.

### Placement considerations:
- BLE module placed near board edge to preserve antenna radiation
- Flash memory placed close to MCU pins to reduce SPI trace length
- LDO regulator positioned near battery input pads
- Decoupling capacitors placed within 2–3 mm of IC power pins
- JTAG header placed at edge for accessibility during debugging

---

## Power Routing

- Battery input routed directly to LDO input using wider traces (0.5 mm)
- 3.3V output distributed using short, low-impedance paths
- Ground plane implemented on bottom layer for:
  - return current path
  - noise reduction
- Local decoupling applied at:
  - MCU supply pins
  - flash memory supply

---

## Signal Routing

### I²C Lines (Sensor Interface)
- Routed as short parallel traces
- Pull-up resistors placed close to MCU side

### SPI Lines (Flash Memory)
- Routed with minimal length mismatch
- Avoided crossing splits in ground plane
- Kept away from high-current paths

---

## Via Usage

- Used for:
  - layer transitions during routing congestion
  - connecting top signals to bottom ground plane
- Typical via size:
  - Diameter: 1 mm

Vias are avoided near high-density pads to prevent DRC violations.

---

## Grounding Strategy

- Continuous ground plane on bottom layer
- Multiple stitching vias used to connect ground pads to plane
- Ground return paths kept short and uninterrupted

---

## Antenna Keepout (Critical)

- Region under BLE antenna kept completely free of:
  - copper
  - vias
  - traces
- No ground plane beneath antenna section

This is essential to maintain RF performance.

---

## Manufacturing Considerations

- Footprints selected considering hand soldering:
  - Resistors: 0603 / 0805
  - Capacitors: 0603 / 0805

---

## Known PCB-Level Issues

- Tight pad spacing within BLE module footprint caused DRC clearance violations
- Some pads inside module footprint required net reassignment to avoid false errors
- Dense routing near module required multiple vias, increasing layout complexity
- Small component sizes made manual assembly difficult

---

## Summary

The PCB design prioritizes compactness while maintaining signal integrity, stable power delivery, and RF performance. Layout decisions were driven by the constraints imposed by the BLE module and the need for reliable operation in a small form factor.
