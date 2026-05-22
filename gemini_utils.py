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

# Create Cloud Storage Client
storage_client = storage.Client(project=os.getenv("PROJECT_ID"))

def prompt_rewriter(prompt: str = Form(...)):
    system_instruction = '''
                You are an artistic helmet designer as well as an expert prompt engineer, and are helping Formula E fans prompt Nano Banana on Agent Platform to create a design/motif of their choice for a Formula E helmet.
                Your Goal: To rewrite their existing prompt with a new, ready to use one that is suitable and will generate a high quality output from Imagen, that can then be used by a different software to create a net and to add branding overlay to.
                You will be sent a basic prompt such as "ocean waves" or "coconuts and palm trees".

                Key things to keep in mind:
                You are NOT prompting to generate a picture of a helmet with the fan's design - adapting this and sculpting it to fit a helmet net as another software's job- the rewritten prompt is just for a design/motif
                When rewriting the prompt, it needs to keep the core essentials of the original prompt and not try to be too clever - e.g. an initial prompt with coconuts & palm trees should not be rewritten as "a photorealistic background of cancun, mexico" (which happens to have palm trees & coconuts)
                IT MUST NOT CONTAIN A CAR or a car with that motif on it (the only acceptable use of a car is if the initial prompt is car related - e.g. taxis) - this prompt is just meant for artwork/motifs
                YOU MUST OUTPUT JUST the updated prompt, you must NOT output "that sounds like a great idea" and "this is my suggested option".
                Do not output anything that sounds self-aware such as "I'd love to help you with that, here's an option..."
                Don't say at the end, anything along the lines of "would you like me to try another one?
                YOU MUST ALSO BE CULTURALLY SENSITIVE AND IP SENSITIVE, to avoid causing unintended harm, so for instance if the original prompt is Japan - do not output anything containing the Rising Sun flag.
                '''

            print("DEBUG: Attempting prompt rewrite with Vertex AI...")
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=1.2,
                    max_output_tokens=2000,
                )
            )
        return {"rewritten_prompt": response.text,
                "original_prompt": prompt
            }

def generate_image(prompt: str = Form(...), original_prompt: str = Form("design")):
    try:
        urls = []
        for i in range(3):
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
                config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="1:1"),
                    )
                )
            
            generated_bytes = None
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        generated_bytes = part.inline_data.data
                        break
            
            if not generated_bytes:
                print(f"WARNING: Gemini did not successfully return motif for image {i+1}.")
                continue
                
            url = gcs_utils.upload_to_gcs(generated_bytes, content_type="image/png", original_prompt=original_prompt)
            urls.append(url)

        if not urls:
            raise HTTPException(status_code=500, detail="Gemini did not successfully return any motifs.")

        return {"urls": urls}

# To get a helmet image with just the forward facing angle
def helmet_editor(
    motif_url: str = Form(...),
    logo_path: str = Form(...),
    original_prompt: str = Form("design"),
    reference_path: str = Form("reference-images/formula-e-helmet-blank-helmet.png")
):
    """
    Edits your Nano Banana generated motif design and team logo with Gemini 3.1 Flash Image and uploads it to Cloud Storage.

    Args: 
      motif_url:  The URL of the generated motif
      logo_path:  The local path to the selected team logo
      reference_path: The path to the original image of a helmet to edit the motif onto
      original_prompt: The user's original theme/prompt
    """
    print(f"DEBUG: helmet_editor called with motif_url={motif_url}")

    helmet_editor_prompt = """
        Edit the provided helmet template (third image) by applying the motif (first image) 
        across its surface and placing the team logo (second image) on the upper forehead of the helmet. 
        Add a die cut if needed to the logo to make sure it is layered/fits in with the rest of the helmet design. 
        The design should wrap realistically around the helmet contours. 
        Output the finished helmet facing straight on a clean white background.
        Please keep the Formula E Google Cloud AI Helmet Designer logo from the template in the output.
        """

    motif_bytes = get_image_bytes(motif_url)
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
            
        image_url = gcs_utils.upload_to_gcs(generated_bytes, content_type="image/png", original_prompt=original_prompt)
        
        return {
            "status": "success",
            "image_url": image_url,
            "qr_code_base64": gcs_utils.generate_qr_base64(image_url)
        }

