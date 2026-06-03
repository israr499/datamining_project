# ============================================
# train_export_models.py
# Module 2 FIXED: Train models from RAW feature dataset
# ElectroGuard - Smart Electricity Anomaly Detection
# ============================================

import os
import json
import joblib
import warnings
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)
from scipy.spatial.distance import cdist

warnings.filterwarnings("ignore")


# ============================================
# PATH SETTINGS
# ============================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
MODELS_DIR = os.path.join(BASE_DIR, "data", "models")

LABELED_PATH = os.path.join(PROCESSED_DIR, "labeled_dataset.csv")
Y_PATH = os.path.join(PROCESSED_DIR, "y_labels.csv")

os.makedirs(MODELS_DIR, exist_ok=True)


# ============================================
# LOAD RAW FEATURE DATA
# ============================================

def load_training_data():
    print("=" * 70)
    print("MODULE 2 FIXED: TRAINING FROM RAW FEATURE DATA")
    print("=" * 70)

    if not os.path.exists(LABELED_PATH):
        raise FileNotFoundError(
            f"Missing labeled dataset: {LABELED_PATH}\n"
            "Run 03_feature_engineering.ipynb first."
        )

    print("\nLoading labeled_dataset.csv...")
    df = pd.read_csv(LABELED_PATH)

    print(f"Loaded dataset shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")

    # Possible label column names
    possible_label_cols = [
        "is_anomaly",
        "label",
        "anomaly_label",
        "target",
        "y"
    ]

    label_col = None

    for col in possible_label_cols:
        if col in df.columns:
            label_col = col
            break

    # If labeled_dataset does not contain label, use y_labels.csv
    if label_col is None:
        if not os.path.exists(Y_PATH):
            raise FileNotFoundError(
                "No label column found in labeled_dataset.csv and y_labels.csv is missing."
            )

        print("No label column found in labeled_dataset.csv. Loading y_labels.csv...")
        y_df = pd.read_csv(Y_PATH)

        if y_df.shape[1] == 1:
            y = y_df.iloc[:, 0].astype(int)
        elif "is_anomaly" in y_df.columns:
            y = y_df["is_anomaly"].astype(int)
        elif "label" in y_df.columns:
            y = y_df["label"].astype(int)
        else:
            y = y_df.iloc[:, 0].astype(int)

    else:
        print(f"Using label column: {label_col}")
        y = df[label_col].astype(int)

    # Drop non-feature columns
    drop_cols = [
        "date",
        "household_id",
        "anomaly_type",
        "type",
        "target",
        "label",
        "is_anomaly",
        "anomaly_label",
        "y"
    ]

    feature_cols = [col for col in df.columns if col not in drop_cols]

    X = df[feature_cols].copy()

    # Keep only numeric columns
    X = X.select_dtypes(include=[np.number])

    # Clean values
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True))

    # Align y length
    y = y.iloc[:len(X)]

    print(f"\nFinal X shape: {X.shape}")
    print(f"Final y shape: {y.shape}")
    print(f"Normal samples: {(y == 0).sum()}")
    print(f"Suspicious samples: {(y == 1).sum()}")
    print(f"Anomaly ratio: {y.mean() * 100:.2f}%")
    print(f"Feature columns: {list(X.columns)}")

    return X, y


# ============================================
# TRAIN MODELS
# ============================================

def train_models(X, y):
    print("\nSplitting data into train/test...")

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    print(f"Training samples: {X_train.shape[0]}")
    print(f"Testing samples: {X_test.shape[0]}")

    print("\nFitting StandardScaler on RAW features...")
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ============================================
    # K-Means
    # ============================================
    print("\nTraining K-Means model...")

    kmeans = KMeans(
        n_clusters=4,
        random_state=42,
        n_init=10
    )

    kmeans.fit(X_train_scaled)

    train_distances = np.min(
        cdist(X_train_scaled, kmeans.cluster_centers_),
        axis=1
    )

    anomaly_threshold = float(np.percentile(train_distances, 97))

    test_distances = np.min(
        cdist(X_test_scaled, kmeans.cluster_centers_),
        axis=1
    )

    kmeans_pred = (test_distances > anomaly_threshold).astype(int)

    # ============================================
    # Decision Tree
    # ============================================
    print("Training Decision Tree...")

    decision_tree = DecisionTreeClassifier(
        max_depth=10,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced"
    )

    decision_tree.fit(X_train_scaled, y_train)
    dt_pred = decision_tree.predict(X_test_scaled)

    # ============================================
    # Naive Bayes
    # ============================================
    print("Training Naive Bayes...")

    naive_bayes = GaussianNB()
    naive_bayes.fit(X_train_scaled, y_train)
    nb_pred = naive_bayes.predict(X_test_scaled)

    # ============================================
    # Random Forest
    # ============================================
    print("Training Random Forest...")

    random_forest = RandomForestClassifier(
        n_estimators=250,
        max_depth=18,
        min_samples_split=6,
        min_samples_leaf=3,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1
    )

    random_forest.fit(X_train_scaled, y_train)
    rf_pred = random_forest.predict(X_test_scaled)
    rf_proba = random_forest.predict_proba(X_test_scaled)[:, 1]

    # ============================================
    # Isolation Forest
    # ============================================
    print("Training Isolation Forest...")

    contamination_rate = max(0.01, min(0.25, float(y_train.mean())))

    isolation_forest = IsolationForest(
        n_estimators=200,
        contamination=contamination_rate,
        random_state=42
    )

    isolation_forest.fit(X_train_scaled)

    iso_raw = isolation_forest.predict(X_test_scaled)
    iso_pred = (iso_raw == -1).astype(int)

    models = {
        "scaler": scaler,
        "kmeans": kmeans,
        "anomaly_threshold": anomaly_threshold,
        "decision_tree": decision_tree,
        "naive_bayes": naive_bayes,
        "random_forest": random_forest,
        "isolation_forest": isolation_forest,
        "feature_columns": list(X.columns)
    }

    predictions = {
        "kmeans_distance": kmeans_pred,
        "decision_tree": dt_pred,
        "naive_bayes": nb_pred,
        "random_forest": rf_pred,
        "isolation_forest": iso_pred
    }

    probabilities = {
        "random_forest": rf_proba
    }

    test_data = {
        "X_test": X_test,
        "X_test_scaled": X_test_scaled,
        "y_test": y_test
    }

    return models, predictions, probabilities, test_data


