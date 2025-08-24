from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Optional
from jsonschema import validate as js_validate, ValidationError

app = FastAPI(title="JSON Validator")

class ValidationRequest(BaseModel):
    instance: Any
    schema: Optional[dict] = None

@app.post("/json/validate")
def validate_json(req: ValidationRequest):
    try:
        if req.schema:
            js_validate(instance=req.instance, schema=req.schema)
        return {"valid": True, "errors": []}
    except ValidationError as e:
        return {"valid": False, "errors": [e.message]}