# To get a helmet image with multiple angles of the helmet
def multi_angle_helmet_editor(
    motif_url: str = Form(...),
    logo_path: str = Form(...),
    original_prompt: str = Form("design"),
    reference_path: str = Form("reference-images/formula-e-helmet-blank-helmet_multi_angle.png")
):
    """
    Edits your Nano Banana generated motif design and team logo with Gemini 3.1 Flash Image Preview onto 
    a multi angle helmet design and uploads it to Cloud Storage.
    """
    print(f"DEBUG: multi_angle_helmet_editor called")

    helmet_editor_prompt = """
        Edit the provided helmet template on all of it's angles (third image) by applying the motif (first image) 
        across its surface and placing the team logo (second image) on the upper forehead of the helmet (just above the visor but NOT ON the visor). 
        Add a die cut if needed to the logo to make sure it is layered/fits in with the rest of the helmet design. 
        The design should wrap realistically around the helmet contours. 
        Output the finished helmet angles on a clean white background with the straight angle in the middle,
        the left angle on the left side and the right angle on the right side. 
        DO NOT EDIT THE FORMULA E GOOGLE CLOUD LOGO on the jawlines and instead work around them. Don't change the color of the logos or the backgrounds.
        """

    try:
        motif_bytes = get_image_bytes(motif_url)
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
            
        image_url = gcs_utils.upload_to_gcs(generated_bytes, content_type="image/png", original_prompt=original_prompt)
        
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
    original_prompt: str = Form("design"),
    reference_path: str = Form("reference-images/blank-net-side-1.png")
):  
    """
    Takes a multi-angle helmet image generated by Gemini and maps it out onto a 3D net image.
    """ 
    print(f"DEBUG: net_generator called")

    prompt = """
    Take the multi-angle design of a custom Formula E helmet, 
    and apply it to a 2D net map using the template provided.

    Keep the design from the multi-angle image as much as possible, including the colors, motif, 
    and logos. The team logo (the other image) should be placed as per the label on the net template (which is in the forehead area). It should be taken exactly from the first image and 
    it should be upside down, as labeled in the helmet net image.
    The Formula E | Google Cloud logo should be on the jawline of either side of the helmet net.

    Preserve all elements from the net template including the cut lines, fold markers, 
    the color legend in the top right corner, and the numbering for folding/cutting.
    You can make the cut lines/fold markers and the numbering a bit less fuzzy and more clear if you need to.
    DO NOT ADD EXTRA ELEMENTS TO THE NET
    """

    try:
        # Keep higher quality (90) for the net motif to preserve detail
        image_bytes = get_image_bytes(image_url, quality=90)

        # Keep high quality (95) for the reference net template to ensure numbers are visible
        ref_bytes = get_image_bytes(reference_path, quality=95)


        try:
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
                        image_size="2K",
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
            
        net_image_url = gcs_utils.upload_to_gcs(generated_bytes, content_type="image/png", original_prompt=original_prompt)

        pdf_url = None
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
            tmp_img.write(generated_bytes)
            tmp_img_path = tmp_img.name
        
        try:
            # Use B1 format (720x1020mm) in Landscape
            pdf = FPDF(orientation='L', unit='mm', format=(720, 1020))
            pdf.add_page(orientation='L')
            # Maintain 16:9 aspect ratio of the generated image to avoid stretching.
            # With w=980 (leaving 20mm side margins), h is automatically calculated as ~551.25mm.
            # Center vertically: (720 - 551.25) / 2 = 84.375mm
            pdf.image(tmp_img_path, x=20, y=84.375, w=980)
            pdf_bytes = bytes(pdf.output())
            pdf_url = gcs_utils.upload_to_gcs(pdf_bytes, content_type="application/pdf", original_prompt=original_prompt)
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
        if path_or_bytes.startswith("gs://"):
            # Handle gs:// URI
            bucket_name = path_or_bytes.split("/")[2]
            blob_name = "/".join(path_or_bytes.split("/")[3:])
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            img_data = blob.download_as_bytes()
            img = PIL_Image.open(io.BytesIO(img_data))
            
        elif "storage.googleapis.com" in path_or_bytes:
            # Handle public GCS URL - extract bucket and blob
            # https://storage.googleapis.com/bucket-name/filename
            clean_url = path_or_bytes.replace("https://", "").replace("http://", "").replace("storage.googleapis.com/", "")
            parts = clean_url.split("/")
            bucket_name = parts[0]
            blob_name = "/".join(parts[1:])
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            img_data = blob.download_as_bytes()
            img = PIL_Image.open(io.BytesIO(img_data))

        elif path_or_bytes.startswith("http://") or path_or_bytes.startswith("https://"):
            resp = requests.get(path_or_bytes)
            resp.raise_for_status()
            img = PIL_Image.open(io.BytesIO(resp.content))

        else:
            # Assume it's a local file path
            # Try several possible locations for the asset
            clean_path = path_or_bytes.lstrip("/")
            # Remove redundant prefixes if they exist
            for prefix in ["../Frontend/public/", "Frontend/public/", "public/"]:
                if clean_path.startswith(prefix):
                    clean_path = clean_path[len(prefix):]
                    break

            possible_paths = [
                path_or_bytes,
                clean_path,
                os.path.join("../Frontend/public", clean_path),
                os.path.join("Frontend/public", clean_path),
                os.path.join("/app/Frontend/public", clean_path),
                os.path.join("Backend", clean_path)
            ]
            
            img = None
            tried_paths = []
            for p in possible_paths:
                if not p: continue
                tried_paths.append(p)
                if os.path.exists(p):
                    try:
                        img = PIL_Image.open(p)
                        print(f"DEBUG: Successfully loaded image from {p}")
                        break
                    except Exception as e:
                        print(f"DEBUG: Found file at {p} but failed to open: {e}")
            
            if img is None:
                raise FileNotFoundError(f"Could not find image. Tried: {', '.join(tried_paths)}")
    else:
        img = PIL_Image.open(io.BytesIO(path_or_bytes))
    
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    if max(img.size) > 2000:
        img.thumbnail((2000, 2000), PIL_Image.Resampling.LANCZOS)
        
    buf = io.BytesIO()
    img.save(buf, format=target_format, quality=quality)
    return buf.getvalue()

    except Exception as e:
        print(f"ERROR: Prompt rewriting failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