# ============================================
# EVALUATION
# ============================================

def evaluate_model(y_true, y_pred, y_proba=None):
    result = {}

    result["accuracy"] = float(accuracy_score(y_true, y_pred))
    result["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
    result["recall"] = float(recall_score(y_true, y_pred, zero_division=0))
    result["f1_score"] = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        if y_proba is not None:
            result["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        else:
            result["roc_auc"] = float(roc_auc_score(y_true, y_pred))
    except Exception:
        result["roc_auc"] = 0.0

    result["confusion_matrix"] = confusion_matrix(y_true, y_pred).tolist()

    return result


def evaluate_all_models(predictions, probabilities, test_data):
    print("\nEvaluating all models...")

    y_test = test_data["y_test"]
    metrics = {}

    for model_name, y_pred in predictions.items():
        y_proba = probabilities.get(model_name)
        metrics[model_name] = evaluate_model(y_test, y_pred, y_proba)

    print("\nMODEL PERFORMANCE")
    print("=" * 70)

    for name, m in metrics.items():
        print(f"\n{name}")
        print(f"Accuracy : {m['accuracy'] * 100:.2f}%")
        print(f"Precision: {m['precision'] * 100:.2f}%")
        print(f"Recall   : {m['recall'] * 100:.2f}%")
        print(f"F1 Score : {m['f1_score'] * 100:.2f}%")
        print(f"ROC-AUC  : {m['roc_auc']:.4f}")

    return metrics


# ============================================
# SAVE FEATURE IMPORTANCE
# ============================================

def create_feature_importance(models):
    rf = models["random_forest"]
    feature_columns = models["feature_columns"]

    importance_df = pd.DataFrame({
        "feature": feature_columns,
        "importance": rf.feature_importances_
    })

    importance_df = importance_df.sort_values(
        by="importance",
        ascending=False
    )

    output_path = os.path.join(PROCESSED_DIR, "feature_importance_values.csv")
    importance_df.to_csv(output_path, index=False)

    print(f"\nSaved feature importance: {output_path}")

    return importance_df


# ============================================
# SAVE MODELS
# ============================================

def save_models(models, metrics, importance_df):
    print("\nSaving corrected models...")

    joblib.dump(models["scaler"], os.path.join(MODELS_DIR, "scaler.pkl"))
    joblib.dump(models["kmeans"], os.path.join(MODELS_DIR, "kmeans_model.pkl"))
    joblib.dump(models["anomaly_threshold"], os.path.join(MODELS_DIR, "anomaly_threshold.pkl"))
    joblib.dump(models["decision_tree"], os.path.join(MODELS_DIR, "decision_tree.pkl"))
    joblib.dump(models["naive_bayes"], os.path.join(MODELS_DIR, "naive_bayes.pkl"))
    joblib.dump(models["random_forest"], os.path.join(MODELS_DIR, "random_forest.pkl"))
    joblib.dump(models["isolation_forest"], os.path.join(MODELS_DIR, "isolation_forest.pkl"))
    joblib.dump(models["feature_columns"], os.path.join(MODELS_DIR, "feature_columns.pkl"))

    model_package = {
        "scaler": models["scaler"],
        "kmeans": models["kmeans"],
        "anomaly_threshold": models["anomaly_threshold"],
        "decision_tree": models["decision_tree"],
        "naive_bayes": models["naive_bayes"],
        "random_forest": models["random_forest"],
        "isolation_forest": models["isolation_forest"],
        "feature_columns": models["feature_columns"],
        "metrics": metrics
    }

    joblib.dump(model_package, os.path.join(MODELS_DIR, "model_package.pkl"))

    metadata = {
        "project_name": "ElectroGuard",
        "module": "Module 2 Fixed - Raw Feature Training",
        "main_model": "random_forest",
        "feature_count": len(models["feature_columns"]),
        "feature_columns": models["feature_columns"],
        "anomaly_threshold": models["anomaly_threshold"],
        "metrics": metrics,
        "top_features": importance_df.head(10).to_dict(orient="records")
    }

    with open(os.path.join(MODELS_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)

    with open(os.path.join(PROCESSED_DIR, "model_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=4)

    print("\nFiles updated:")
    print("- data/models/model_package.pkl")
    print("- data/models/scaler.pkl")
    print("- data/models/feature_columns.pkl")
    print("- data/models/model_metadata.json")
    print("- data/processed/model_metrics.json")
    print("- data/processed/feature_importance_values.csv")


# ============================================
# MAIN
# ============================================

def main():
    X, y = load_training_data()

    models, predictions, probabilities, test_data = train_models(X, y)

    metrics = evaluate_all_models(
        predictions,
        probabilities,
        test_data
    )

    importance_df = create_feature_importance(models)

    save_models(models, metrics, importance_df)

    print("\n" + "=" * 70)
    print("MODULE 2 FIXED SUCCESSFULLY")
    print("=" * 70)
    print("Now restart Flask:")
    print("python run.py")


if __name__ == "__main__":
    main()