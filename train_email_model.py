import os
import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

DATASET_PATH = os.path.join(
    BASE_DIR,
    "data",
    "emails.csv"
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)

os.makedirs(MODEL_DIR, exist_ok=True)


# ============================================================
# LOAD DATASET
# ============================================================

print("\n" + "=" * 70)
print("AI EVIDENCE ANALYZER - EMAIL ML TRAINING")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(DATASET_PATH)

print(f"Dataset loaded successfully.")
print(f"Total rows: {len(df)}")

print("\nColumns:")
print(df.columns.tolist())


# ============================================================
# CLEAN DATA
# ============================================================

# Keep only required columns
df = df[["text", "label"]]

# Remove missing values
df = df.dropna(subset=["text", "label"])

# Convert text to string
df["text"] = df["text"].astype(str)

# Normalize labels
df["label"] = df["label"].astype(str).str.lower().str.strip()

# Keep only ham and spam
df = df[df["label"].isin(["ham", "spam"])]

# Remove duplicate messages
df = df.drop_duplicates(subset=["text"])

print("\nAfter cleaning:")
print(f"Total emails: {len(df)}")

print("\nClass distribution:")
print(df["label"].value_counts())


# ============================================================
# CONVERT LABELS
# ============================================================

# ham  = 0
# spam = 1

df["target"] = df["label"].map({
    "ham": 0,
    "spam": 1
})

X = df["text"]
y = df["target"]


# ============================================================
# TRAIN / VALIDATION / TEST SPLIT
# ============================================================

# First split:
# 80% temporary training data
# 20% final unseen test data

X_train_val, X_test, y_train_val, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

# Second split:
# 80% training
# 20% validation
#
# Overall:
# 64% train
# 16% validation
# 20% test

X_train, X_val, y_train, y_val = train_test_split(
    X_train_val,
    y_train_val,
    test_size=0.20,
    random_state=42,
    stratify=y_train_val
)

print("\nDataset split:")
print(f"Training:   {len(X_train)}")
print(f"Validation: {len(X_val)}")
print(f"Testing:    {len(X_test)}")


# ============================================================
# TF-IDF FEATURE EXTRACTION
# ============================================================

print("\n" + "-" * 70)
print("Creating TF-IDF features...")
print("-" * 70)

vectorizer = TfidfVectorizer(
    lowercase=True,
    strip_accents="unicode",
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.98,
    sublinear_tf=True,
    max_features=100000
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_val_tfidf = vectorizer.transform(X_val)
X_test_tfidf = vectorizer.transform(X_test)

print(f"Training TF-IDF shape:   {X_train_tfidf.shape}")
print(f"Validation TF-IDF shape: {X_val_tfidf.shape}")
print(f"Testing TF-IDF shape:    {X_test_tfidf.shape}")
print(f"Vocabulary size:         {len(vectorizer.vocabulary_)}")


# ============================================================
# MODELS
# ============================================================

models = {

    "Logistic Regression": LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42
    ),

    "Linear SVM": LinearSVC(
        class_weight="balanced",
        random_state=42
    ),

    "Naive Bayes": MultinomialNB()
}


# ============================================================
# EVALUATION FUNCTION
# ============================================================

def evaluate_model(model, X_data, y_data):

    predictions = model.predict(X_data)

    accuracy = accuracy_score(
        y_data,
        predictions
    )

    precision = precision_score(
        y_data,
        predictions,
        zero_division=0
    )

    recall = recall_score(
        y_data,
        predictions,
        zero_division=0
    )

    f1 = f1_score(
        y_data,
        predictions,
        zero_division=0
    )

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "predictions": predictions
    }


# ============================================================
# TRAIN AND COMPARE MODELS
# ============================================================

print("\n" + "=" * 70)
print("TRAINING AND MODEL COMPARISON")
print("=" * 70)

results = {}

for name, model in models.items():

    print(f"\nTraining {name}...")

    model.fit(
        X_train_tfidf,
        y_train
    )

    evaluation = evaluate_model(
        model,
        X_val_tfidf,
        y_val
    )

    results[name] = evaluation

    print(f"Accuracy:  {evaluation['accuracy'] * 100:.2f}%")
    print(f"Precision: {evaluation['precision'] * 100:.2f}%")
    print(f"Recall:    {evaluation['recall'] * 100:.2f}%")
    print(f"F1 Score:  {evaluation['f1_score'] * 100:.2f}%")


# ============================================================
# MODEL COMPARISON TABLE
# ============================================================

print("\n" + "=" * 70)
print("MODEL COMPARISON")
print("=" * 70)

print(
    f"{'Model':<25}"
    f"{'Accuracy':<15}"
    f"{'Precision':<15}"
    f"{'Recall':<15}"
    f"{'F1':<15}"
)

print("-" * 85)

