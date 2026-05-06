# ============================================================
# MODULE 3 - CARDIAC RISK PREDICTION
# File: preprocess.py
# Purpose: Data loading, cleaning, encoding, and feature selection
# Dataset: UCI Heart Disease (heart_disease_uci.csv)
# ============================================================

import os
import pandas as pd
import numpy as np


# ---------- COLUMN MAPPINGS ----------
# Our GUI input fields map to UCI dataset columns:
#   Age              -> age
#   Gender           -> sex        (Male=1, Female=0)
#   Blood Pressure   -> trestbps   (resting blood pressure in mmHg)
#   Cholesterol      -> chol       (serum cholesterol in mg/dL)
#   Diabetes         -> fbs        (fasting blood sugar > 120 mg/dL: TRUE=1, FALSE=0)
#   Smoking          -> NOT in UCI dataset (ignored during prediction)
#   ECG Result       -> restecg    (normal=0, lv hypertrophy=1, st-t abnormality=2)
#
# FUTURE INTEGRATION NOTE:
# -----------------------------------------------------------------
# Module 2 (ECG Signal Analysis) will output a classification such
# as "Normal", "Abnormal - ST Depression", "Abnormal - Arrhythmia",
# etc. To integrate it here:
#   1. Accept the Module 2 output string as the ECG Result input.
#   2. Map the Module 2 labels to numeric codes (0, 1, 2) using a
#      dictionary, then pass them into the feature vector.
#   3. The model will automatically use the encoded value.
# -----------------------------------------------------------------


# ---------- FEATURE COLUMNS ----------
# These are the columns the model will use for prediction.
FEATURE_COLUMNS = ["age", "sex_num", "trestbps", "chol", "fbs_num", "restecg_num"]


def get_dataset_path():
    """
    Return the absolute path to the dataset CSV file.
    Looks for 'heart_disease_uci.csv' in the parent directory
    (where the original dataset lives).
    """
    # Go up one level from the cardiac_risk_prediction package folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "heart_disease_uci.csv")

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Dataset not found at: {csv_path}\n"
            "Please place 'heart_disease_uci.csv' in the project root."
        )
    return csv_path


def load_data(csv_path=None):
    """
    Load the heart disease CSV into a pandas DataFrame.

    Parameters
    ----------
    csv_path : str or None
        Full path to the CSV. If None, auto-detect using get_dataset_path().

    Returns
    -------
    pd.DataFrame
        Raw dataframe loaded from the CSV.
    """
    if csv_path is None:
        csv_path = get_dataset_path()

    print(f"[preprocess] Loading dataset from: {csv_path}")
    data = pd.read_csv(csv_path)
    print(f"[preprocess] Loaded {len(data)} rows, {len(data.columns)} columns")
    return data


def encode_sex(value):
    """Convert sex string to numeric: Male=1, Female=0."""
    return 1 if str(value).strip().lower() == "male" else 0


def encode_fbs(value):
    """Convert fasting blood sugar to numeric: TRUE=1, FALSE=0."""
    return 1 if str(value).strip().upper() == "TRUE" else 0


def encode_restecg(value):
    """
    Convert resting ECG result to numeric code.
      normal           -> 0
      lv hypertrophy   -> 1
      st-t abnormality -> 2
    """
    val = str(value).strip().lower()
    if val == "normal":
        return 0
    elif val == "lv hypertrophy":
        return 1
    elif val == "st-t abnormality":
        return 2
    else:
        return 0  # default to normal for unknown values


def clean_and_encode(data):
    """
    Perform all preprocessing steps on the raw dataframe:
      1. Create binary target column (0 = no disease, 1 = disease)
      2. Encode categorical columns (sex, fbs, restecg) to numeric
      3. Drop rows with missing values in feature or target columns
      4. Return cleaned feature matrix X and target vector y

    Parameters
    ----------
    data : pd.DataFrame
        Raw dataframe from load_data().

    Returns
    -------
    X : pd.DataFrame
        Cleaned feature matrix with columns matching FEATURE_COLUMNS.
    y : pd.Series
        Binary target (0 = no disease, 1 = disease).
    """
    df = data.copy()

    # --- Step 1: Binary target ---
    # Original 'num' column has values 0-4; convert to binary
    df["target"] = df["num"].apply(lambda x: 1 if x > 0 else 0)
    print(f"[preprocess] Target distribution:\n{df['target'].value_counts().to_string()}")

    # --- Step 2: Encode categorical variables ---
    df["sex_num"] = df["sex"].apply(encode_sex)
    df["fbs_num"] = df["fbs"].apply(encode_fbs)
    df["restecg_num"] = df["restecg"].apply(encode_restecg)

    # --- Step 3: Handle missing values ---
    # Keep only the feature columns and target, then drop NaN rows
    required_cols = FEATURE_COLUMNS + ["target"]
    clean_df = df[required_cols].dropna()

    rows_dropped = len(df) - len(clean_df)
    if rows_dropped > 0:
        print(f"[preprocess] Dropped {rows_dropped} rows with missing values")

    # --- Step 4: Separate features and target ---
    X = clean_df[FEATURE_COLUMNS].reset_index(drop=True)
    y = clean_df["target"].reset_index(drop=True)

    print(f"[preprocess] Final dataset: {len(X)} samples, {len(FEATURE_COLUMNS)} features")
    return X, y


def prepare_input(age, gender, bp, chol, diabetes, smoking, ecg):
    """
    Convert raw user inputs (from the GUI) into a feature array
    that matches the model's expected format.

    Parameters
    ----------
    age : int           Age in years.
    gender : str        "Male" or "Female".
    bp : int            Resting blood pressure in mmHg.
    chol : int          Serum cholesterol in mg/dL.
    diabetes : str      "Yes" or "No".
    smoking : str       "Yes" or "No" (not used by the model).
    ecg : str           "Normal", "LV Hypertrophy", or "ST-T Abnormality".

    Returns
    -------
    np.ndarray
        Shape (1, 6) feature array ready for model.predict_proba().

    Notes
    -----
    - Smoking status is captured in the UI for medical records but is
      NOT a feature in the UCI Heart Disease dataset, so it is ignored
      during prediction.
    - FUTURE: When Module 2 (ECG Analysis) is integrated, its output
      can be passed directly as the `ecg` parameter here.
    """
    sex_val = 1 if gender == "Male" else 0
    fbs_val = 1 if diabetes == "Yes" else 0

    ecg_map = {
        "Normal": 0,
        "LV Hypertrophy": 1,
        "ST-T Abnormality": 2,
    }
    ecg_val = ecg_map.get(ecg, 0)

    # Note: smoking is not used in the feature vector
    # Return a DataFrame with named columns to match training data format
    features = pd.DataFrame(
        [[age, sex_val, bp, chol, fbs_val, ecg_val]],
        columns=FEATURE_COLUMNS
    )
    return features
