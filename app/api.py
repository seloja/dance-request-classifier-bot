from fastapi import FastAPI

from app.classifier import get_classifier
from app.responses import CLASS_NAMES, EMPTY_TEXT_ANSWER, get_response
from app.schemas import ClassifyRequest, ClassifyResponse


app = FastAPI(title="Dance Studio Request Classifier")


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "dance request classifier"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/classify", response_model=ClassifyResponse)
def classify(request: ClassifyRequest) -> ClassifyResponse:
    text = request.text
    if not text.strip():
        return ClassifyResponse(
            text=text,
            label="admin_other",
            class_name=CLASS_NAMES["admin_other"],
            confidence=0.0,
            answer=EMPTY_TEXT_ANSWER,
        )

    prediction = get_classifier().predict(text)
    label = prediction.get("label", "admin_other")
    if label not in CLASS_NAMES:
        label = "admin_other"

    response = get_response(label)
    return ClassifyResponse(
        text=text,
        label=label,
        class_name=response["class_name"],
        confidence=round(float(prediction.get("confidence", 0.0)), 4),
        answer=response["answer"],
    )
