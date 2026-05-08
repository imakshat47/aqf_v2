# api.py  — AQF FastAPI backend
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── AQF modules ───────────────────────────────────────────────────────────────
from composition_loader import group_docs_by_composition_archetype
from schema_union_builder import build_union_schema
from field_catalog import build_field_catalog
from form_definition_builder import build_form_definition
from query_compiler import compile_query
from query_executor import run_query
from query_summary import build_query_summary_markdown

app = FastAPI(title="AQF API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory cache (per server session) ─────────────────────────────────────
_cache: Dict[str, Any] = {}

# ── Pydantic models ───────────────────────────────────────────────────────────

class LoadRequest(BaseModel):
    data_dir: str = "dataset/orbda1"

class CriterionModel(BaseModel):
    field_key: str
    operator: str
    value: Optional[Any] = None

class OutputFieldModel(BaseModel):
    field_key: str
    name: str
    dv_type: str = ""

class SortModel(BaseModel):
    field_key: str
    direction: str = "asc"

class AdvancedModel(BaseModel):
    occurrence_semantics: str = "ALL"
    include_unknown: bool = False
    slice_size: int = 1000
    result_limit: int = 100

class QueryRequest(BaseModel):
    data_dir: str = "dataset/orbda1"
    criteria: List[CriterionModel] = []
    output_fields: List[OutputFieldModel] = []
    sort: Optional[SortModel] = None
    advanced: AdvancedModel = AdvancedModel()

class SummaryRequest(BaseModel):
    criteria: List[Dict] = []
    output_fields: List[Dict] = []
    sort: Optional[Dict] = None
    advanced: Dict = {}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_schema(data_dir: str):
    key = str(Path(data_dir).resolve())
    if key in _cache:
        return _cache[key]

    folder = Path(data_dir)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Data directory not found: {data_dir}")

    valid_groups, skipped = group_docs_by_composition_archetype(folder)
    if not valid_groups:
        raise HTTPException(status_code=422, detail="No valid composition files found in the dataset folder.")

    comp_arch = max(valid_groups.items(), key=lambda x: len(x[1]))[0]
    docs = [d for _, d in valid_groups[comp_arch]]
    files = [p for p, _ in valid_groups[comp_arch]]

    union = build_union_schema(docs)
    catalog = build_field_catalog(union)
    form = build_form_definition(union, catalog)

    # Build field_key → label lookup
    fk_to_label = {f["field_key"]: f["label"] for f in catalog}

    _cache[key] = {
        "comp_arch": comp_arch,
        "union": union,
        "catalog": catalog,
        "form": form,
        "files": files,
        "skipped": skipped,
        "fk_to_label": fk_to_label,
    }
    return _cache[key]

def _enrich_criteria(criteria: List[CriterionModel], catalog: List[Dict]) -> List[Dict]:
    fk_map = {f["field_key"]: f for f in catalog}
    out = []
    for c in criteria:
        f = fk_map.get(c.field_key, {})
        out.append({
            "field_key": c.field_key,
            "operator": c.operator,
            "value": c.value,
            "entry_name": f.get("entry_name", ""),
            "cluster_path_str": f.get("cluster_path_str", ""),
            "element_name": f.get("element_name", c.field_key),
            "dv_type": f.get("dv_type", ""),
        })
    return out

def _enrich_outputs(output_fields: List[OutputFieldModel], catalog: List[Dict]) -> List[Dict]:
    fk_map = {f["field_key"]: f for f in catalog}
    out = []
    for o in output_fields:
        f = fk_map.get(o.field_key, {})
        out.append({
            "field_key": o.field_key,
            "name": f.get("label", o.name),
            "dv_type": f.get("dv_type", o.dv_type),
            "entry_name": f.get("entry_name", ""),
            "cluster_path_str": f.get("cluster_path_str", ""),
            "element_name": f.get("element_name", ""),
        })
    return out

def _enrich_sort(sort: Optional[SortModel], catalog: List[Dict]) -> Optional[Dict]:
    if not sort:
        return None
    fk_map = {f["field_key"]: f for f in catalog}
    f = fk_map.get(sort.field_key, {})
    return {
        "field_key": sort.field_key,
        "direction": sort.direction,
        "entry_name": f.get("entry_name", ""),
        "cluster_path_str": f.get("cluster_path_str", ""),
        "element_name": f.get("element_name", sort.field_key),
    }

# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/load")
def load_dataset(req: LoadRequest):
    """
    Load the dataset, build union schema, field catalog, and form definition.
    Returns the full form definition the React frontend renders.
    """
    bundle = _load_schema(req.data_dir)
    union = bundle["union"]

    # Schema stats
    groups_count = len(union.get("groups", {}))
    subgroups_count = sum(len(g["subgroups"]) for g in union["groups"].values())
    fields_count = len(bundle["catalog"])
    suggestion_fields = sum(1 for f in bundle["catalog"] if f.get("suggested_values"))
    null_fields = sum(1 for f in bundle["catalog"] if f.get("has_null_flavour"))
    files_count = len(bundle["files"])
    skipped_count = len(bundle["skipped"])

    return {
        "composition_label": union["composition_label"],
        "composition_archetype": bundle["comp_arch"],
        "stats": {
            "files": files_count,
            "skipped": skipped_count,
            "groups": groups_count,
            "subgroups": subgroups_count,
            "fields": fields_count,
            "suggestion_fields": suggestion_fields,
            "null_fields": null_fields,
        },
        "form": bundle["form"],
    }

@app.post("/api/query")
def execute_query(req: QueryRequest):
    """
    Compile and execute an AQF query. Returns matched rows + funnel.
    Rows are returned with readable labels instead of raw field_keys.
    """
    bundle = _load_schema(req.data_dir)
    catalog = bundle["catalog"]
    files = bundle["files"]
    fk_to_label = bundle["fk_to_label"]

    enriched_criteria = _enrich_criteria(req.criteria, catalog)
    enriched_outputs = _enrich_outputs(req.output_fields, catalog)
    enriched_sort = _enrich_sort(req.sort, catalog)

    form_state = {
        "criteria": [{"field_key": c["field_key"], "operator": c["operator"], "value": c["value"]} for c in enriched_criteria],
        "output_fields": [{"field_key": o["field_key"], "name": o["name"], "dv_type": o["dv_type"]} for o in enriched_outputs],
        "sort": {"field_key": enriched_sort["field_key"], "direction": enriched_sort["direction"]} if enriched_sort else None,
        "advanced": req.advanced.model_dump(),
    }

    plan = compile_query(form_state)
    slice_size = int(req.advanced.slice_size)
    result = run_query(
        files[:slice_size],
        plan,
        occurrence_semantics=req.advanced.occurrence_semantics,
        limit=int(req.advanced.result_limit),
    )

    # Sort if requested
    if enriched_sort and result.get("rows"):
        fk = enriched_sort["field_key"]
        rev = enriched_sort["direction"] == "desc"
        result["rows"] = sorted(
            result["rows"],
            key=lambda r: (r.get(fk) is None, r.get(fk)),
            reverse=rev,
        )

    # Remap field_keys to readable labels in rows
    readable_rows = []
    for row in result.get("rows", []):
        readable = {}
        for k, v in row.items():
            if k == "_file":
                readable["_file"] = v
            else:
                readable[fk_to_label.get(k, k)] = v
        readable_rows.append(readable)

    # Funnel with readable labels
    readable_funnel = []
    for stage in result.get("funnel", []):
        s = dict(stage)
        if "field_key" in s:
            s["label"] = fk_to_label.get(s["field_key"], s["field_key"])
        readable_funnel.append(s)

    # Build query summary
    summary_md = build_query_summary_markdown(
        enriched_criteria, enriched_outputs, enriched_sort, req.advanced.model_dump()
    )

    return {
        "scanned": result["scanned"],
        "matched": result["matched"],
        "elapsed_sec": result["elapsed_sec"],
        "sec_per_doc": result["sec_per_doc"],
        "rows": readable_rows,
        "funnel": readable_funnel,
        "summary": summary_md,
        "output_labels": [fk_to_label.get(o["field_key"], o["name"]) for o in enriched_outputs],
    }

@app.post("/api/summary")
def get_summary(req: SummaryRequest):
    summary_md = build_query_summary_markdown(
        req.criteria, req.output_fields, req.sort, req.advanced
    )
    return {"summary": summary_md}

@app.get("/api/health")
def health():
    return {"status": "ok", "cache_keys": list(_cache.keys())}
