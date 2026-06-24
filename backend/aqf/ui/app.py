# aqf/ui/app.py
"""AQF Streamlit Demo - Unified Pipeline"""
from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd
import requests

# ── Config ─────────────────────────────────────────────────────────
API_BASE = st.secrets.get("AQF_API_URL", "http://localhost:8000")
DATA_DIR = Path("data")

st.set_page_config(page_title="AQF Unified Demo", layout="wide")

# ── CSS ─────────────────────────────────────────────────────────────
AQF_CSS = """
<style>
:root{--bg:#F8FAFC;--surface:#FFFFFF;--border:#E2E8F0;--text:#0F172A;--muted:#64748B;--blue:#2563EB;--blue-soft:#DBEAFE;--green-soft:#DCFCE7;--amber-soft:#FEF3C7;--red-soft:#FEE2E2;}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg);color:var(--text);}
.aqf-card,.aqf-warning,.aqf-empty,.aqf-success{border:1px solid var(--border);border-radius:14px;padding:16px;margin-bottom:12px;background:var(--surface);}
.aqf-warning{background:var(--amber-soft);border-color:#FCD34D;}
.aqf-empty{background:var(--red-soft);border-color:#FCA5A5;}
.aqf-success{background:var(--green-soft);border-color:#86EFAC;}
.aqf-chip{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:var(--blue-soft);border:1px solid #BFDBFE;color:#1D4ED8;font-size:12px;font-weight:600;margin:4px 6px 0 0;}
.aqf-title{font-size:20px;font-weight:700;color:var(--text);margin-bottom:6px;}
.aqf-label{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:0.04em;}
.aqf-value{font-size:14px;color:#334155;}
</style>
"""
st.markdown(AQF_CSS, unsafe_allow_html=True)

# ── Helpers ─────────────────────────────────────────────────────────
def api_post(endpoint, payload):
    try:
        r = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def api_get(endpoint):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def signature_of_state(criteria, outputs, sort, advanced):
    raw = json.dumps({"criteria": criteria, "output_fields": outputs, "sort": sort, "advanced": advanced}, sort_keys=True, default=str)
    return hashlib.md5(raw.encode()).hexdigest()

# ── State ───────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "schema_loaded": False,
        "form": None,
        "catalog": None,
        "active_criteria": [],
        "active_output": [],
        "active_advanced": {"occurrence_semantics": "ALL", "include_unknown": False, "slice_size": 1000, "result_limit": 100},
        "sort_state": None,
        "last_result": None,
        "last_signature": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── UI ──────────────────────────────────────────────────────────────
st.title("AQF Adaptive Query Forms")
st.caption("Unified pipeline supporting versioned, direct, and EHR-index JSON formats")

# Sidebar
with st.sidebar:
    st.markdown("## Workspace")
    data_dir = st.text_input("Dataset folder", value="data")
    
    if st.button("Load / Refresh Schema", use_container_width=True):
        with st.spinner("Loading..."):
            result = api_post("/api/load", {"data_dir": data_dir})
            if result:
                st.session_state.form = result["form"]
                st.session_state.catalog = result  # Store full response
                st.session_state.schema_loaded = True
                st.success(f"Loaded: {result['composition_label']}")
                st.json(result["stats"])
    
    if st.button("Reset Query", use_container_width=True):
        st.session_state.active_criteria = []
        st.session_state.active_output = []
        st.session_state.sort_state = None
        st.session_state.last_result = None
    
    st.markdown("---")
    health = api_get("/api/health")
    if health:
        st.caption(f"API: {health['status']} v{health.get('version', '?')}")

# Main area
if not st.session_state.schema_loaded:
    st.info("Select a dataset folder and click **Load / Refresh Schema** to begin.")
    st.stop()

form = st.session_state.form

# Query chips
chips = []
for c in st.session_state.active_criteria[:5]:
    chips.append(f"FILTER: {c.get('element_name', 'Field')} {c.get('operator', '')} {c.get('value', '')}")
for o in st.session_state.active_output[:5]:
    chips.append(f"OUTPUT: {o.get('name', 'Field')}")
if st.session_state.sort_state:
    chips.append(f"SORT: {st.session_state.sort_state.get('element_name', 'Field')} ({st.session_state.sort_state.get('direction', 'asc')})")

if chips:
    st.markdown("".join(f'<span class="aqf-chip">{c}</span>' for c in chips), unsafe_allow_html=True)

# Tabs
tab_criteria, tab_output, tab_advanced, tab_results = st.tabs(["Criteria", "Output", "Advanced", "Results"])

