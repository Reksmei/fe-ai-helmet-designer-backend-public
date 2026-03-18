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

# Initialize client for Vertex AI
client = genai.Client(
    vertexai=True, 
    project=os.getenv("PROJECT_ID"), 
    location=os.getenv("LOCATION")
)

# To get a helmet image with just the forward facing angle
def helmet_editor(
    motif_url: str = Form(...),
    logo_path: str = Form(...),
    reference_path: str = Form("../Frontend/public/reference-images/formula-e-helmet-blank-helmet.jpg")
):
    """
    Edits your Imagen generated motif design and team logo with Gemini 3.1 Flash Image and uploads it to Cloud Storage.

    Args: 
      motif_url:  The URL of the generated motif
      logo_path:  The local path to the selected team logo
      reference_path: The path to the original image of a helmet to edit the motif onto
    """
    print(f"DEBUG: helmet_editor called with motif_url={motif_url}")

    helmet_editor_prompt = """
        Edit the provided helmet template (third image) by applying the motif (first image) 
        across its surface and placing the team logo (second image) just above the visor on 
        the forehead of the helmet. The design should wrap realistically around the helmet contours. 
        Output the finished helmet facing straight on a clean white background.
        """

    try:
        if not os.path.exists(logo_path):
            raise HTTPException(status_code=400, detail=f"Logo not found: {logo_path}")

        motif_resp = requests.get(motif_url)
        motif_bytes = get_image_bytes(motif_resp.content)
        logo_bytes = get_image_bytes(logo_path)
        ref_bytes = get_image_bytes(reference_path)
        
        response = client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=[
            helmet_editor_prompt,
            types.Part.from_bytes(data=motif_bytes, mime_type="image/jpeg"),
            types.Part.from_bytes(data=logo_bytes, mime_type="image/jpeg"),
            types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
                ],
                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="4:3"),
                ),
            )
            
        generated_bytes = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    generated_bytes = part.inline_data.data
                    break
        
        if not generated_bytes:
            raise HTTPException(status_code=500, detail="Gemini did not return an image.")
            
        image_url = gcs_utils.upload_to_gcs(generated_bytes, content_type="image/png")
        
        return {
            "status": "success",
            "image_url": image_url,
            "qr_code_base64": gcs_utils.generate_qr_base64(image_url)
        }
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# To get a helmet image with multiple angles of the helmet
def multi_angle_helmet_editor(
    motif_url: str = Form(...),
    logo_path: str = Form(...),
    reference_path: str = Form("../Frontend/public/reference-images/hankook_formula-e-helmet-blank-helmet_multi_angle.png")
):
    """
    Edits your Imagen generated motif design and team logo with Gemini 3.1 Flash onto 
    a multi angle helmet design and uploads it to Cloud Storage.
    """
    print(f"DEBUG: multi_angle_helmet_editor called")

    helmet_editor_prompt = """
        Edit the provided helmet template on all of it's angles (third image) by applying the motif (first image) 
        across its surface and placing the team logo (second image) just above the visor on 
        the forehead of the helmet. The design should wrap realistically around the helmet contours. 
        Output the finished helmet angles on a clean white background with the straight angle in the middle,
        the left angle on the left side and the right angle on the right side. 
        Do not remove/edit the existing hankook logo on the sides, you can put the motif design below it but the logos need to be visible.
        """

    try:
        if not os.path.exists(logo_path):
            raise HTTPException(status_code=400, detail=f"Logo not found: {logo_path}")

        motif_resp = requests.get(motif_url)
        motif_bytes = get_image_bytes(motif_resp.content)
        logo_bytes = get_image_bytes(logo_path)
        ref_bytes = get_image_bytes(reference_path) # Compresses the 1.3MB PNG to JPEG
        
        response = client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=[
                helmet_editor_prompt,
                types.Part.from_bytes(data=motif_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=logo_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
                ],
                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config = types.ImageConfig(aspect_ratio="16:9"),
                ),
            )
            
        generated_bytes = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    generated_bytes = part.inline_data.data
                    break
        
        if not generated_bytes:
            raise HTTPException(status_code=500, detail="Gemini did not return an image.")
            
        image_url = gcs_utils.upload_to_gcs(generated_bytes, content_type="image/png")
        
        return {
            "status": "success",
            "image_url": image_url,
            "qr_code_base64": gcs_utils.generate_qr_base64(image_url)
        }
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# To edit the multi-angle helmet design onto a 2D net and convert the image to a pdf for printing
async def net_generator(
    image_url: str = Form(...), 
    reference_path: str = Form("../Frontend/public/reference-images/blank-net-side1.png")
):
    """
    Takes a multi-angle helmet image generated by Gemini and maps it out onto a 3D net image.
    """
    print(f"DEBUG: net_generator called")

    prompt = """
    Take the multi-angle design of a custom Formula E helmet (the first image), 
    and apply it to a 2D net map using the template provided (the second image).

    Keep the design from the multi-angle image as much as possible, including the colors, motif, 
    and logos. The team logo should be placed just above the helmet visor on the net template 
    and the Hankook logo should be on the jawline of either side of the helmet net.

    Preserve all elements from the net template including the cut lines, fold markers, 
    the color legend in the top right corner, and the numbering for folding/cutting.
    You can make the cut lines/fold markers and the numbering a bit less fuzzy and more clear if you need to.
    """

    try:
        image_resp = requests.get(image_url)
        # Keep higher quality (90) for the net motif to preserve detail
        image_bytes = get_image_bytes(image_resp.content, quality=90)

        if not os.path.exists(reference_path):
            raise HTTPException(status_code=400, detail=f"Net template not found: {reference_path}")

        # Keep high quality (95) for the reference net template to ensure numbers are visible
        ref_bytes = get_image_bytes(reference_path, quality=95)

        response = client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                types.Part.from_bytes(data=ref_bytes, mime_type="image/jpeg")
                ],
                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config = types.ImageConfig(
                        aspect_ratio="16:9",
                        image_size="2K"
                    ),
                ),
            )

        generated_bytes = None
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    generated_bytes = part.inline_data.data
                    break
        
        if not generated_bytes:
            raise HTTPException(status_code=500, detail="Gemini did not return an image.")
            
        net_image_url = gcs_utils.upload_to_gcs(generated_bytes, content_type="image/png")

        pdf_url = None
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            tmp_img.write(generated_bytes)
            tmp_img_path = tmp_img.name
        
        try:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_page(orientation='L')
            pdf.image(tmp_img_path, x=5, y=5, w=287, h=200)
            pdf_bytes = bytes(pdf.output())
            pdf_url = gcs_utils.upload_to_gcs(pdf_bytes, content_type="application/pdf")
        finally:
            if os.path.exists(tmp_img_path):
                os.remove(tmp_img_path)
        
        return {
            "status": "success",
            "net_image_url": net_image_url,
            "pdf_url": pdf_url,
        }
    except Exception as e:
        print(f"ERROR: Unexpected error in net_generator: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_image_bytes(path_or_bytes: any, target_format: str = "JPEG", quality: int = 85) -> bytes:
    if isinstance(path_or_bytes, str):
        img = PIL_Image.open(path_or_bytes)
    else:
        img = PIL_Image.open(io.BytesIO(path_or_bytes))
    
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    if max(img.size) > 2000:
        img.thumbnail((2000, 2000), PIL_Image.Resampling.LANCZOS)
        
    buf = io.BytesIO()
    img.save(buf, format=target_format, quality=quality)
    return buf.getvalue()

def prompt_rewriter(prompt: str = Form(...)):
    system_instruction = '''
                You are an artistic helmet designer as well as an expert prompt engineer, and are helping Formula E fans prompt Imagen 3 on Vertex AI to create a design/motif of their choice for a Formula E helmet.
                Your Goal: To rewrite their existing prompt with a new, ready to use one that is suitable and will generate a high quality output from Imagen, that can then be used by a different software to create a net and to add branding overlay to.
                You will be sent a basic prompt such as "ocean waves" or "coconuts and palm trees".

                Key things to keep in mind:
                You are NOT prompting to generate a picture of a helmet with the fan's design - adapting this and sculpting it to fit a helmet net as another software's job- the rewritten prompt is just for a design/motif
                When rewriting the prompt, it needs to keep the core essentials of the original prompt and not try to be too clever - e.g. an initial prompt with coconuts & palm trees should not be rewritten as "a photorealistic background of cancun, mexico" (which happens to have palm trees & coconuts)
                YOU MUST OUTPUT JUST the updated prompt, you must NOT output "that sounds like a great idea" and "this is my suggested option".
                Do not output anything that sounds self-aware such as "I'd love to help you with that, here's an option..."
                Don't say at the end, anything along the lines of "would you like me to try another one?
                '''
    try:
            print("DEBUG: Attempting prompt rewrite with Vertex AI...")
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=1.2,
                    max_output_tokens=2000,
                )
            )

        return {"rewritten_prompt": response.text}
    except Exception as e:
        print(f"ERROR: Prompt rewriting failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_image(prompt: str = Form(...)):
    try:
        response = client.models.generate_images(
            model='imagen-4.0-generate-001',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=3,
                include_rai_reason=True,
                output_mime_type='image/jpeg',
            )
        )
        
        urls = []
        for img in response.generated_images:
            image_bytes = getattr(img.image, 'image_bytes', None) or (img.image._as_bytes() if hasattr(img.image, '_as_bytes') else None)
            if image_bytes:
                url = gcs_utils.upload_to_gcs(image_bytes, content_type="image/jpeg")
                urls.append(url)
            
        return {"urls": urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
