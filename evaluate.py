from pathlib import Path

import pandas as pd

from app.classifier import get_classifier


DATA_DIR = Path("data")
RESULT_PATH = DATA_DIR / "evaluation_results.csv"


def load_dataset() -> pd.DataFrame:
    test_path = DATA_DIR / "test.csv"
    dataset_path = DATA_DIR / "dataset.csv"
    path = test_path if test_path.exists() else dataset_path
    if not path.exists():
        raise FileNotFoundError("No evaluation data found. Add data/test.csv or data/dataset.csv.")

    data = pd.read_csv(path)
    required_columns = {"text", "label"}
    if not required_columns.issubset(data.columns):
        raise ValueError("CSV file must contain text,label columns.")
    return data


def main() -> None:
    data = load_dataset()
    classifier = get_classifier()
    rows = []

    for _, row in data.iterrows():
        prediction = classifier.predict(str(row["text"]))
        predicted_label = prediction["label"]
        true_label = row["label"]
        rows.append(
            {
                "text": row["text"],
                "true_label": true_label,
                "predicted_label": predicted_label,
                "confidence": prediction["confidence"],
                "is_correct": predicted_label == true_label,
            }
        )

    results = pd.DataFrame(rows)
    results.to_csv(RESULT_PATH, index=False)

    total = len(results)
    correct = int(results["is_correct"].sum())
    incorrect = total - correct
    accuracy = correct / total if total else 0.0

    print(f"Total: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {incorrect}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Saved results to {RESULT_PATH}")


if __name__ == "__main__":
    main()
