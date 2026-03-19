"""snap3D — S3 Storage"""
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import uuid, os
from typing import Optional, BinaryIO
from app.core.config import settings

def _get_client():
    kwargs = dict(aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION, config=Config(signature_version="s3v4"))
    if settings.S3_ENDPOINT: kwargs["endpoint_url"] = settings.S3_ENDPOINT
    return boto3.client("s3", **kwargs)

def upload_file(file_obj: BinaryIO, key: str, content_type: str = "application/octet-stream") -> str:
    _get_client().upload_fileobj(file_obj, settings.S3_BUCKET, key, ExtraArgs={"ContentType": content_type})
    return key

def upload_bytes(data: bytes, key: str, content_type: str = "application/octet-stream") -> str:
    import io; return upload_file(io.BytesIO(data), key, content_type)

def generate_presigned_url(key: str, expires: int = 3600) -> str:
    if settings.CDN_BASE_URL: return f"{settings.CDN_BASE_URL}/{key}"
    return _get_client().generate_presigned_url("get_object", Params={"Bucket": settings.S3_BUCKET, "Key": key}, ExpiresIn=expires)

def delete_file(key: str):
    try: _get_client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
    except ClientError: pass

def make_image_key(id: int, tid: int, fname: str) -> str:
    ext = os.path.splitext(fname)[-1].lower() or ".jpg"
    return f"uploads/{id}/{tid}/{uuid.uuid4().hex}{ext}"

def make_model_key(id: int, tid: int, fmt: str) -> str:
    return f"models/{id}/{tid}/model.{fmt}"
