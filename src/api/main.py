# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# FIXED: Import directly from the api package sibling
from .analytical import router as analytical_router 

app = FastAPI(
    title="Scope Credit Risk Star-Schema Analytics API",
    description="High-performance read layer exposing point-in-time analytical records and history data.",
    version="1.0.0"
)

# Enable CORS for BI dashboards or frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FIXED: Use the corrected router variable name here
app.include_router(analytical_router, prefix="/api/v1")

@app.get("/health", tags=["Infrastructure System Check"])
def health_check():
    return {"status": "healthy", "timestamp": "2026-07-10T11:19:35Z"}