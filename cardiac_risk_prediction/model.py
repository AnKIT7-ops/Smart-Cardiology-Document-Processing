# ============================================================
# MODULE 3 - CARDIAC RISK PREDICTION
# File: model.py
# Purpose: Model training, evaluation, saving/loading, prediction
# Models: Logistic Regression + XGBoost
# ============================================================

import os
import pickle
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from xgboost import XGBClassifier

from preprocess import load_data, clean_and_encode, FEATURE_COLUMNS

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")
LR_MODEL_PATH = os.path.join(MODEL_DIR, "logistic_regression.pkl")
XGB_MODEL_PATH = os.path.join(MODEL_DIR, "xgboost_model.pkl")


class CardiacRiskModel:
    """Trains, saves, loads, and predicts with cardiac risk models."""

    def __init__(self):
        self.lr_model = None
        self.xgb_model = None
        self.lr_accuracy = 0.0
        self.xgb_accuracy = 0.0
        self.lr_report = ""
        self.xgb_report = ""
        self.lr_confusion = None
        self.xgb_confusion = None

    def train(self, csv_path=None, test_size=0.2, random_state=42):
        """Train both models, evaluate, save, and return metrics dict."""
        data = load_data(csv_path)
        X, y = clean_and_encode(data)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        print(f"\n[model] Train: {len(X_train)} | Test: {len(X_test)}\n")

        # --- Logistic Regression ---
        print("=" * 50)
        print("LOGISTIC REGRESSION")
        print("=" * 50)
        self.lr_model = LogisticRegression(max_iter=1000, random_state=random_state)
        self.lr_model.fit(X_train, y_train)
        lr_pred = self.lr_model.predict(X_test)
        self.lr_accuracy = accuracy_score(y_test, lr_pred)
        self.lr_confusion = confusion_matrix(y_test, lr_pred)
        self.lr_report = classification_report(y_test, lr_pred, zero_division=0)
        print(f"Accuracy: {self.lr_accuracy * 100:.2f}%")
        print(f"Confusion Matrix:\n{self.lr_confusion}")
        print(f"Classification Report:\n{self.lr_report}")

        # --- XGBoost ---
        print("=" * 50)
        print("XGBOOST CLASSIFIER")
        print("=" * 50)
        self.xgb_model = XGBClassifier(
            eval_metric="logloss", random_state=random_state,
        )
        self.xgb_model.fit(X_train, y_train)
        xgb_pred = self.xgb_model.predict(X_test)
        self.xgb_accuracy = accuracy_score(y_test, xgb_pred)
        self.xgb_confusion = confusion_matrix(y_test, xgb_pred)
        self.xgb_report = classification_report(y_test, xgb_pred, zero_division=0)
        print(f"Accuracy: {self.xgb_accuracy * 100:.2f}%")
        print(f"Confusion Matrix:\n{self.xgb_confusion}")
        print(f"Classification Report:\n{self.xgb_report}")

        self.save_models()
        return {
            "lr_accuracy": self.lr_accuracy,
            "xgb_accuracy": self.xgb_accuracy,
            "lr_report": self.lr_report,
            "xgb_report": self.xgb_report,
            "lr_confusion": self.lr_confusion,
            "xgb_confusion": self.xgb_confusion,
        }

    def save_models(self):
        """Save both trained models to disk using pickle."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        if self.lr_model is not None:
            with open(LR_MODEL_PATH, "wb") as f:
                pickle.dump({"model": self.lr_model, "accuracy": self.lr_accuracy}, f)
            print(f"[model] Logistic Regression saved -> {LR_MODEL_PATH}")
        if self.xgb_model is not None:
            with open(XGB_MODEL_PATH, "wb") as f:
                pickle.dump({"model": self.xgb_model, "accuracy": self.xgb_accuracy}, f)
            print(f"[model] XGBoost saved -> {XGB_MODEL_PATH}")

    def load_models(self):
        """Load previously saved models from disk. Returns True if any loaded."""
        loaded = False
        if os.path.exists(LR_MODEL_PATH):
            with open(LR_MODEL_PATH, "rb") as f:
                b = pickle.load(f)
                self.lr_model = b["model"]
                self.lr_accuracy = b["accuracy"]
            print(f"[model] Loaded LR (acc: {self.lr_accuracy*100:.2f}%)")
            loaded = True
        if os.path.exists(XGB_MODEL_PATH):
            with open(XGB_MODEL_PATH, "rb") as f:
                b = pickle.load(f)
                self.xgb_model = b["model"]
                self.xgb_accuracy = b["accuracy"]
            print(f"[model] Loaded XGB (acc: {self.xgb_accuracy*100:.2f}%)")
            loaded = True
        if not loaded:
            print("[model] No saved models found. Please train first.")
        return loaded

    def models_exist_on_disk(self):
        """Check if saved model files exist."""
        return os.path.exists(LR_MODEL_PATH) or os.path.exists(XGB_MODEL_PATH)

    def predict(self, features, model_choice="XGBoost"):
        """
        Predict heart disease probability and return risk info dict.
        features: np.ndarray shape (1,6) from preprocess.prepare_input()
        model_choice: "Logistic Regression" or "XGBoost"
        """
        if model_choice == "Logistic Regression":
            if self.lr_model is None:
                raise RuntimeError("Logistic Regression not trained/loaded.")
            prob = self.lr_model.predict_proba(features)[0][1]
            acc = self.lr_accuracy
        else:
            if self.xgb_model is None:
                raise RuntimeError("XGBoost not trained/loaded.")
            prob = self.xgb_model.predict_proba(features)[0][1]
            acc = self.xgb_accuracy

        pct = prob * 100
        if pct < 30:
            level, color = "Low", "#16a34a"
            action = "Maintain a healthy lifestyle. Regular check-ups recommended annually."
            followup = "No"
        elif pct <= 70:
            level, color = "Medium", "#f59e0b"
            action = "Consult a cardiologist. Monitor BP and cholesterol regularly."
            followup = "Yes"
        else:
            level, color = "High", "#dc2626"
            action = "Immediate medical attention required. Detailed cardiac evaluation needed."
            followup = "Yes"

        return {
            "probability": pct,
            "risk_level": level,
            "risk_color": color,
            "action": action,
            "followup": followup,
            "model_used": model_choice,
            "accuracy": acc * 100,
        }


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   CARDIAC RISK PREDICTION - MODEL TRAINING")
    print("=" * 60 + "\n")
    crm = CardiacRiskModel()
    res = crm.train()
    print("\n" + "=" * 60)
    print(f"   LR Accuracy:  {res['lr_accuracy']*100:.2f}%")
    print(f"   XGB Accuracy: {res['xgb_accuracy']*100:.2f}%")
    print("=" * 60)
