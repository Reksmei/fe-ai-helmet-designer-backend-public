# Copyright 2026 Reksmei Arkadiusz-Davidavic

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://apache.org

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from fastapi import Form, HTTPException
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
import qrcode
import requests
import urllib.request
from PIL import Image as PIL_Image
from fpdf import FPDF
import gcs_utils

load_dotenv()

# Initialize client for Agent Platform
aclient = genai.Client(
    enterprise=True, 
    project=os.getenv("PROJECT_ID"), 
    location=os.getenv("LOCATION")
).aio

async def helmet_animator(image_url: str = Form(...)):
    """
    Generates a video of the helmet spinning using Veo and uploads it to GCS
    """
    VIDEO_ANIMATOR_PROMPT = """
      Cinematic 3D product ad of a Formula E helmet suspended in mid-air. 
      The camera performs a single, seamless 360-degree orbital rotation around 
      the helmet in a constant clockwise direction. 
      The motion starts at the front, moves to the side, back, other side, 
      and returns to the front without ever changing direction or reversing. 
      High-end studio lighting with realistic HDR reflections on the visor. 
      The background should be dark blue and should remain constant.
      Smooth, consistent camera velocity, no easing at the loop point.
"""

    try:
        prompt = VIDEO_ANIMATOR_PROMPT
        filename = image_url.split('/')[-1]
        bucket_name = "helmet-images-output"
        gs_uri = f"gs://{bucket_name}/{filename}"

        operation = aclient.models.generate_videos(
            model='veo-3.1-generate-001',
            prompt=prompt,
            config=types.GenerateVideosConfig(
                reference_images=[types.VideoGenerationReferenceImage(
                    image=types.Image(gcs_uri=gs_uri, mime_type="image/png"),
                    reference_type="asset",
                )],
                number_of_videos=1,
                duration_seconds=8,
                generate_audio=False
            )
        )
        
        while not operation.done:
            time.sleep(30)
            operation = client.operations.get(operation)
            
        if operation.error:
            raise Exception(f"Video generation failed: {operation.error}")

        if operation.response:
            video_data = operation.result.generated_videos[0].video.video_bytes
            video_url = gcs_utils.upload_video_to_gcs(video_data, content_type="video/mp4")
            return {
                "status": "success",
                "video_url": video_url,
                "qr_code_base64": gcs_utils.generate_qr_base64(video_url)
            }
        else:
            raise Exception("No video generated")
    except Exception as e:
        print(f"Error in helmet_animator: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
