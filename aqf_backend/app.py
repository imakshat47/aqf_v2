from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aqf_backend.routers.health import router as health_router
from aqf_backend.routers.query import router as query_router

app = FastAPI(title="AQF Backend", version="2.0.0", description="AQF clinical query backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router)
app.include_router(query_router)

@app.get("/")
def root():
    return {"service": "AQF Backend", "status": "running"}
