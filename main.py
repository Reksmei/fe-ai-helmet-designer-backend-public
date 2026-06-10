import os
import io
import uuid
import base64
import time
import tempfile
from typing import Optional, List
from google import genai
from google.genai import types
from google.cloud import storage
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import qrcode
import requests
import urllib.request
import gemini_utils
import veo_utils
from PIL import Image as PIL_Image
from fpdf import FPDF
import asyncio


load_dotenv()

# Initialize FastAPI
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/prompt_rewriter")
def fastapi_prompt_rewriter(prompt: str = Form(...)):
    # prompt_rewriter function with gemini_utils.py to rewrite prompt for Imagen 
    return gemini_utils.prompt_rewriter(prompt=prompt)


@app.post("/generate_image")
def fastapi_generate_image(prompt: str = Form(...)):
    return gemini_utils.generate_image(prompt=prompt)

@app.post("/helmet_editor")
def fastapi_helmet_editor(motif_url: str = Form(...),
    logo_path: str = Form(...),
    reference_path: str = Form("../Frontend/public/reference-images/formula-e-helmet-blank-helmet.jpg")):
    # Call helmet_editor function with gemini_utils.py to generate helmet with single, center angle
    return gemini_utils.helmet_editor(motif_url=motif_url, logo_path=logo_path, reference_path=reference_path)
    
@app.post("/multi_angle_helmet_editor")
def fastapi_multi_angle_helmet_editor(
    motif_url: str = Form(...),
    logo_path: str = Form(...),
    reference_path: str = Form("../Frontend/public/reference-images/hankook_formula-e-helmet-blank-helmet_multi_angle.png")
):
    # Call multi_angle_helmet_editor function with gemini_utils.py to generate helmet with left, center and right angles
    return gemini_utils.multi_angle_helmet_editor(motif_url=motif_url, logo_path=logo_path, reference_path=reference_path)
    
@app.post("/helmet_animator")
async def fastapi_helmet_animator(image_url: str = Form(...)):
    # Call helmet_animator function with veo_utils.py to generate rotating helmet video
    return await veo_utils.helmet_animator(image_url=image_url)

@app.post("/net_generator")
def fastapi_net_generator(
    image_url: str = Form(...), 
    reference_path: str = Form("../Frontend/public/reference-images/blank-net-side1.png")
):
    # Call net_generator function with gemini_utils.py to generate net image and pdf
    return gemini_utils.net_generator(image_url=image_url, reference_path=reference_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
