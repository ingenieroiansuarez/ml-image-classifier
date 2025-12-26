import os
from typing import List

from app import db
from app import settings as config
from app import utils
from app.auth.jwt import get_current_user
from app.model.schema import PredictRequest, PredictResponse
from app.model.services import model_predict
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

router = APIRouter(tags=["Model"], prefix="/model")


@router.post("/predict")
async def predict(file: UploadFile, current_user=Depends(get_current_user)):
    rpse = {"success": False, "prediction": None, "score": None}
    # To correctly implement this endpoint you should:
    #   1. Check a file was sent and that file is an image, see `allowed_file()` from `utils.py`.
    #   2. Store the image to disk, calculate hash (see `get_file_hash()` from `utils.py`) before
    #      to avoid re-writing an image already uploaded.
    #   3. Send the file to be processed by the `model` service, see `model_predict()` from `services.py`.
    #   4. Update and return `rpse` dict with the corresponding values
    # If user sends an invalid request (e.g. no file provided) this endpoint
    # should return `rpse` dict with default values HTTP 400 Bad Request code
    # TODO
    
    # Check if file was sent and is valid
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not utils.allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="File type is not supported.")
    
    # Generate hash for the filename
    hashed_filename = await utils.get_file_hash(file)
    
    # Save file to disk
    file_path = os.path.join(config.UPLOAD_FOLDER, hashed_filename)
    
    # Only save if file doesn't exist
    if not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    
    # Send to model service for prediction
    prediction, score = await model_predict(hashed_filename)
    
    # Update response
    rpse["success"] = True
    rpse["prediction"] = prediction
    rpse["score"] = score
    rpse["image_file_name"] = hashed_filename

    return PredictResponse(**rpse)
