from pydantic import BaseModel


class ClassifyRequest(BaseModel):
    text: str


class ClassifyResponse(BaseModel):
    text: str
    label: str
    class_name: str
    confidence: float
    answer: str
