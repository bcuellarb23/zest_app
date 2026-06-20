import boto3
import os
from botocore.config import Config 

# R2 Confiduration
R2_CONFIG = {
    'account_id': os.environ.get('R2_ACCOUNT_ID'),
    'access_key': os.environ.get('R2_ACCESS_KEY'),
    'secret_access_key': os.environ.get('R2_SECRET_ACCESS_KEY'),
    'bucket_name': os.environ.get('R2_BUCKET_NAME'),
    'public_base_url': os.environ.get('R2_PUBLIC_BASE_URL')
}

s3 = boto3.client(
    service_name = "s3", 
    endpoint_url = f"https://{R2_CONFIG['account_id']}.r2.cloudflarestorage.com",
    aws_access_key_id = R2_CONFIG['access_key'],
    aws_secret_access_key = R2_CONFIG['secret_access_key'],
    config = Config(signature_version = "s3v4"),
)

def upload_profile_picture(file_obj, user_id):
    
    """ 
    This function is conected to cloudflare 
    it manages images in the app
    """

    import io
    from PIL import Image

    img = Image.open(file_obj)
    img = img.convert("RGB")
    img.thumbnail((256, 256))

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality = 80)
    buffer.seek(0)

    key = f"avatars/user_{user_id}.jpg"
    s3.upload_fileobj(
        buffer,
        R2_CONFIG['bucket_name'],
        key,
        ExtraArgs={"ContentType": "image/jpeg"}
    )

    return f"{R2_CONFIG['public_base_url']}/{key}"
