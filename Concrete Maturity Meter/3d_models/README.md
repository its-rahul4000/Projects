## 🔧 Hardware Casing Design

The hardware casing is divided into three primary components, each designed to serve a specific functional and structural purpose:

1. Main Box

The Main Box is the primary enclosure designed to house the core hardware components, including the battery and the main PCB. It provides structural support, protection from external damage, and sufficient internal space for component placement and wiring.

2. Lid

The Lid serves as the top cover of the main box. It is designed to fit securely onto the main enclosure, ensuring protection of internal components while allowing easy access for assembly.

3. Metallic Casing for Temperature Sensor

A separate metallic casing is designed specifically for the temperature sensor. This casing ensures better thermal conductivity and protection, allowing accurate temperature measurement while shielding the sensor from mechanical damage and environmental interference.



## 🧠 Design Considerations

### 1. Material Selection
- The 3D printed **box and lid** were made using **PLA material** due to its ease of printing and sufficient strength.

### 2. Dimensions & Tolerances

**Main Box Dimensions**
- Length: 48 mm
- Width: 40 mm
- Height: 19 mm

**Lid Dimensions**
- Length: 48 mm
- Width: 40 mm
- Height: 6 mm

**Metallic Sensor Casing**
- Diameter: 4.2 mm
- Height: 1.6 mm

**Tolerance Considerations**
- Battery height tolerance: 1.5 mm
- PCB height tolerance: 2 mm
- Edge tolerance: 1 mm on both sides
- Clearance between lid and box: 0.5 mm
- PCB/Battery fitting margin: 1 mm on each side

### 3. Thermal Considerations
- Thermal considerations were not required for the main box.
- For the metallic casing, thermal paste was used and the cavity around the **temperature sensor** was filled with metallic paste to improve heat transfer and accurate sensing.

### 4. Structural Strength
- The metallic casing was chosen to be a **cylindrical structure** to distribute pressure from surrounding concrete.
- The main box casing also incorporates rounded edges to improve durability and reduce stress concentration.

### 5. Wall Thickness
- Base thickness: 1.5 mm
- Side walls: 2 mm
- Top wall: 1 mm

### 6. Ease of Assembly
- Assembly is simple since the lid fits directly onto the box with designed tolerances.




## ⚙️ Design Methodology / Modeling Approach

### 1. Software Used

The enclosure (Main Box + Lid) were designed using Autodesk Fusion 360, a CAD software that enables precise parametric modeling and easy modification of dimensions. Fusion 360 was used to create the main box and lid while maintaining the required tolerances for the PCB and battery

### 2. Design Workflow

The design process followed a structured CAD workflow:

1. Sketch Creation - Initial 2D sketches of the box base and lid were created with the required dimensions (48 × 40 mm). The internal layout was also planned to accommodate the PCB (along with antenna) and battery.

2. Extrusion / 3D Modeling - The sketches were extruded to create the 3D geometry of the enclosure.

   * The main box was extruded to a height of **19 mm**.
   * The lid was extruded to **6 mm** depth.

3. Feature Addition - Additional features such as rounded edges, wall thickness, tolerances, and snap-fit lid structure were incorporated to improve structural strength and ease of assembly.

### 3. Final Model Preparation or Fabrication

* After verifying the dimensions and assembly fit, the model was exported in .stl format for 3D printing.
* The design ensured proper tolerances so that the PCB, battery, and lid could fit accurately into the enclosure.
* The PLA material was used to 3d print both the components


