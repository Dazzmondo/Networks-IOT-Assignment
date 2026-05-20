"""
Purpose:
    Uploads detection images to Cloudinary and returns a public URL.

Why Cloudinary?
    Cloudinary makes captured images accessible from anywhere, not just the local Pi.  
    This means dog-detection images can be viewed remotely (e.g. in the
    Flask dashboard on Render, or in the MQTT payload).

Graceful degradation:
    If Cloudinary credentials are not set in .env, the service is
    disabled and returns None for every upload.  The rest of the system
    continues to work with local file paths only.

Dependencies:
    pip install cloudinary
"""

import cloudinary
import cloudinary.uploader

from config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_FOLDER,
)
from logger_service import logger


class CloudinaryService:
    """
    Wraps Cloudinary image upload.

    Upload is triggered only for dog detections (the cases where the
    system saves an archived image to disk).

    Usage:
        cloud = CloudinaryService()
        url   = cloud.upload("/path/to/dog_20250115.jpg", "dog_20250115")
        # url → "https://res.cloudinary.com/..." or None
    """

    def __init__(self):
        # Checks all credentials are present before enabling the service.
        # This catches partial configuration early at startup.
        self._enabled = all([
            CLOUDINARY_CLOUD_NAME,
            CLOUDINARY_API_KEY,
            CLOUDINARY_API_SECRET,
        ])    

        if self._enabled:
            cloudinary.config(
                cloud_name = CLOUDINARY_CLOUD_NAME,
                api_key    = CLOUDINARY_API_KEY,
                api_secret = CLOUDINARY_API_SECRET,
            )
            logger.info("Cloudinary image upload enabled.")
        else:
            logger.info(
                "Cloudinary credentials not set — image upload disabled. "
                "Detection images will be saved locally only."
            )

    def upload(self, image_path: str, public_id: str | None = None) -> str | None:
        """
        Upload an image to Cloudinary.

        Follows the upload_cloudinary.py pattern from the smart-doorbell lab:
            result = cloudinary.uploader.upload(image_path, ...)
            url    = result["secure_url"]

        Args:
            image_path: local path to the JPEG to upload.
            public_id:  optional stable ID (if None, Cloudinary auto-generates one).

        Returns:
            Public HTTPS URL string, or None if upload is disabled or fails.
        """
        if not self._enabled:
            return None

        try:
            result = cloudinary.uploader.upload(
                image_path,
                folder     = CLOUDINARY_FOLDER,
                public_id  = public_id,
                overwrite  = True,   # replace same public_id each time
                invalidate = True,   # clear CDN cache on overwrite
            )
            url = result["secure_url"]
            logger.info(f"Cloudinary upload → {url}")
            return url
        except Exception as error:
            logger.error(f"Cloudinary upload failed: {error}")
            return None
