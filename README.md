# ⚡ ElectroGuard - Smart Electricity Anomaly Detection System

## 📌 Overview

ElectroGuard is a machine learning-based electricity anomaly detection system designed to identify suspicious electricity consumption patterns and potential electricity theft using smart meter data. The project leverages data mining techniques, clustering algorithms, anomaly detection methods, and classification models to provide an intelligent, scalable, and automated solution for utility providers.

Traditional electricity theft detection methods often rely on manual inspections and rule-based systems, which are time-consuming and inefficient. ElectroGuard addresses these challenges by analyzing electricity consumption data and automatically detecting irregular usage behaviors.

---

## 🎯 Objectives

* Detect abnormal electricity consumption patterns.
* Identify potential electricity theft cases.
* Reduce dependence on manual inspections.
* Improve detection accuracy using machine learning.
* Provide interactive visualizations and insights for analysis.

---

## ✨ Features

### Data Preprocessing

* Missing value handling
* Data cleaning and formatting
* Dataset normalization and transformation

### Feature Engineering

* Average consumption calculation
* Variance analysis
* Peak usage detection
* Night usage ratio extraction

### Exploratory Data Analysis (EDA)

* Consumption trend visualization
* Statistical summaries
* Pattern identification

### Machine Learning Models

* K-Means Clustering
* Decision Tree Classifier
* Naïve Bayes Classifier

### Anomaly Detection

* Distance-based anomaly scoring
* Cluster centroid deviation analysis
* Suspicious consumption identification

### Visualization Dashboard

* Consumption trend graphs
* Cluster distribution plots
* Anomaly score visualization
* Prediction result display

### Model Evaluation

* Accuracy Score
* Precision
* Recall
* Confusion Matrix

---

## 🏗️ System Architecture

```text
Dataset
   │
   ▼
Data Preprocessing
   │
   ▼
Feature Engineering
   │
   ▼
Exploratory Data Analysis
   │
   ▼
K-Means Clustering
   │
   ▼
Anomaly Detection
   │
   ▼
Classification Models
   │
   ▼
Prediction & Visualization
```

---

## 🛠️ Technologies Used

### Programming Language

* Python

### Libraries

* Pandas
* NumPy
* Scikit-learn
* Matplotlib
* Seaborn
* ipywidgets

### Development Environment

* Jupyter Notebook

### Dataset

* Smart Meter Electricity Consumption Dataset (CSV Format)

---

## 📂 Project Structure

```text
ElectroGuard/
│
├── data/
│   └── electricity_dataset.csv
│
├── notebooks/
│   └── ElectroGuard.ipynb
│
├── models/
│   └── trained_models.pkl
│
├── visualizations/
│   └── plots/
│
├── requirements.txt
│
├── README.md
│
└── reports/
    └── project_report.pdf
```

---

## 🚀 Installation

### Clone the Repository

```bash
git clone https://github.com/your-username/ElectroGuard.git
cd ElectroGuard
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Project

Launch Jupyter Notebook:

```bash
jupyter notebook
```

Open:

```text
notebooks/ElectroGuard.ipynb
```

Run all cells sequentially to:

1. Load and preprocess data
2. Generate features
3. Perform EDA
4. Train clustering and classification models
5. Detect anomalies
6. Visualize results

---

## 📊 Machine Learning Workflow

1. Data Collection
2. Data Cleaning & Preprocessing
3. Feature Engineering
4. Exploratory Data Analysis
5. K-Means Clustering
6. Distance-Based Anomaly Detection
7. Decision Tree Classification
8. Naïve Bayes Classification
9. Model Evaluation
10. Prediction & Visualization

---

## 📈 Evaluation Metrics

The system evaluates model performance using:

* Accuracy
* Precision
* Recall
* F1-Score
* Confusion Matrix

---

## 🔮 Future Enhancements

* Real-time smart meter integration
* Web-based dashboard deployment
* Deep learning-based anomaly detection
* Live data streaming support
* Utility provider integration
* Automated alert generation

---


## 📚 References

* Scikit-learn Documentation
* Pandas Documentation
* NumPy Documentation
* Matplotlib Documentation
* Seaborn Documentation
* Chandola et al. (2009) – Anomaly Detection Survey
* Aggarwal (2015) – Data Mining: The Textbook

---

## 📄 License

This project was developed as part of the Data Mining (CSL-460) course at Bahria University Karachi Campus for academic and research purposes.
