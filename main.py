from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict
from jsonschema import validate as js_validate, ValidationError
import json

# optional schema inference
try:
    from genson import SchemaBuilder
    HAS_GENSON = True
except Exception:
    HAS_GENSON = False

app = FastAPI(title="JSON Tools")

# -------- models (pydantic v2) --------
class ValidateOne(BaseModel):
    instance: Any
    schema_: Optional[dict] = Field(None, alias="schema")
    model_config = {"populate_by_name": True}

class ValidateBatch(BaseModel):
    schema_: dict = Field(..., alias="schema")
    data: List[Any]
    model_config = {"populate_by_name": True}

class FormatBody(BaseModel):
    data: Any
    indent: Optional[int] = 2
    sort_keys: Optional[bool] = False

class GenerateSchemaBody(BaseModel):
    example: Any

# in-memory schema store (ephemeral)
SCHEMAS: Dict[str, dict] = {}

# -------- endpoints --------
@app.post("/validate")
def validate_json(req: ValidateOne):
    try:
        if req.schema_:
            js_validate(instance=req.instance, schema=req.schema_)
        return {"valid": True, "errors": []}
    except ValidationError as e:
        return {"valid": False, "errors": [e.message]}

@app.post("/validate-batch")
def validate_batch(req: ValidateBatch):
    results = []
    for idx, item in enumerate(req.data):
        try:
            js_validate(instance=item, schema=req.schema_)
            results.append({"index": idx, "valid": True, "errors": []})
        except ValidationError as e:
            results.append({"index": idx, "valid": False, "errors": [e.message]})
    return {"results": results}

@app.post("/format")
def format_json(req: FormatBody):
    try:
        formatted = json.dumps(
            req.data, indent=req.indent or 2, sort_keys=bool(req.sort_keys), ensure_ascii=False
        )
        return {"formatted": formatted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Format error: {e}")

@app.post("/generate-schema")
def generate_schema(req: GenerateSchemaBody):
    if not HAS_GENSON:
        raise HTTPException(status_code=500, detail="Schema inference not available. Install genson.")
    b = SchemaBuilder()
    b.add_object(req.example)
    return {"schema": b.to_schema()}

@app.put("/schemas/{name}")
def put_schema(name: str, body: dict):
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object (schema).")
    SCHEMAS[name] = body
    return {"ok": True, "name": name}

@app.get("/schemas/{name}")
def get_schema(name: str):
    if name not in SCHEMAS:
        raise HTTPException(status_code=404, detail="Schema not found")
    return {"name": name, "schema": SCHEMAS[name]}