for name, result in results.items():

    print(
        f"{name:<25}"
        f"{result['accuracy'] * 100:<15.2f}"
        f"{result['precision'] * 100:<15.2f}"
        f"{result['recall'] * 100:<15.2f}"
        f"{result['f1_score'] * 100:<15.2f}"
    )


# ============================================================
# SELECT BEST MODEL
# ============================================================

best_model_name = max(
    results,
    key=lambda name: results[name]["f1_score"]
)

print("\n" + "=" * 70)
print("BEST MODEL")
print("=" * 70)

print(f"Selected model: {best_model_name}")
print(
    f"Validation F1 Score: "
    f"{results[best_model_name]['f1_score'] * 100:.2f}%"
)


# ============================================================
# RETRAIN BEST MODEL ON TRAIN + VALIDATION
# ============================================================

print("\nRetraining best model using training + validation data...")

X_final_train = pd.concat(
    [X_train, X_val]
)

y_final_train = pd.concat(
    [y_train, y_val]
)

# Create a fresh vectorizer
final_vectorizer = TfidfVectorizer(
    lowercase=True,
    strip_accents="unicode",
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.98,
    sublinear_tf=True,
    max_features=100000
)

X_final_tfidf = final_vectorizer.fit_transform(
    X_final_train
)

X_final_test_tfidf = final_vectorizer.transform(
    X_test
)


# Create fresh instance of selected model

if best_model_name == "Logistic Regression":

    best_model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42
    )

elif best_model_name == "Linear SVM":

    best_model = LinearSVC(
        class_weight="balanced",
        random_state=42
    )

else:

    best_model = MultinomialNB()


best_model.fit(
    X_final_tfidf,
    y_final_train
)


# ============================================================
# FINAL TEST EVALUATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL UNSEEN TEST EVALUATION")
print("=" * 70)

test_predictions = best_model.predict(
    X_final_test_tfidf
)

test_accuracy = accuracy_score(
    y_test,
    test_predictions
)

test_precision = precision_score(
    y_test,
    test_predictions,
    zero_division=0
)

test_recall = recall_score(
    y_test,
    test_predictions,
    zero_division=0
)

test_f1 = f1_score(
    y_test,
    test_predictions,
    zero_division=0
)

cm = confusion_matrix(
    y_test,
    test_predictions
)

print(f"\nSelected Model: {best_model_name}")

print(f"\nAccuracy:  {test_accuracy * 100:.2f}%")
print(f"Precision: {test_precision * 100:.2f}%")
print(f"Recall:    {test_recall * 100:.2f}%")
print(f"F1 Score:  {test_f1 * 100:.2f}%")

print("\nConfusion Matrix:")
print(cm)

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        test_predictions,
        target_names=["Ham", "Spam"],
        zero_division=0
    )
)


# ============================================================
# SAVE MODEL
# ============================================================

model_path = os.path.join(
    MODEL_DIR,
    "email_model.pkl"
)

vectorizer_path = os.path.join(
    MODEL_DIR,
    "email_tfidf_vectorizer.pkl"
)

metrics_path = os.path.join(
    MODEL_DIR,
    "email_metrics.json"
)

model_name_path = os.path.join(
    MODEL_DIR,
    "email_model_name.txt"
)


joblib.dump(
    best_model,
    model_path
)

joblib.dump(
    final_vectorizer,
    vectorizer_path
)


# ============================================================
# SAVE METRICS
# ============================================================

metrics_data = {

    "dataset": {
        "total_emails": len(df),
        "ham": int((y == 0).sum()),
        "spam": int((y == 1).sum())
    },

    "split": {
        "training": len(X_final_train),
        "testing": len(X_test)
    },

    "model": best_model_name,

    "metrics": {
        "accuracy": test_accuracy,
        "precision": test_precision,
        "recall": test_recall,
        "f1_score": test_f1
    },

    "confusion_matrix": cm.tolist(),

    "model_comparison": {

        name: {
            "accuracy": result["accuracy"],
            "precision": result["precision"],
            "recall": result["recall"],
            "f1_score": result["f1_score"]
        }

        for name, result in results.items()
    }
}


with open(
    metrics_path,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        metrics_data,
        file,
        indent=4
    )


with open(
    model_name_path,
    "w",
    encoding="utf-8"
) as file:

    file.write(best_model_name)


# ============================================================
# FINAL MESSAGE
# ============================================================

print("\n" + "=" * 70)
print("MODEL TRAINING COMPLETE")
print("=" * 70)

print("\nSaved files:")

print(f"✓ {model_path}")
print(f"✓ {vectorizer_path}")
print(f"✓ {metrics_path}")
print(f"✓ {model_name_path}")

print("\nThe best email classification model is ready.")
print("Next: integrate live message prediction into the Flask application.")