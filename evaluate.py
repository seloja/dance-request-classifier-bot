import argparse
from pathlib import Path

import pandas as pd

from app.classifier import create_classifier


DATA_DIR = Path("data")
RESULT_PATH = DATA_DIR / "evaluation_results.csv"
BASELINE_ACCURACY_TARGET = 0.85


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate dance request classifier.")
    parser.add_argument(
        "--classifier",
        choices=["baseline", "transformer"],
        default=None,
        help="Classifier type to evaluate. By default uses CLASSIFIER_TYPE from .env.",
    )
    parser.add_argument(
        "--output",
        default=str(RESULT_PATH),
        help="Path to CSV file with evaluation predictions.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = load_dataset()
    classifier = create_classifier(args.classifier)
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
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)

    total = len(results)
    correct = int(results["is_correct"].sum())
    incorrect = total - correct
    accuracy = correct / total if total else 0.0

    print(f"Total: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {incorrect}")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Baseline target: {BASELINE_ACCURACY_TARGET:.4f}")
    print(
        "Transformer is acceptable for demo: "
        f"{accuracy >= BASELINE_ACCURACY_TARGET}"
    )
    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    main()
