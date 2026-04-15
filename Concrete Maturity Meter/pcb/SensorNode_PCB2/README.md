# Sensor Node PCB – Layout and Electrical Design

## Board Specifications

- Dimensions: 18.5 mm × 16 mm  
- Layers: 2-layer PCB  
- Stackup: Top (components + signals), Bottom (ground plane)  

---

## Layout Strategy

The sensor node PCB is designed for minimal footprint and simplicity, with all components placed to ensure short signal paths and stable operation.

### Placement considerations:
- Temperature sensor placed centrally to ensure uniform thermal exposure
- Pull-up resistors placed close to sensor pins
- Decoupling capacitor placed directly adjacent to sensor VDD pin
- Connector placed at board edge for straightforward interfacing

---

## Power Routing

- VDD routed directly from connector to sensor with minimal trace length
- Single decoupling capacitor used to stabilize supply
- Ground plane implemented on bottom layer for noise suppression

---

## Signal Routing

### I²C Lines (SDA, SCL)
- Routed as short traces between connector and sensor
- Avoided unnecessary vias to reduce impedance and noise
- Maintained consistent spacing between SDA and SCL

---

## Via Usage

- Minimal vias used due to small board size
- Only used where routing on top layer was not feasible
- Ground vias used to connect pads to ground plane

---

## Grounding Strategy

- Continuous ground plane on bottom layer
- Direct connection from sensor GND pin to ground plane
- Ensures stable reference for I²C communication

---

## Manufacturing Considerations

- Component sizes:
  - Resistors: 0805
  - Capacitors: 0603
- Layout optimized for hand soldering despite compact size
- Short trace lengths reduce susceptibility to noise

---

## Known PCB-Level Issues

- Very compact layout reduced routing flexibility
- Close spacing between components required careful soldering
- Limited mechanical robustness due to small board area
- No dedicated shielding or encapsulation provision on PCB

---

## Summary

The sensor node PCB is optimized for compactness and simplicity, focusing on reliable temperature sensing and stable I²C communication. The layout minimizes signal path lengths and ensures proper power decoupling within a constrained footprint.
