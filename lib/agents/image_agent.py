#!/usr/bin/env python3
"""
Image Agent for AI Image Generation

Generates images for social media using Google Imagen 4 with
prompt enhancement via Gemini Flash and SWIZZ voice persona styling.

Features:
- Social post graphics with platform-optimized aspect ratios
- Video/blog thumbnails
- Carousel multi-image generation
- Story/reel cover images
- Quote card / text overlay backgrounds
- Freeform AI art generation
- Two-model prompt enhancement pipeline (Gemini text -> Imagen image)
"""

import asyncio
from typing import Dict, Any, Optional, List

from lib.agents.base_agent import BaseAgent, AgentState
from lib.persona.swizz_persona import SwizzPersona
from lib.storage.database import EngagementDatabase


# Persona mode -> visual style hints for prompt enhancement
PERSONA_STYLE_MAP = {
    "professional": "corporate, clean, modern, professional color palette, polished",
    "personal": "vibrant, bold, energetic, street style, dynamic colors, expressive",
    "ceo": "authoritative, executive, data-driven, premium, sophisticated, dark tones",
}


class ImageAgent(BaseAgent):
    """
    Agent that generates images for social media content.

    Uses a two-model pipeline:
    1. Gemini Flash (text) to enhance user prompts into detailed Imagen prompts
    2. Imagen 3 to generate the actual images

    Persona mode influences the visual style of generated images.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        persona: Optional[SwizzPersona] = None,
        db: Optional[EngagementDatabase] = None,
        ai_provider: str = "gemini",
    ):
        """
        Initialize the image agent.

        Args:
            config: Agent configuration dictionary
            persona: SwizzPersona instance (optional, creates default)
            db: Database instance (optional, creates new if not provided)
            ai_provider: AI provider for text generation (prompt enhancement)
        """
        super().__init__(config, ai_provider, name="ImageAgent")

        self.persona = persona or SwizzPersona(
            mode=config.get('persona_mode', 'professional')
        )
        self.db = db or EngagementDatabase()

        self.default_platform = config.get('default_platform', 'instagram')

        # Lazy-init imagen client
        self._imagen_client = None

        self.logger.info(
            f"Configured: persona={self.persona._mode}, "
            f"platform={self.default_platform}"
        )

    @property
    def imagen_client(self):
        """Lazy-load ImagenClient."""
        if self._imagen_client is None:
            from lib.ai.imagen_client import ImagenClient
            self._imagen_client = ImagenClient()
        return self._imagen_client

    async def start(self):
        """Start the image processing loop."""
        self.transition(AgentState.MONITORING)
        self._running = True

        while self._running:
            try:
                if self._stop_event and self._stop_event.is_set():
                    break
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break

        self.transition(AgentState.STOPPING)

    async def stop(self):
        """Gracefully stop the agent."""
        self.logger.info("Stop requested")
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    async def process_item(self, item: Any) -> bool:
        """Process an image generation request."""
        try:
            action = item.get("action", "graphic")
            self.transition(AgentState.GENERATING)

            if action == "graphic":
                self.generate_post_graphic(
                    topic=item.get("topic", ""),
                    platform=item.get("platform", self.default_platform),
                    style=item.get("style", "modern"),
                    persona_mode=item.get("persona_mode", self.persona._mode),
                )
            elif action == "thumbnail":
                self.generate_thumbnail(
                    title=item.get("title", ""),
                    platform=item.get("platform", "youtube"),
                    style=item.get("style", "bold"),
                )

            self.stats['items_processed'] += 1
            self.transition(AgentState.MONITORING)
            return True

        except Exception as e:
            self.logger.error(f"Image generation failed: {e}")
            self.stats['errors'] += 1
            return False

    # ─────────────────────────────────────────────────────────────
    # PROMPT ENHANCEMENT
    # ─────────────────────────────────────────────────────────────

    def enhance_prompt(
        self,
        raw_prompt: str,
        platform: str = "instagram",
        style: str = "modern",
        persona_mode: str = "professional",
    ) -> str:
        """
        Enhance a user prompt into a detailed Imagen-optimized prompt.

        Uses Gemini Flash (text model) to refine the user's description
        into a detailed, visually-specific prompt. Persona mode influences
        the visual style.

        Args:
            raw_prompt: User's original image description
            platform: Target platform (affects composition guidance)
            style: Visual style (modern, minimal, bold, artistic, photorealistic, etc.)
            persona_mode: professional, personal, or ceo

        Returns:
            Enhanced prompt string ready for Imagen
        """
        persona_style = PERSONA_STYLE_MAP.get(persona_mode, PERSONA_STYLE_MAP["professional"])

        enhancement_prompt = (
            "You are an expert prompt engineer for AI image generation. "
            "Transform the user's idea into a detailed, visually-specific prompt "
            "for Google Imagen 3.\n\n"
            f"User idea: {raw_prompt}\n"
            f"Target platform: {platform}\n"
            f"Visual style: {style}\n"
            f"Brand mood: {persona_style}\n\n"
            "Requirements:\n"
            "- Be specific about composition, lighting, colors, and textures\n"
            "- Mention the art style (digital illustration, photography, flat design, etc.)\n"
            "- Include quality modifiers (high quality, detailed, professional)\n"
            "- Do NOT include text or words in the image description\n"
            "- Keep the prompt under 200 words\n\n"
            "Return ONLY the enhanced prompt text, nothing else."
        )

        try:
            enhanced = self.response_generator._generate(
                enhancement_prompt, max_length=1000
            )
            return enhanced.strip()
        except Exception as e:
            self.logger.warning(f"Prompt enhancement failed, using raw prompt: {e}")
            return raw_prompt

    # ─────────────────────────────────────────────────────────────
    # GENERATION METHODS
    # ─────────────────────────────────────────────────────────────

    def generate_post_graphic(
        self,
        topic: str,
        platform: str = "instagram",
        style: str = "modern",
        persona_mode: str = "professional",
        num_images: int = 1,
        upload: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a social post graphic.

        Args:
            topic: What the graphic should depict
            platform: Target platform (determines aspect ratio)
            style: Visual style
            persona_mode: professional, personal, or ceo
            num_images: Number of images (1-4)
            upload: Whether to upload to Late SDK

        Returns:
            Dict with image_urls/local_paths, prompt_used, platform, aspect_ratio
        """
        enhanced_prompt = self.enhance_prompt(topic, platform, style, persona_mode)

        if upload:
            urls = self.imagen_client.generate_and_upload(
                prompt=enhanced_prompt,
                platform=platform,
                image_type="post",
                num_images=num_images,
            )
            return {
                "image_urls": urls,
                "prompt_used": enhanced_prompt,
                "platform": platform,
                "aspect_ratio": self.imagen_client.get_preset(platform, "post") or "1:1",
                "uploaded": True,
            }
        else:
            results = self.imagen_client.generate_for_platform(
                prompt=enhanced_prompt,
                platform=platform,
                image_type="post",
                num_images=num_images,
            )
            return {
                "local_paths": [r["local_path"] for r in results],
                "prompt_used": enhanced_prompt,
                "platform": platform,
                "aspect_ratio": results[0]["aspect_ratio"] if results else "1:1",
                "uploaded": False,
            }

    def generate_thumbnail(
        self,
        title: str,
        platform: str = "youtube",
        style: str = "bold",
        num_images: int = 1,
        upload: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a video/blog thumbnail (16:9).

        Args:
            title: Video/blog title to inspire the thumbnail
            platform: Target platform
            style: Visual style
            num_images: Number of variants
            upload: Whether to upload to Late SDK

        Returns:
            Dict with image data
        """
        enhanced_prompt = self.enhance_prompt(
            f"Thumbnail for: {title}",
            platform=platform,
            style=style,
            persona_mode="professional",
        )

        if upload:
            urls = self.imagen_client.generate_and_upload(
                prompt=enhanced_prompt,
                platform=platform,
                image_type="thumbnail",
                num_images=num_images,
            )
            return {
                "image_urls": urls,
                "prompt_used": enhanced_prompt,
                "platform": platform,
                "aspect_ratio": "16:9",
                "uploaded": True,
            }
        else:
            results = self.imagen_client.generate_for_platform(
                prompt=enhanced_prompt,
                platform=platform,
                image_type="thumbnail",
                num_images=num_images,
            )
            return {
                "local_paths": [r["local_path"] for r in results],
                "prompt_used": enhanced_prompt,
                "platform": platform,
                "aspect_ratio": "16:9",
                "uploaded": False,
            }

    def generate_carousel_images(
        self,
        slides: List[str],
        platform: str = "instagram",
        style: str = "modern",
        persona_mode: str = "professional",
        upload: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate images for each carousel slide.

        Args:
            slides: List of slide descriptions
            platform: Target platform
            style: Visual style (consistent across slides)
            persona_mode: professional, personal, or ceo
            upload: Whether to upload to Late SDK

        Returns:
            Dict with slide_images list, prompt_used for each, platform
        """
        slide_results = []

        for i, slide_desc in enumerate(slides):
            enhanced = self.enhance_prompt(
                f"Carousel slide {i+1}/{len(slides)}: {slide_desc}. "
                f"Maintain consistent visual style across all slides.",
                platform=platform,
                style=style,
                persona_mode=persona_mode,
            )

            if upload:
                urls = self.imagen_client.generate_and_upload(
                    prompt=enhanced,
                    platform=platform,
                    image_type="post",
                    num_images=1,
                )
                slide_results.append({
                    "slide": i + 1,
                    "description": slide_desc,
                    "image_url": urls[0] if urls else None,
                    "prompt_used": enhanced,
                })
            else:
                results = self.imagen_client.generate_for_platform(
                    prompt=enhanced,
                    platform=platform,
                    image_type="post",
                    num_images=1,
                )
                slide_results.append({
                    "slide": i + 1,
                    "description": slide_desc,
                    "local_path": results[0]["local_path"] if results else None,
                    "prompt_used": enhanced,
                })

        return {
            "slide_images": slide_results,
            "slide_count": len(slides),
            "platform": platform,
            "style": style,
            "uploaded": upload,
        }

    def generate_story_image(
        self,
        context: str,
        platform: str = "instagram",
        persona_mode: str = "professional",
        upload: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a story/reel cover image (9:16).

        Args:
            context: What the story is about
            platform: Target platform
            persona_mode: professional, personal, or ceo
            upload: Whether to upload to Late SDK

        Returns:
            Dict with image data
        """
        enhanced_prompt = self.enhance_prompt(
            f"Story cover image: {context}",
            platform=platform,
            style="bold",
            persona_mode=persona_mode,
        )

        if upload:
            urls = self.imagen_client.generate_and_upload(
                prompt=enhanced_prompt,
                platform=platform,
                image_type="story",
                num_images=1,
            )
            return {
                "image_urls": urls,
                "prompt_used": enhanced_prompt,
                "platform": platform,
                "aspect_ratio": "9:16",
                "uploaded": True,
            }
        else:
            results = self.imagen_client.generate_for_platform(
                prompt=enhanced_prompt,
                platform=platform,
                image_type="story",
                num_images=1,
            )
            return {
                "local_paths": [r["local_path"] for r in results],
                "prompt_used": enhanced_prompt,
                "platform": platform,
                "aspect_ratio": "9:16",
                "uploaded": False,
            }

    def generate_text_overlay(
        self,
        text: str,
        background_style: str = "gradient",
        platform: str = "instagram",
        upload: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a background image for text overlay (quote cards, announcements).

        Note: Imagen generates the background only; text is added separately.

        Args:
            text: The text that will be overlaid (informs background design)
            background_style: gradient, solid, abstract, photo, minimal
            platform: Target platform
            upload: Whether to upload to Late SDK

        Returns:
            Dict with image data
        """
        enhanced_prompt = self.enhance_prompt(
            f"Background for a quote card / text overlay. "
            f"The text to overlay is: '{text}'. "
            f"Create a clean background with space for text, style: {background_style}. "
            f"Do NOT include any text or letters in the image.",
            platform=platform,
            style=background_style,
            persona_mode="professional",
        )

        if upload:
            urls = self.imagen_client.generate_and_upload(
                prompt=enhanced_prompt,
                platform=platform,
                image_type="post",
                num_images=1,
            )
            return {
                "image_urls": urls,
                "prompt_used": enhanced_prompt,
                "overlay_text": text,
                "platform": platform,
                "uploaded": True,
            }
        else:
            results = self.imagen_client.generate_for_platform(
                prompt=enhanced_prompt,
                platform=platform,
                image_type="post",
                num_images=1,
            )
            return {
                "local_paths": [r["local_path"] for r in results],
                "prompt_used": enhanced_prompt,
                "overlay_text": text,
                "platform": platform,
                "uploaded": False,
            }

    def generate_ai_art(
        self,
        description: str,
        style: str = "artistic",
        aspect_ratio: str = "1:1",
        num_images: int = 1,
        upload: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate freeform AI art (user provides the prompt directly).

        No platform-specific optimization; uses the user's description as-is
        with optional style enhancement.

        Args:
            description: Detailed image description
            style: Visual style
            aspect_ratio: Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)
            num_images: Number of images (1-4)
            upload: Whether to upload to Late SDK

        Returns:
            Dict with image data
        """
        enhanced_prompt = self.enhance_prompt(
            description, style=style, persona_mode="professional"
        )

        if upload:
            # Generate locally first, then upload
            results = self.imagen_client.generate_image(
                prompt=enhanced_prompt,
                aspect_ratio=aspect_ratio,
                num_images=num_images,
            )
            import os
            urls = []
            for r in results:
                try:
                    url = self.imagen_client._upload_to_late(r["local_path"])
                    urls.append(url)
                finally:
                    try:
                        os.unlink(r["local_path"])
                    except OSError:
                        pass

            return {
                "image_urls": urls,
                "prompt_used": enhanced_prompt,
                "aspect_ratio": aspect_ratio,
                "uploaded": True,
            }
        else:
            results = self.imagen_client.generate_image(
                prompt=enhanced_prompt,
                aspect_ratio=aspect_ratio,
                num_images=num_images,
            )
            return {
                "local_paths": [r["local_path"] for r in results],
                "prompt_used": enhanced_prompt,
                "aspect_ratio": aspect_ratio,
                "uploaded": False,
            }

    def list_presets(self) -> Dict[str, str]:
        """Return available platform presets."""
        from lib.ai.imagen_client import ImagenClient
        return dict(ImagenClient.PLATFORM_PRESETS)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="AI Image Generation Agent")
    parser.add_argument(
        '--action',
        choices=['graphic', 'thumbnail', 'carousel', 'story', 'overlay', 'art', 'presets', 'status'],
        default='status',
        help='Action to perform',
    )
    parser.add_argument('--prompt', type=str, help='Image description / prompt')
    parser.add_argument('--platform', type=str, default='instagram', help='Target platform')
    parser.add_argument('--style', type=str, default='modern',
                        help='Visual style (modern, minimal, bold, artistic, photorealistic, flat, gradient, neon)')
    parser.add_argument('--persona', type=str, default='professional',
                        choices=['professional', 'personal', 'ceo'],
                        help='Persona mode')
    parser.add_argument('--aspect-ratio', type=str, default='1:1',
                        help='Aspect ratio for art mode (1:1, 16:9, 9:16, 4:3, 3:4)')
    parser.add_argument('--num-images', type=int, default=1, help='Number of images (1-4)')
    parser.add_argument('--slides', type=str, nargs='+', help='Slide descriptions for carousel')
    parser.add_argument('--upload', action='store_true', help='Upload to Late SDK')
    parser.add_argument('--dry-run', action='store_true', help='Show enhanced prompt without generating')

    args = parser.parse_args()

    config = {
        'persona_mode': args.persona,
        'default_platform': args.platform,
    }

    agent = ImageAgent(config)

    if args.action == 'status':
        stats = agent.get_stats()
        print("\nImage Agent Status:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    elif args.action == 'presets':
        presets = agent.list_presets()
        print("\nAvailable platform presets:")
        for key, ratio in sorted(presets.items()):
            print(f"  {key}: {ratio}")

    elif args.action == 'graphic':
        if not args.prompt:
            print("[ERROR] --prompt required")
            return

        if args.dry_run:
            enhanced = agent.enhance_prompt(args.prompt, args.platform, args.style, args.persona)
            print(f"\n[DRY RUN] Enhanced prompt:\n{enhanced}")
            return

        print(f"\n[INFO] Generating post graphic for {args.platform}...\n")
        result = agent.generate_post_graphic(
            topic=args.prompt,
            platform=args.platform,
            style=args.style,
            persona_mode=args.persona,
            num_images=args.num_images,
            upload=args.upload,
        )
        _print_result(result)

    elif args.action == 'thumbnail':
        if not args.prompt:
            print("[ERROR] --prompt required (video/blog title)")
            return

        if args.dry_run:
            enhanced = agent.enhance_prompt(f"Thumbnail for: {args.prompt}", args.platform, args.style, "professional")
            print(f"\n[DRY RUN] Enhanced prompt:\n{enhanced}")
            return

        print(f"\n[INFO] Generating thumbnail for {args.platform}...\n")
        result = agent.generate_thumbnail(
            title=args.prompt,
            platform=args.platform,
            style=args.style,
            num_images=args.num_images,
            upload=args.upload,
        )
        _print_result(result)

    elif args.action == 'carousel':
        slides = args.slides or [args.prompt or "Slide content"]
        if args.dry_run:
            for i, slide in enumerate(slides):
                enhanced = agent.enhance_prompt(
                    f"Carousel slide {i+1}/{len(slides)}: {slide}",
                    args.platform, args.style, args.persona
                )
                print(f"\n[DRY RUN] Slide {i+1} prompt:\n{enhanced}")
            return

        print(f"\n[INFO] Generating {len(slides)}-slide carousel...\n")
        result = agent.generate_carousel_images(
            slides=slides,
            platform=args.platform,
            style=args.style,
            persona_mode=args.persona,
            upload=args.upload,
        )
        _print_result(result)

    elif args.action == 'story':
        if not args.prompt:
            print("[ERROR] --prompt required")
            return

        if args.dry_run:
            enhanced = agent.enhance_prompt(f"Story cover image: {args.prompt}", args.platform, "bold", args.persona)
            print(f"\n[DRY RUN] Enhanced prompt:\n{enhanced}")
            return

        print(f"\n[INFO] Generating story image...\n")
        result = agent.generate_story_image(
            context=args.prompt,
            platform=args.platform,
            persona_mode=args.persona,
            upload=args.upload,
        )
        _print_result(result)

    elif args.action == 'overlay':
        if not args.prompt:
            print("[ERROR] --prompt required (text to overlay)")
            return

        if args.dry_run:
            enhanced = agent.enhance_prompt(
                f"Background for text overlay: '{args.prompt}'",
                args.platform, args.style, "professional"
            )
            print(f"\n[DRY RUN] Enhanced prompt:\n{enhanced}")
            return

        print(f"\n[INFO] Generating text overlay background...\n")
        result = agent.generate_text_overlay(
            text=args.prompt,
            background_style=args.style,
            platform=args.platform,
            upload=args.upload,
        )
        _print_result(result)

    elif args.action == 'art':
        if not args.prompt:
            print("[ERROR] --prompt required")
            return

        if args.dry_run:
            enhanced = agent.enhance_prompt(args.prompt, style=args.style, persona_mode="professional")
            print(f"\n[DRY RUN] Enhanced prompt:\n{enhanced}")
            return

        print(f"\n[INFO] Generating AI art...\n")
        result = agent.generate_ai_art(
            description=args.prompt,
            style=args.style,
            aspect_ratio=args.aspect_ratio,
            num_images=args.num_images,
            upload=args.upload,
        )
        _print_result(result)


def _print_result(result: Dict[str, Any]):
    """Print generation result."""
    import json
    print(json.dumps(
        {k: v for k, v in result.items() if k != "image_bytes"},
        indent=2, default=str,
    ))


if __name__ == "__main__":
    main()
