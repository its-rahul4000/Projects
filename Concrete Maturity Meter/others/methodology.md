## 📄 Methodology

### 1. Objective
To estimate the **compressive strength of concrete** using the **maturity method**, based on temperature measurements recorded over time.

---

### 2. Principle

The method is based on the **Nurse-Saul maturity equation**, which correlates concrete **(M30 grade)** strength with its temperature history.

The maturity index is calculated as: M = Σ (T - T₀) × Δt

---


Where:
- `T` = Average Concrete temperature (°C)  
- `T₀` = Datum temperature (typically -10°C)  
- `Δt` = Time interval (hours)  

---

### 3. Data Acquisition

- Temperature readings were recorded **every 10 minutes** using a temperature sensor embedded in concrete(considering power constraints and is feasible for our usecase).
- These readings capture the **thermal profile during curing**.

---

### 4. Maturity Calculation

- Since readings are taken every **10 minutes**, each interval corresponds to: Δt = 10 / 60 = 0.167 hours

---


- For each reading:
  1. Compute `(T - T₀)` ; here T is the average of the 6 readings per hour
  2. Multiply by `Δt` ; here Δt is 1 hour
  3. Accumulate over time

- The maturity index is **aggregated over 1-hour intervals** for analysis.

---

### 5. Data Processing

- The computed maturity values `M` are transformed using: ln(M)


- This transformation helps establish a **linear relationship** with compressive strength.

---

### 6. Strength Calibration

- Compressive strength laboratory tested values were obtained at:
  - **1 day**
  - **3 days**
  - **7 days**
  - **28 days**

We have plotted the curve considering the values at 1st, 3rd and 7th day because we have tested our product for 8 days due to time constraint. Concrete acheives almost 75% of its strength in the first 7 days.

- **Compressive Strength (MPa)**
- 
   f_c = a + b · ln(M)


Where:
- `f_c` = Compressive strength (MPa)  
- `a, b` = Constants  

---

### 7. Model Application

- The regression model is used to:
  - Predict compressive strength at intermediate times  
  - Compare laboratory "Destructive tested" values with actual tested hourly strength development values

- Hourly strength values are plotted to validate the trend.

---

### 8. Visualization

- A graph of **Compressive Strength vs Maturity** is plotted:
  - Regression curve (based on 3-point calibration)
  - Actual hourly strength data points

---

### 9. Key Assumptions

- Uniform curing conditions  
- Constant datum temperature (`T₀ = -10°C`)  
- Linear relationship between `ln(M)` and strength  

---

### 10. Outcome

- The maturity method enables:
  - **Non-destructive strength estimation**
  - Real-time monitoring of concrete curing
  - Reduced dependency on destructive testing  

---

### 💡 Advantages

- Real-time monitoring  
- Cost-effective  
- Field-applicable  

---

### ⚠️ Limitations

- Sensitive to temperature measurement accuracy   



