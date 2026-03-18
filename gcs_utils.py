import os
import io
import uuid
import base64
from google.cloud import storage
import qrcode

# Create Cloud Storage Client
storage_client = storage.Client(project=os.getenv("PROJECT_ID"))

def upload_to_gcs(data: bytes, content_type: str = "image/png") -> str:
    """
    Uploads generated images and pdfs to Cloud Storage with unique name and returns public URL
    """
    uid = uuid.uuid4()
    
    if "pdf" in content_type:
        ext = "pdf"
        bucket_name = "helmet_nets_output"
        filename = f"helmet_net_{uid}.{ext}"
    elif "jpeg" in content_type or "jpg" in content_type:
        ext = "jpg"
        bucket_name = "helmet-images-output"
        filename = f"helmet_image_{uid}.{ext}"
    else:
        ext = "png"
        bucket_name = "helmet-images-output"
        filename = f"helmet_image_{uid}.{ext}"

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_string(data, content_type=content_type)
    return f"https://storage.googleapis.com/{bucket_name}/{filename}"

def upload_video_to_gcs(video_data: bytes, content_type: str = "video/mp4") -> str:
    """
    Uploads generated videos to Cloud Storage with unique name and returns public URL
    """
    bucket_name = "helmet_animation_output"
    bucket = storage_client.bucket(bucket_name)
    filename = f"helmet_animation_{uuid.uuid4()}.mp4"
    blob = bucket.blob(filename)
    blob.upload_from_string(video_data, content_type=content_type)
    return f"https://storage.googleapis.com/{bucket_name}/{filename}"

def generate_qr_base64(url: str) -> str:
    """
    Generates a QR code for a URL and returns it as a base64 string.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode('utf-8')
