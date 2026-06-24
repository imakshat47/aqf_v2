# aqf/api/main.py
"""AQF Unified FastAPI Backend - Production Ready"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aqf.core import get_cache
from aqf.loaders import group_compositions_by_archetype
from aqf.schema import build_union_schema, build_field_catalog, build_form_definition
from aqf.query import compile_query, run_query, build_query_summary_markdown

app = FastAPI(
    title="AQF API",
    version="3.0",
    description="Adaptive Query Forms - Unified Pipeline for all openEHR JSON types"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_cache = {}

# ── Pydantic Models ─────────────────────────────────────────────────

class LoadRequest(BaseModel):
    data_dir: str = "data"

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
    data_dir: str = "data"
    criteria: List[CriterionModel] = []
    output_fields: List[OutputFieldModel] = []
    sort: Optional[SortModel] = None
    advanced: AdvancedModel = AdvancedModel()

# ── Helpers ─────────────────────────────────────────────────────────

def _load_schema(data_dir: str):
    key = str(Path(data_dir).resolve())
    if key in _cache:
        return _cache[key]

    folder = Path(__file__).resolve().parent.parent.parent / Path(data_dir)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Data directory not found: {data_dir}")

    valid_groups, skipped = group_compositions_by_archetype(folder)
    if not valid_groups:
        raise HTTPException(status_code=422, detail="No valid composition files found.")

    comp_arch = max(valid_groups.items(), key=lambda x: len(x[1]))[0]
    normalized_docs = [d for _, d in valid_groups[comp_arch]]
    files = [p for p, _ in valid_groups[comp_arch]]

    union = build_union_schema(normalized_docs)
    catalog = build_field_catalog(union)
    form = build_form_definition(union, catalog)

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

def _enrich_criteria(criteria, catalog):
    fk_map = {f["field_key"]: f for f in catalog}
    out = []
    for c in criteria:
        f = fk_map.get(c.field_key, {})
        out.append({
            "field_key": c.field_key, "operator": c.operator, "value": c.value,
            "entry_name": f.get("entry_name", ""),
            "cluster_path_str": f.get("cluster_path_str", ""),
            "element_name": f.get("element_name", c.field_key),
            "dv_type": f.get("dv_type", ""),
        })
    return out

def _enrich_outputs(outputs, catalog):
    fk_map = {f["field_key"]: f for f in catalog}
    out = []
    for o in outputs:
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

def _enrich_sort(sort, catalog):
    if not sort:
        return None
    fk_map = {f["field_key"]: f for f in catalog}
    f = fk_map.get(sort.field_key, {})
    return {
        "field_key": sort.field_key, "direction": sort.direction,
        "entry_name": f.get("entry_name", ""),
        "cluster_path_str": f.get("cluster_path_str", ""),
        "element_name": f.get("element_name", sort.field_key),
    }

# ── Routes ─────────────────────────────────────────────────────────

@app.post("/api/load")
def load_dataset(req: LoadRequest):
    """Load dataset, build union schema, field catalog, and form definition."""
    bundle = _load_schema(req.data_dir)
    union = bundle["union"]

    groups_count = len(union.get("groups", {}))
    subgroups_count = sum(len(g["subgroups"]) for g in union["groups"].values())
    fields_count = len(bundle["catalog"])
    suggestion_fields = sum(1 for f in bundle["catalog"] if f.get("suggested_values"))
    null_fields = sum(1 for f in bundle["catalog"] if f.get("has_null_flavour"))

    return {
        "composition_label": union["composition_label"],
        "composition_archetype": bundle["comp_arch"],
        "stats": {
            "files": len(bundle["files"]),
            "skipped": len(bundle["skipped"]),
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
    """Compile and execute AQF query. Returns matched rows + funnel."""
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
    result = run_query(
        files[:req.advanced.slice_size],
        plan,
        occurrence_semantics=req.advanced.occurrence_semantics,
        limit=req.advanced.result_limit,
    )

    # Sort
    if enriched_sort and result.get("rows"):
        fk = enriched_sort["field_key"]
        rev = enriched_sort["direction"] == "desc"
        result["rows"] = sorted(result["rows"], key=lambda r: (r.get(fk) is None, r.get(fk)), reverse=rev)

    # Remap to readable labels
    readable_rows = []
    for row in result.get("rows", []):
        readable = {k: v for k, v in row.items() if k == "_file"}
        for k, v in row.items():
            if k != "_file":
                readable[fk_to_label.get(k, k)] = v
        readable_rows.append(readable)

    readable_funnel = []
    for stage in result.get("funnel", []):
        s = dict(stage)
        if "field_key" in s:
            s["label"] = fk_to_label.get(s["field_key"], s["field_key"])
        readable_funnel.append(s)

    summary_md = build_query_summary_markdown(enriched_criteria, enriched_outputs, enriched_sort, req.advanced.model_dump())

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

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "3.0", "cache_keys": list(_cache.keys())}