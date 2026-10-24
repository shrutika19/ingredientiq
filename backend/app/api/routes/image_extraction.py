
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.services.vision_extraction import extract_ingredient_text
from app.services.gemini_client import GeminiConfigurationError

router = APIRouter(
    prefix="/ingredients",
    tags=["Image Extraction"],
)

MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000

ALLOWED_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class ImageExtractionResponse(BaseModel):
    status: str = "completed"
    ingredient_text: str
    extraction_status: str
    warnings: list[str]


def reject(status_code: int, code: str, message: str):
    raise HTTPException(
        status_code=status_code,
        detail={"error": code, "message": message},
    )


@router.post(
    "/extract-image",
    response_model=ImageExtractionResponse,
)
async def extract_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_FORMATS.values():
        reject(400, "INVALID_IMAGE", "Unsupported image type.")

    # Read one byte beyond the limit to detect oversized files.
    image_bytes = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if len(image_bytes) > MAX_FILE_SIZE:
        reject(413, "IMAGE_TOO_LARGE", "Maximum size is 5 MB.")

    if not image_bytes:
        reject(400, "INVALID_IMAGE", "Image is empty.")

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            if image.format not in ALLOWED_FORMATS:
                reject(400, "INVALID_IMAGE", "Unsupported image format.")

            if image.width < 100 or image.height < 100:
                reject(400, "INVALID_IMAGE", "Image resolution is too low.")

            if image.width * image.height > MAX_PIXELS:
                reject(400, "INVALID_IMAGE", "Image dimensions are too large.")

            detected_mime = ALLOWED_FORMATS[image.format]
            if file.content_type != detected_mime:
                reject(400, "INVALID_IMAGE", "Image type mismatch.")

            image.verify()

    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        reject(400, "INVALID_IMAGE", "Invalid or corrupted image.")

    try:
        text = await run_in_threadpool(
            extract_ingredient_text,
            image_bytes,
            detected_mime,
        )
    except GeminiConfigurationError:
        reject(503, "VISION_UNAVAILABLE", "Extraction unavailable.")

    if not text:
        return ImageExtractionResponse(
            ingredient_text="",
            extraction_status="unreadable",
            warnings=["No readable ingredient list was detected."],
        )

    return ImageExtractionResponse(
        ingredient_text=text,
        extraction_status="review_required",
        warnings=[],
    )
