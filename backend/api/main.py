from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import backend.api.services.citizen_reporter as citizen_reporter
import backend.api.services.nlp_analyzer as nlp_analyzer

app = FastAPI(title="Unified Hazard API")

# Development CORS - open to all origins. Lock this down for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploaded media folder at /media/hazard so URLs returned by citizen_reporter work
app.mount(
    "/media/hazard",
    StaticFiles(directory=citizen_reporter.report_manager.media_storage_path),
    name="hazard_media"
)

# Include routers from modules
app.include_router(citizen_reporter.router)
app.include_router(nlp_analyzer.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Unified Hazard API running"}
