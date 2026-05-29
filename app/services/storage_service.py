from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """Simple storage service to upload/delete files to S3-compatible R2."""

    def __init__(self):
        self.enabled = bool(settings.R2_ENABLED)
        if self.enabled:
            try:
                import boto3

                self._client = boto3.client(
                    "s3",
                    endpoint_url=settings.R2_ENDPOINT_URL or None,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID or None,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY or None,
                    region_name=settings.R2_REGION or None,
                )
            except Exception as exc:  # pragma: no cover - runtime import
                logger.exception("Failed to initialize boto3 client: %s", exc)
                self.enabled = False
                self._client = None
        else:
            self._client = None

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Upload raw bytes to configured bucket and return a public URL or path.

        When R2 is disabled, raises RuntimeError.
        """
        if not self.enabled or not self._client:
            raise RuntimeError("R2 storage is not enabled or client not configured")

        bucket = settings.R2_BUCKET
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self._client.put_object(Bucket=bucket, Key=key, Body=data, **extra_args)

        # Build public URL
        if settings.R2_PUBLIC_URL:
            public = settings.R2_PUBLIC_URL.rstrip("/") + "/" + key
        else:
            # endpoint_url typically like https://<account>.r2.cloudflarestorage.com
            endpoint = settings.R2_ENDPOINT_URL.rstrip("/") if settings.R2_ENDPOINT_URL else ""
            public = f"{endpoint}/{bucket}/{key}" if endpoint else f"/{bucket}/{key}"

        return public

    def delete(self, key: str) -> bool:
        if not self.enabled or not self._client:
            # nothing to delete in R2
            return False
        bucket = settings.R2_BUCKET
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            logger.exception("Failed to delete object %s/%s", bucket, key)
            return False

    def key_from_url(self, url: str) -> Optional[str]:
        """Attempt to extract object key from a public URL returned by upload_bytes.

        Returns None if extraction fails.
        """
        if not url:
            return None
        # If public URL is configured and url starts with it, strip
        if settings.R2_PUBLIC_URL and url.startswith(settings.R2_PUBLIC_URL):
            return url[len(settings.R2_PUBLIC_URL.rstrip('/')) + 1 :].lstrip('/')

        # If endpoint + /bucket/ in URL
        endpoint = (settings.R2_ENDPOINT_URL or "").rstrip('/')
        bucket = settings.R2_BUCKET
        if endpoint and bucket and url.startswith(f"{endpoint}/{bucket}/"):
            return url.split(f"{endpoint}/{bucket}/", 1)[1]

        # As a last resort, try to find /{bucket}/ inside url
        marker = f"/{bucket}/"
        if marker in url:
            return url.split(marker, 1)[1]

        return None


# Singleton instance to reuse
storage_service = StorageService()
