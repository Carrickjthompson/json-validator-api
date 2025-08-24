from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional, List, Dict
from jsonschema import validate as js_validate, ValidationError
import json

# Optional: schema inference
try:
    from genson import SchemaBuilder
    HAS_GENSON = True
except Exception:
    HAS_GENSON = False

app = FastAPI(title="JSON Tools")

# ---------- Models ----------
class ValidateOne(BaseModel):
    instance: Any
    schema: Optional[dict] = None

class ValidateBatch(BaseModel):
    schema: dict
    data: List[Any]

class FormatBody(BaseModel):
    data: Any
    indent: Optional[int] = 2
    sort_keys: Optional[bool] = False

class GenerateSchemaBody(BaseModel):
    example: Any

# ---------- In-memory schema store (ephemeral) ----------
SCHEMAS: Dict[str, dict] = {}

# ---------- Endpoints ----------

# 1) Single validate (existing)
@app.post("/validate")
def validate_json(req: ValidateOne):
    try:
        if req.schema:
            js_validate(instance=req.instance, schema=req.schema)
        return {"valid": True, "errors": []}
    except ValidationError as e:
        return {"valid": False, "errors": [e.message]}

# 2) Batch validate
@app.post("/validate-batch")
def validate_batch(req: ValidateBatch):
    results = []
    for idx, item in enumerate(req.data):
        try:
            js_validate(instance=item, schema=req.schema)
            results.append({"index": idx, "valid": True, "errors": []})
        except ValidationError as e:
            results.append({"index": idx, "valid": False, "errors": [e.message]})
    return {"results": results}

# 3) Pretty/normalize JSON
@app.post("/format")
def format_json(req: FormatBody):
    try:
        formatted = json.dumps(req.data, indent=req.indent or 2, sort_keys=bool(req.sort_keys), ensure_ascii=False)
        return {"formatted": formatted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Format error: {e}")

# 4) Generate schema from example
@app.post("/generate-schema")
def generate_schema(req: GenerateSchemaBody):
    if not HAS_GENSON:
        raise HTTPException(status_code=500, detail="Schema inference not available. Install genson.")
    builder = SchemaBuilder()
    builder.add_object(req.example)
    return {"schema": builder.to_schema()}

# 5) Schema repository: save/fetch
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