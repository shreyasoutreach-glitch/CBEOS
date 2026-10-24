"""Document storage adapters.

Local storage is for synthetic-data sandbox use only. Production mode must use
an explicitly configured S3-compatible bucket and separately pass operational
approval/recovery gates. Keys are generated server-side and never accept paths.
"""
from __future__ import annotations

import os
from pathlib import Path


def _validate_key(key: str) -> str:
    key = str(key or "")
    if not key or key in {".", ".."} or "/" in key or "\\" in key or "\x00" in key:
        raise ValueError("Invalid storage object key")
    return key


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.root / _validate_key(key)).resolve()
        if path.parent != self.root:
            raise ValueError("Invalid storage object key")
        return path

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        path = self._path(key)
        with path.open("wb") as handle:
            handle.write(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            raise FileNotFoundError("Stored document not found") from None

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            pass


class S3Storage:
    def __init__(self, bucket: str, region: str = "", endpoint_url: str = "", client=None):
        if not bucket.strip():
            raise ValueError("S3 bucket is required")
        self.bucket = bucket.strip()
        if client is None:
            try:
                import boto3
            except ImportError as exc:
                raise RuntimeError("S3 storage requires boto3") from exc
            options = {}
            if region.strip():
                options["region_name"] = region.strip()
            if endpoint_url.strip():
                options["endpoint_url"] = endpoint_url.strip()
            client = boto3.client("s3", **options)
        self.client = client

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=_validate_key(key),
            Body=data,
            ContentType=content_type or "application/octet-stream",
            ServerSideEncryption="AES256",
        )

    def get(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=_validate_key(key))
        except Exception as exc:
            response_code = getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode")
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code")
            if response_code == 404 or error_code in {"NoSuchKey", "NotFound", "404"}:
                raise FileNotFoundError("Stored document not found") from None
            raise
        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=_validate_key(key))


_s3_clients = {}


def get_storage():
    """Resolve storage from configuration; production readiness is enforced elsewhere."""
    backend = os.getenv("CBAM_DOCUMENT_STORAGE_BACKEND", "local").strip().lower()
    if backend == "local":
        from . import db as dbm
        return LocalStorage(dbm.UP)
    if backend in {"s3", "object_storage"}:
        bucket = os.getenv("CBAM_OBJECT_STORAGE_BUCKET", "").strip()
        region = os.getenv("CBAM_OBJECT_STORAGE_REGION", "").strip()
        endpoint = os.getenv("CBAM_OBJECT_STORAGE_ENDPOINT_URL", "").strip()
        if not bucket:
            raise RuntimeError("Object storage bucket is not configured")
        key = (bucket, region, endpoint)
        if key not in _s3_clients:
            _s3_clients[key] = S3Storage(bucket=bucket, region=region, endpoint_url=endpoint)
        return _s3_clients[key]
    raise RuntimeError("Unsupported document storage backend")