with tab_criteria:
    st.subheader(form["composition_label"])
    with st.form("criteria_form"):
        search = st.text_input("Search fields", key="crit_search")
        widget_meta = []
        
        for group in form["criteria_groups"]:
            with st.expander(group["group_label"], expanded=False):
                for subgroup in group["subgroups"]:
                    st.markdown(f"**{subgroup['label']}**")
                    for fld in subgroup["fields"]:
                        hay = f"{fld['full_label']} {fld['label']} {subgroup['label']}".lower()
                        if search and search.lower() not in hay:
                            continue
                        
                        cols = st.columns([1, 2, 2, 4])
                        use_key = f"use_{fld['field_key']}"
                        op_key = f"op_{fld['field_key']}"
                        val_key = f"val_{fld['field_key']}"
                        suggest_key = f"suggest_{fld['field_key']}"
                        
                        with cols[0]:
                            st.checkbox("Use", key=use_key)
                        with cols[1]:
                            op_labels = [f"{o['phrase']} ({o['op']})" for o in fld["operators"]]
                            st.selectbox("Condition", op_labels, key=op_key)
                        with cols[2]:
                            mode = fld.get("suggestion_mode", "none")
                            suggestions = fld.get("suggested_values", [])
                            if mode in ("categorical", "boolean") and suggestions:
                                st.selectbox("Value", ["<custom>"] + suggestions, key=suggest_key)
                                st.text_input("Custom", key=val_key)
                            else:
                                st.text_input("Value", key=val_key)
                        widget_meta.append(fld)
        
        if st.form_submit_button("Apply Filters"):
            new_criteria = []
            for fld in widget_meta:
                use_key = f"use_{fld['field_key']}"
                if not st.session_state.get(use_key, False):
                    continue
                op_choice = st.session_state.get(f"op_{fld['field_key']}")
                op_obj = next((o for o in fld["operators"] if f"{o['phrase']} ({o['op']})" == op_choice), None)
                if not op_obj:
                    continue
                
                mode = fld.get("suggestion_mode", "none")
                suggestions = fld.get("suggested_values", [])
                value = None
                if mode in ("categorical", "boolean") and suggestions:
                    selected = st.session_state.get(f"suggest_{fld['field_key']}")
                    custom = st.session_state.get(f"val_{fld['field_key']}")
                    value = custom if selected == "<custom>" else selected
                else:
                    value = st.session_state.get(f"val_{fld['field_key']}")
                
                if op_obj["op"] not in ("is_known", "is_unknown") and (value is None or str(value).strip() == ""):
                    continue
                
                new_criteria.append({
                    "field_key": fld["field_key"],
                    "operator": op_obj["op"],
                    "value": None if op_obj["op"] in ("is_known", "is_unknown") else value
                })
            st.session_state.active_criteria = new_criteria
            st.success(f"Applied {len(new_criteria)} filters")

with tab_output:
    st.subheader("Output Fields")
    output_defs = form["output_fields"]
    default = [o["name"] for o in st.session_state.active_output] if st.session_state.active_output else []
    selected = st.multiselect("Choose columns", [f["label"] for f in output_defs], default=default)
    
    sort_choices = {f["label"]: f["field_key"] for f in output_defs}
    sort_label = st.selectbox("Sort by", ["(none)"] + list(sort_choices.keys()))
    sort_dir = st.selectbox("Direction", ["asc", "desc"])
    
    if st.button("Apply Output"):
        selected_outputs = []
        for lbl in selected:
            f = next((x for x in output_defs if x["label"] == lbl), None)
            if f:
                selected_outputs.append({"field_key": f["field_key"], "name": f["label"], "dv_type": f["dv_type"]})
        st.session_state.active_output = selected_outputs
        if sort_label != "(none)":
            st.session_state.sort_state = {"field_key": sort_choices[sort_label], "direction": sort_dir}
        else:
            st.session_state.sort_state = None

with tab_advanced:
    st.subheader("Advanced Settings")
    sem = st.selectbox("Occurrence semantics", ["ALL", "ANY"])
    inc_unknown = st.checkbox("Include unknown values")
    slice_sz = st.number_input("Slice size", 10, 10000, 1000, 10)
    res_limit = st.number_input("Result limit", 10, 5000, 100, 10)
    st.session_state.active_advanced = {
        "occurrence_semantics": sem,
        "include_unknown": inc_unknown,
        "slice_size": slice_sz,
        "result_limit": res_limit
    }

with tab_results:
    if st.button("Run Query", use_container_width=True):
        req = {
            "data_dir": data_dir,
            "criteria": st.session_state.active_criteria,
            "output_fields": st.session_state.active_output,
            "sort": st.session_state.sort_state,
            "advanced": st.session_state.active_advanced
        }
        with st.spinner("Executing..."):
            result = api_post("/api/query", req)
            if result:
                st.session_state.last_result = result
                st.session_state.last_signature = signature_of_state(
                    st.session_state.active_criteria,
                    st.session_state.active_output,
                    st.session_state.sort_state,
                    st.session_state.active_advanced
                )
    
    if st.session_state.last_result:
        r = st.session_state.last_result
        c1, c2, c3 = st.columns(3)
        c1.metric("Scanned", r["scanned"])
        c2.metric("Matched", r["matched"])
        c3.metric("Sec/doc", f"{r.get('sec_per_doc', 0):.6f}")
        
        st.markdown(r.get("summary", ""))
        
        if r.get("funnel"):
            st.markdown("### Query Funnel")
            st.dataframe(pd.DataFrame(r["funnel"]), use_container_width=True)
        
        if r.get("rows"):
            st.markdown("### Results")
            df = pd.DataFrame(r["rows"])
            visible = [c for c in df.columns if c != "_file"]
            st.dataframe(df[visible], use_container_width=True)
        else:
            st.info("No matches found.")
    else:
        st.info("Configure filters and click **Run Query**.")