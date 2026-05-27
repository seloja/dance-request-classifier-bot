import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import Dataset
from sklearn.metrics import accuracy_score, classification_report, f1_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    set_seed,
)

from app.config import settings
from app.classifier import LABELS


TRAIN_PATH = Path("data/train.csv")
TEST_PATH = Path("data/test.csv")
MODEL_DIR = Path(settings.model_dir)
MAX_LENGTH = 128
SEED = 42
LEARNING_RATE = 5e-5
NUM_TRAIN_EPOCHS = 15
BATCH_SIZE = 16
WEIGHT_DECAY = 0.01
WARMUP_STEPS = 38
METRICS_PATH = Path("data/transformer_metrics.json")
PREDICTIONS_PATH = Path("data/transformer_predictions.csv")

label2id = {label: index for index, label in enumerate(LABELS)}
id2label = {index: label for label, index in label2id.items()}


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    data = pd.read_csv(path)
    if not {"text", "label"}.issubset(data.columns):
        raise ValueError(f"{path} must contain text,label columns.")
    data = data[["text", "label"]].dropna()
    data["label_id"] = data["label"].map(label2id)
    if data["label_id"].isna().any():
        unknown = sorted(set(data.loc[data["label_id"].isna(), "label"]))
        raise ValueError(f"Unknown labels in {path}: {unknown}")
    data["label_id"] = data["label_id"].astype(int)
    return data


def compute_metrics(eval_prediction) -> dict:
    logits, labels = eval_prediction
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "macro_f1": f1_score(labels, predictions, average="macro", zero_division=0),
    }


def set_reproducibility() -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    set_seed(SEED)


def main() -> None:
    set_reproducibility()
    train_df = read_csv(TRAIN_PATH)
    test_df = read_csv(TEST_PATH)

    tokenizer = AutoTokenizer.from_pretrained(settings.model_name)

    def tokenize(batch):
        tokenized = tokenizer(
            batch["text"],
            truncation=True,
            padding="max_length",
            max_length=MAX_LENGTH,
        )
        tokenized["labels"] = batch["label_id"]
        return tokenized

    train_dataset = Dataset.from_pandas(train_df[["text", "label_id"]]).map(
        tokenize,
        batched=True,
        remove_columns=["text", "label_id"],
    )
    test_dataset = Dataset.from_pandas(test_df[["text", "label_id"]]).map(
        tokenize,
        batched=True,
        remove_columns=["text", "label_id"],
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        settings.model_name,
        num_labels=len(LABELS),
        label2id=label2id,
        id2label=id2label,
    )

    training_args = TrainingArguments(
        output_dir=str(MODEL_DIR / "checkpoints"),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        num_train_epochs=NUM_TRAIN_EPOCHS,
        weight_decay=WEIGHT_DECAY,
        warmup_steps=WARMUP_STEPS,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        greater_is_better=True,
        save_total_limit=2,
        dataloader_pin_memory=False,
        seed=SEED,
        data_seed=SEED,
        logging_steps=20,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        processing_class=tokenizer,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print(f"Accuracy: {metrics.get('eval_accuracy', 0.0):.4f}")
    print(f"Macro F1: {metrics.get('eval_macro_f1', 0.0):.4f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(MODEL_DIR))
    tokenizer.save_pretrained(str(MODEL_DIR))
    print(f"Model saved to {MODEL_DIR}")

    prediction_output = trainer.predict(test_dataset)
    shifted_logits = prediction_output.predictions - prediction_output.predictions.max(
        axis=1,
        keepdims=True,
    )
    probabilities = np.exp(shifted_logits)
    probabilities = probabilities / probabilities.sum(axis=1, keepdims=True)
    predicted_ids = np.argmax(probabilities, axis=-1)

    predictions_df = test_df[["text", "label"]].copy()
    predictions_df["predicted_label"] = [id2label[int(index)] for index in predicted_ids]
    predictions_df["confidence"] = probabilities.max(axis=1)
    predictions_df["is_correct"] = predictions_df["label"] == predictions_df["predicted_label"]
    predictions_df.to_csv(PREDICTIONS_PATH, index=False)

    report = classification_report(
        test_df["label_id"],
        predicted_ids,
        labels=list(range(len(LABELS))),
        target_names=LABELS,
        output_dict=True,
        zero_division=0,
    )
    metrics_payload = {
        "model_name": settings.model_name,
        "model_dir": str(MODEL_DIR),
        "seed": SEED,
        "learning_rate": LEARNING_RATE,
        "num_train_epochs": NUM_TRAIN_EPOCHS,
        "batch_size": BATCH_SIZE,
        "weight_decay": WEIGHT_DECAY,
        "warmup_steps": WARMUP_STEPS,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "accuracy": float(metrics.get("eval_accuracy", 0.0)),
        "macro_f1": float(metrics.get("eval_macro_f1", 0.0)),
        "classification_report": report,
    }
    METRICS_PATH.write_text(
        json.dumps(metrics_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Metrics saved to {METRICS_PATH}")
    print(f"Predictions saved to {PREDICTIONS_PATH}")


if __name__ == "__main__":
    main()
