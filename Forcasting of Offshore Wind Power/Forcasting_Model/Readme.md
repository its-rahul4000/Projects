# 🌬️ Forecasting of Offshore Wind Power

## 📖 Project Overview

This project focuses on forecasting offshore wind power generation using time-series models. It compares baseline and advanced statistical approaches while providing detailed visualization and performance analysis.

---

## ⚡ Models Used

| Model                 | Description                                    | Performance (MAE)            |
| --------------------- | ---------------------------------------------- | ---------------------------- |
| **Persistence Model** | Uses previous values as predictions (baseline) | 0.0231                       |
| **ARIMA(2,0,2)**      | Auto-Regressive Integrated Moving Average      | **0.0188** (19% improvement) |

---

## 📊 Key Results

* **ARIMA outperforms Persistence by ~19%**
* **Best month:** December (MAE = 0.0137)
* **Worst month:** October (MAE = 0.0270)
* **Overall MAPE:** 7.25%

---

## 📁 Project Structure

```
Forcasting_Model/
│
├── data/
│   ├── raw/
│   │   └── Existing.csv
│   └── processed/
│       └── UK_OFF_hourly_2010_2022.csv
│
├── outputs/
│   ├── figures/
│   │   ├── arima_plots/
│   │   ├── persistence_plots/
│   │   └── weekly_analysis/
│   └── metrics/
│
├── scripts/
│   ├── 01_data_prep.py
│   ├── 02_persistence.py
│   ├── 03_arima.py
│   ├── 04_weekly_analysis.py
│   └── main.py
│
├── report/
├── .venv/
├── README.md
└── requirements.txt
```

---

## 📥 Dataset Setup

Download dataset manually due to large size:

👉 https://doi.org/10.11583/DTU.29617955

Place the file at:

```
Forcasting_Model/data/raw/Existing.csv
```

### Dataset Info

* Time Range: **2000–2020** (filtered to 2010-2020 for analysis)
* Resolution: **Hourly**
* Records: **376,920 → 113,952 (processed)**
* Capacity Factor Range: **0.0007 – 0.9000**
* Mean: **0.4160**

---

## ⚙️ Environment Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
```

### 2. Activate Environment

**Windows**

```bash
.venv\Scripts\activate
```

**Mac/Linux**

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### Required Libraries

* pandas
* numpy
* matplotlib
* scikit-learn
* statsmodels
* scipy

---

## 📊 Running the Models

### ✅ Method 1: Run Everything (Recommended)

```bash
cd scripts
python main.py
```

---

### ⚙️ Method 2: Run Step-by-Step

```bash
cd scripts
```

#### 1. Data Preprocessing

* Filters UK data (2010–2020)
* Handles missing values
* Generates statistics

```bash
python 01_data_prep.py
```

#### 2. Persistence Model

* Tests multiple forecast horizons
* Baseline comparison

```bash
python 02_persistence.py
```

#### 3. ARIMA Model

* Automatic parameter selection (AIC)
* Forecast generation

```bash
python 03_arima.py
```

#### 4. Weekly Analysis

* Detailed visualization
* Error and pattern analysis

```bash
python 04_weekly_analysis.py
```

---

## 📈 Outputs

### Generated Visualizations

**ARIMA Plots**

* Full-year forecast
* Monthly and weekly views
* Error distribution
* Q-Q residual plots

**Persistence Plots**

* Full-year comparison
* Weekly trends
* Hourly error patterns

**Weekly Analysis**

* Seasonal weekly patterns
* Average weekly heatmaps

---

### Metrics Files

* `data_statistics.txt`
* `persistence_metrics_2022.txt`
* `arima_metrics_full_2022.txt`
* `arima_parameter_selection.csv`
* `weekly_analysis_summary.txt`

---

## 📊 Key Insights

### Seasonal Trends

| Season | Avg Capacity |
| ------ | ------------ |
| Winter | 0.538        |
| Spring | 0.376        |
| Summer | 0.299        |
| Fall   | 0.453        |

### Hourly Trends

* Peak: **21:00 (~0.434)**
* Lowest: **04:00–06:00**

---

### Model Performance

| Season | ARIMA MAE | Persistence MAE |
| ------ | --------- | --------------- |
| Winter | 0.0160    | 0.0223          |
| Spring | 0.0178    | 0.0234          |
| Summer | 0.0181    | 0.0223          |
| Fall   | 0.0232    | 0.0246          |

---
##  References
Actual Dataset References:

Nayak, S., Koivisto, M. J., & Kanellas, P. (2025). 
Time series of hourly resolution Offshore Wind generation for 
European Scale Energy system studies [Data set]. 
Technical University of Denmark. 
https://doi.org/10.11583/DTU.29617955

---