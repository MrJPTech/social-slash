#!/usr/bin/env python3
"""
Imagen AI Client for Image Generation

Uses Google's Imagen 4 model via the google-genai SDK for:
- Social media post graphics
- Platform-optimized image generation with aspect ratio presets
- Temp file management and Late SDK upload integration
"""

import os
import tempfile
from typing import Dict, List, Optional, Any

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class ImagenClient:
    """
    Imagen AI client for social media image generation.

    Uses Imagen 4 via the google-genai SDK (same API key as GeminiClient).
    """

    MODEL = "imagen-4.0-generate-001"

    # Platform + image type -> aspect ratio presets
    PLATFORM_PRESETS: Dict[str, str] = {
        # Instagram
        "instagram_post": "1:1",
        "instagram_story": "9:16",
        "instagram_reel": "9:16",
        # Twitter / X
        "twitter_post": "16:9",
        "twitter_header": "16:9",
        # LinkedIn
        "linkedin_post": "4:3",
        "linkedin_banner": "16:9",
        # YouTube
        "youtube_thumbnail": "16:9",
        "youtube_banner": "16:9",
        # TikTok
        "tiktok_cover": "9:16",
        "tiktok_post": "9:16",
        # Facebook
        "facebook_post": "4:3",
        "facebook_story": "9:16",
        "facebook_cover": "16:9",
        # Pinterest
        "pinterest_pin": "3:4",
        # Threads
        "threads_post": "1:1",
        # Reddit
        "reddit_post": "16:9",
        # Google Business
        "googlebusiness_post": "4:3",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Imagen client.

        Args:
            api_key: Google API key. Defaults to GOOGLE_API_KEY env var.
        """
        if not GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package not installed. "
                "Run: pip install google-genai"
            )

        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')

        if not self.api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.client = genai.Client(api_key=self.api_key)

    @classmethod
    def get_preset(cls, platform: str, image_type: str = "post") -> Optional[str]:
        """
        Look up an aspect ratio preset for a platform and image type.

        Args:
            platform: Platform name (instagram, twitter, etc.)
            image_type: Image type (post, story, cover, etc.)

        Returns:
            Aspect ratio string (e.g. "1:1") or None if no preset found
        """
        key = f"{platform.lower()}_{image_type.lower()}"
        return cls.PLATFORM_PRESETS.get(key)

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        num_images: int = 1,
        safety_filter: str = "BLOCK_LOW_AND_ABOVE",
    ) -> List[Dict[str, Any]]:
        """
        Generate images from a text prompt.

        Args:
            prompt: Text description of the image to generate
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            num_images: Number of images to generate (1-4)
            safety_filter: Safety filter level

        Returns:
            List of dicts with 'image_bytes' and 'local_path' keys
        """
        num_images = max(1, min(4, num_images))

        config = types.GenerateImagesConfig(
            number_of_images=num_images,
            aspect_ratio=aspect_ratio,
            safety_filter_level=safety_filter,
            person_generation="ALLOW_ADULT",
        )

        try:
            response = self.client.models.generate_images(
                model=self.MODEL,
                prompt=prompt,
                config=config,
            )
        except Exception as e:
            print(f"[ERROR] Imagen generation failed: {e}")
            raise

        results = []
        for img in response.generated_images:
            image_bytes = img.image.image_bytes
            local_path = self._save_to_temp(image_bytes)
            results.append({
                "image_bytes": image_bytes,
                "local_path": local_path,
            })

        print(f"[SUCCESS] Generated {len(results)} image(s)")
        return results

    def generate_for_platform(
        self,
        prompt: str,
        platform: str,
        image_type: str = "post",
        num_images: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Generate images optimized for a specific platform.

        Resolves platform + image_type to an aspect ratio preset,
        then delegates to generate_image().

        Args:
            prompt: Text description
            platform: Target platform (instagram, twitter, linkedin, etc.)
            image_type: Image type (post, story, cover, thumbnail, etc.)
            num_images: Number of images (1-4)

        Returns:
            List of dicts with image_bytes, local_path, aspect_ratio
        """
        aspect_ratio = self.get_preset(platform, image_type) or "1:1"

        results = self.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            num_images=num_images,
        )

        for r in results:
            r["aspect_ratio"] = aspect_ratio
            r["platform"] = platform
            r["image_type"] = image_type

        return results

    def generate_and_upload(
        self,
        prompt: str,
        platform: str,
        image_type: str = "post",
        num_images: int = 1,
    ) -> List[str]:
        """
        Generate images and upload them via Late SDK.

        End-to-end: generate -> save temp -> upload -> cleanup -> return URLs.

        Args:
            prompt: Text description
            platform: Target platform
            image_type: Image type
            num_images: Number of images (1-4)

        Returns:
            List of cloud media URLs
        """
        results = self.generate_for_platform(
            prompt=prompt,
            platform=platform,
            image_type=image_type,
            num_images=num_images,
        )

        urls = []
        for r in results:
            try:
                url = self._upload_to_late(r["local_path"])
                urls.append(url)
            finally:
                # Clean up temp file
                try:
                    os.unlink(r["local_path"])
                except OSError:
                    pass

        print(f"[SUCCESS] Uploaded {len(urls)} image(s) to Late")
        return urls

    def _save_to_temp(self, image_bytes: bytes) -> str:
        """
        Save image bytes to a temporary PNG file.

        Args:
            image_bytes: Raw image bytes

        Returns:
            Path to the temp file
        """
        tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        tmp.write(image_bytes)
        tmp.close()
        return tmp.name

    def _upload_to_late(self, local_path: str) -> str:
        """
        Upload a local image file to Late SDK media hosting.

        Args:
            local_path: Path to the local image file

        Returns:
            Cloud URL for the uploaded media
        """
        from late import Late

        api_key = os.getenv("LATE_API_KEY", "")
        if not api_key:
            raise ValueError("LATE_API_KEY required for media upload")

        client = Late(api_key=api_key)
        response = client.media.upload(local_path)
        return response.url


# Example usage
if __name__ == "__main__":
    client = ImagenClient()

    # List available presets
    print("Platform presets:")
    for key, ratio in sorted(ImagenClient.PLATFORM_PRESETS.items()):
        print(f"  {key}: {ratio}")

    # Test generation
    result = client.generate_image(
        prompt="Modern tech startup workspace with clean minimal design",
        aspect_ratio="1:1",
        num_images=1,
    )
    print(f"\nGenerated {len(result)} image(s)")
    for r in result:
        print(f"  Saved to: {r['local_path']}")
