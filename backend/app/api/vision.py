"""
FastAPI router for Vision. Delegates to VisionService (Groq + qwen3.8-27b).
"""
from fastapi import APIRouter, UploadFile, File
import logging

from app.services.vision_service import VisionService

router = APIRouter()
logger = logging.getLogger("aarogyatriage.vision")

_vision = VisionService()


@router.post("/vision/analyze")
async def analyze_image(image: UploadFile = File(...)):
    contents = await image.read()
    result = _vision.analyze_image(contents, image.filename or "photo.png")

    if result.get("status") == "error":
        return {"success": False, "error": result.get("message", "Vision failed")}

    finding = result.get("finding") or result.get("observation") or "No findings"
    return {
        "success": True,
        "data": {
            "observations": [finding],
            "confidence": result.get("confidence", 0.9),
            "location": result.get("location"),
            "characteristics": result.get("characteristics", []),
            "_source": result.get("source", "groq/qwen3.8-27b"),
        },
    }