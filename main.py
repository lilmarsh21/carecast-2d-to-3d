from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import os
import shutil
import uuid
import traceback

from midas_infer import load_midas_model, predict_depth
from mesh_builder import merge_and_save_point_clouds

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "static/models"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://doc.carecast.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Service is running"}

@app.post("/generate-3d/")
async def generate_3d(xrays: List[UploadFile] = File(...)):
    try:
        print("✅ /generate-3d/ hit")

        if not 1 <= len(xrays) <= 20:
            raise HTTPException(status_code=400, detail="Upload between 1 and 20 X-rays.")

        filepaths = []
        for file in xrays:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in [".jpg", ".jpeg", ".png"]:
                raise HTTPException(status_code=400, detail="Only .jpg, .jpeg, .png allowed.")

            save_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
            with open(save_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            filepaths.append(save_path)

        print("📦 Loading model...")
        midas, transform = load_midas_model()
        print("✅ Model loaded.")

        depth_maps = [predict_depth(fp, midas, transform) for fp in filepaths]

        model_id = str(uuid.uuid4())
        output_path = os.path.join(OUTPUT_DIR, f"{model_id}.glb")
        merge_and_save_point_clouds(depth_maps, output_path)

        print("✅ 3D model saved.")
        return JSONResponse({
            "message": "3D model generated.",
            "model_url": f"/static/models/{model_id}.glb"
        })

    except Exception as e:
        print("🔥 CRASHED DURING /generate-3d/")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

app.mount("/static", StaticFiles(directory="static"), name="static")
