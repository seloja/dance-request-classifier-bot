from pathlib import Path

import numpy as np
import pandas as pd
from datasets import Dataset
from sklearn.metrics import accuracy_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from app.config import settings
from app.classifier import LABELS


TRAIN_PATH = Path("data/train.csv")
TEST_PATH = Path("data/test.csv")
MODEL_DIR = Path(settings.model_dir)
MAX_LENGTH = 128

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
    return {"accuracy": accuracy_score(labels, predictions)}


def main() -> None:
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

    train_dataset = Dataset.from_pandas(train_df).map(tokenize, batched=True)
    test_dataset = Dataset.from_pandas(test_df).map(tokenize, batched=True)

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
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=16,
        num_train_epochs=5,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
        logging_steps=20,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print(f"Accuracy: {metrics.get('eval_accuracy', 0.0):.4f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(MODEL_DIR))
    tokenizer.save_pretrained(str(MODEL_DIR))
    print(f"Model saved to {MODEL_DIR}")


if __name__ == "__main__":
    main()
