# Reflection: Learning, Challenges, and Team Experience

## Overview

This project involved designing and implementing a low-power embedded system for monitoring concrete curing through temperature-based maturity analysis. Over the 12-week course, we developed both hardware and firmware components, culminating in a functional prototype capable of sensing, processing, and transmitting data via BLE.

Our team consisted of:

- Rahul Kumar (23B1212) – Firmware and software testing  
- Khyati Singh (23B1220) – Casing design, hardware integration, testing  
- S. Monica (23B1243) – PCB design, circuitry, system integration
- Khushi Chandak (23B3920) – Concrete testing, experimental validation  
- Arnav Ramteke (23B1281) – Circuit design and software support  

---

## Technical Learning

### 1. PCB Design and Hardware Integration

One of the most significant learning outcomes was the complete design and fabrication of a compact 2-layer PCB. The use of dense components such as the BLE module required careful routing, placement, and adherence to RF constraints.

Key takeaways:
- Importance of **component placement before routing**
- Managing **tight clearances and DRC constraints**
- Designing for **manufacturability (hand soldering limitations)**
- Ensuring **proper decoupling and grounding**

---

### 2. Embedded Systems and Firmware Challenges

The firmware development involved configuring BLE communication, interfacing with sensors over I²C, and managing data logging and processing.

A major challenge was:
- Uploading code onto the CC2650 module via XDS debugger

At one point:
- The module was **not detected at all**
- Debugging required checking connections, JTAG wiring, and software setup

This highlighted:
- The fragility of embedded debugging workflows
- The importance of **robust hardware-software interfacing**

---

### 3. Real-World Testing in Concrete

The most valuable learning came from deploying the system in actual concrete conditions.

Observations:
- The system functioned correctly for ~2 days
- Temperature sensing and BLE transmission were stable
- Computed maturity values matched expected lab values

However:
- The system abruptly stopped functioning
- Post-removal testing showed no obvious hardware failure

This emphasized:
- Real-world environments introduce **unpredictable failure modes**
- Need for **robust encapsulation and long-term reliability testing**

---

## Challenges Faced

### 1. PCB Design Constraints
- Extremely compact layout led to routing difficulties
- Small SMD components increased soldering complexity
- Required multiple iterations to finalize layout

---

### 2. Firmware Uploading Issues
- CC2650 module frequently failed to connect via debugger
- At one stage, it was completely undetectable
- This blocked further testing and development

---

### 3. System Failure in Concrete
- Device stopped working after successful operation
- Root cause could not be conclusively identified
- Possible causes:
  - moisture ingress
  - power instability
  - hidden solder or connection issue

---

### 4. Mechanical Design Iterations
- Casing required multiple redesigns to:
  - fit compact PCB
  - maintain structural integrity
  - allow correct orientation inside concrete

---

### 5. Team Coordination

Challenges included:
- Scheduling conflicts among team members
- Occasional differences in design approach

Resolution:
- Tasks were redistributed dynamically
- Team members stepped in when others faced constraints
- Decisions were made collaboratively after discussion

---

## What Worked Well

- Temperature sensing was accurate and stable  
- BLE communication worked reliably with good range  
- Power consumption was low and met expectations  
- Maturity calculation aligned with lab results  
- Modular architecture (sensor + main board) worked effectively  

---

## What Did Not Work Well

- Firmware upload/debugging reliability  
- Long-term system stability in concrete  
- Lack of fault diagnosis tools in embedded system  
- No dedicated mobile interface for end-user  

---

## Key Takeaways

- Real-world deployment is significantly more complex than lab testing  
- Hardware reliability is as important as functional correctness  
- Debugging embedded systems requires patience and structured testing  
- Team adaptability is critical in long-term projects  
- Iterative design (hardware + mechanical) is unavoidable and necessary  

---

## Conclusion

This project provided a comprehensive experience spanning PCB design, embedded systems, mechanical integration, and real-world testing. While not all aspects functioned perfectly, the challenges encountered contributed significantly to our understanding of practical engineering systems and collaborative problem-solving.
