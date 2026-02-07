#!/usr/bin/env python3
"""
Media Agent for Content Captioning and Formatting

Generates captions, alt text, and formatting for media content
in the SWIZZ voice persona. Handles reels, posts, stories, and carousels.

Features:
- Reel/post/story caption generation
- Carousel multi-slide captions
- Alt text generation (accessible, professional)
- Media format suggestions
- Dual-persona voice support
"""

import asyncio
from typing import Dict, Any, Optional, List

from lib.agents.base_agent import BaseAgent, AgentState
from lib.persona.swizz_persona import SwizzPersona
from lib.storage.database import EngagementDatabase


class MediaAgent(BaseAgent):
    """
    Agent that generates captions and text for media content.

    Takes media descriptions and produces platform-ready captions,
    alt text, and formatting using the SWIZZ voice persona.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        persona: Optional[SwizzPersona] = None,
        db: Optional[EngagementDatabase] = None,
        ai_provider: str = "gemini"
    ):
        """
        Initialize the media agent.

        Args:
            config: Agent configuration dictionary
            persona: SwizzPersona instance (optional, creates default)
            db: Database instance (optional, creates new if not provided)
            ai_provider: AI provider for generation
        """
        super().__init__(config, ai_provider, name="MediaAgent")

        self.persona = persona or SwizzPersona(
            mode=config.get('persona_mode', 'professional')
        )
        self.db = db or EngagementDatabase()

        self.default_platform = config.get('default_platform', 'instagram')
        self.poll_interval = config.get('poll_interval_seconds', 30)

        # Media processing queue
        self._media_queue: asyncio.Queue = asyncio.Queue()

        self.logger.info(
            f"Configured: persona={self.persona._mode}, "
            f"platform={self.default_platform}"
        )

    async def start(self):
        """Start the media processing loop."""
        self.transition(AgentState.MONITORING)
        self._running = True

        while self._running:
            try:
                try:
                    item = self._media_queue.get_nowait()
                    await self.process_item(item)
                except asyncio.QueueEmpty:
                    pass

                if self._stop_event and self._stop_event.is_set():
                    break

                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats['errors'] += 1
                self.transition(AgentState.ERROR)
                self.logger.error(f"Media processing error: {e}")
                await asyncio.sleep(self.poll_interval * 2)
                self.transition(AgentState.MONITORING)

        self.transition(AgentState.STOPPING)

    async def stop(self):
        """Gracefully stop the agent."""
        self.logger.info("Stop requested")
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    async def process_item(self, media_data: Dict[str, Any]) -> bool:
        """
        Process a media captioning request.

        Args:
            media_data: Dict with description, media_type, platform, context

        Returns:
            True if processed successfully
        """
        try:
            description = media_data.get('description', '')
            media_type = media_data.get('media_type', 'post')
            platform = media_data.get('platform', self.default_platform)
            persona_mode = media_data.get('persona_mode', self.persona._mode)

            self.log_item('media', platform, 'self', description[:50])
            self.transition(AgentState.GENERATING)

            if media_type == 'carousel':
                slides = media_data.get('slides', [description])
                result = self.generate_carousel_captions(slides, platform, persona_mode)
            elif media_type == 'story':
                context = media_data.get('context', '')
                result = {'text': self.generate_story_text(context, media_type, persona_mode)}
            elif media_type == 'reel':
                context = media_data.get('context', '')
                result = {'caption': self.generate_reel_caption(description, context, persona_mode)}
            else:
                result = {'caption': self.generate_reel_caption(description, '', persona_mode)}

            self.stats['items_processed'] += 1
            self.format_console_output('success', f"Generated {media_type} caption for {platform}")
            self.transition(AgentState.MONITORING)
            return True

        except Exception as e:
            self.logger.error(f"Media processing failed: {e}")
            self.stats['errors'] += 1
            return False

    def generate_reel_caption(
        self,
        description: str,
        context: str = "",
        persona_mode: str = "professional",
    ) -> str:
        """
        Generate a short, punchy reel/post caption.

        Args:
            description: Description of the media content
            context: Additional context
            persona_mode: Voice mode

        Returns:
            Caption text
        """
        if persona_mode != self.persona._mode:
            self.persona.set_mode(persona_mode)

        active = self.persona.get_active_persona()
        platform_config = self.persona.get_platform_config('reels')
        max_chars = platform_config.get('max_chars', 2200)

        system_prompt = active.get_system_prompt("casual")
        length_guide = active.get_response_length_guide("casual")

        context_text = f"\nContext: {context}" if context else ""

        prompt = (
            f"{system_prompt}\n\n"
            f"Write a caption for this reel/post.\n"
            f"Media: {description}{context_text}\n"
            f"Target length: {length_guide[0]}-{length_guide[1]} words\n"
            f"Make it punchy and engaging. Can include relevant emojis.\n"
            f"Return ONLY the caption text."
        )

        raw = self.response_generator._generate(prompt, max_length=max_chars)
        caption = active.apply_vocab_transform(raw)

        if len(caption) > max_chars:
            caption = caption[:max_chars - 3].rsplit(' ', 1)[0] + "..."

        return caption

    def generate_story_text(
        self,
        context: str,
        media_type: str = "story",
        persona_mode: str = "professional",
    ) -> str:
        """
        Generate story overlay text (ultra-minimal per persona style).

        Args:
            context: What the story is about
            media_type: Type of story content
            persona_mode: Voice mode

        Returns:
            Story text (very short)
        """
        if persona_mode != self.persona._mode:
            self.persona.set_mode(persona_mode)

        active = self.persona.get_active_persona()
        system_prompt = active.get_system_prompt("casual")

        prompt = (
            f"{system_prompt}\n\n"
            f"Write text overlay for an Instagram story.\n"
            f"Context: {context}\n"
            f"MUST be ultra-short (1-5 words max). Stories are visual-first.\n"
            f"Can be just emojis or emojis + 1-3 words.\n"
            f"Return ONLY the text overlay."
        )

        raw = self.response_generator._generate(prompt, max_length=100)
        return active.apply_vocab_transform(raw).strip()

    def generate_carousel_captions(
        self,
        slides_descriptions: List[str],
        platform: str = "instagram",
        persona_mode: str = "professional",
    ) -> Dict[str, Any]:
        """
        Generate captions for a multi-slide carousel.

        Args:
            slides_descriptions: Description of each slide
            platform: Target platform
            persona_mode: Voice mode

        Returns:
            Dict with main_caption and slide_texts
        """
        if persona_mode != self.persona._mode:
            self.persona.set_mode(persona_mode)

        active = self.persona.get_active_persona()
        platform_config = self.persona.get_platform_config(platform)
        max_chars = platform_config.get('max_chars', 2200)

        system_prompt = active.get_system_prompt("business")
        slides_text = "\n".join(
            f"Slide {i+1}: {desc}" for i, desc in enumerate(slides_descriptions)
        )

        prompt = (
            f"{system_prompt}\n\n"
            f"Write captions for a {len(slides_descriptions)}-slide carousel post.\n\n"
            f"{slides_text}\n\n"
            f"Provide:\n"
            f"1. Main post caption (under {max_chars} chars)\n"
            f"2. Text for each slide (1-2 lines each, if needed)\n\n"
            f"Keep it engaging. SWIZZ voice. Return formatted clearly."
        )

        raw = self.response_generator._generate(prompt, max_length=max_chars * 2)
        content = active.apply_vocab_transform(raw)

        return {
            'main_caption': content,
            'slide_count': len(slides_descriptions),
            'platform': platform,
        }

    def generate_alt_text(self, media_description: str) -> str:
        """
        Generate accessibility alt text for media.

        Note: Alt text is professional/descriptive, NOT persona-styled.

        Args:
            media_description: Description of the visual content

        Returns:
            Alt text string
        """
        prompt = (
            "Write concise, descriptive alt text for this image/video.\n"
            "Be factual and descriptive for screen readers.\n"
            "Max 125 characters. No hashtags, no emojis.\n\n"
            f"Media: {media_description}\n\n"
            "Return ONLY the alt text."
        )

        return self.response_generator._generate(prompt, max_length=125).strip()

    def suggest_media_format(
        self,
        content_idea: str,
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """
        Recommend the best media format for a content idea.

        Args:
            content_idea: The content concept
            platform: Target platform

        Returns:
            Dict with format recommendation and reasoning
        """
        active = self.persona.get_active_persona()
        system_prompt = active.get_system_prompt("business")

        prompt = (
            f"{system_prompt}\n\n"
            f"What's the best media format for this content on {platform}?\n\n"
            f"Content idea: {content_idea}\n\n"
            f"Choose from: Reel, Static Post, Carousel, Story, Live\n"
            f"Explain why in 1-2 sentences. Be direct."
        )

        raw = self.response_generator._generate(prompt, max_length=500)
        content = active.apply_vocab_transform(raw)

        return {
            'content_idea': content_idea,
            'platform': platform,
            'recommendation': content,
        }

    def queue_media(self, media_data: Dict[str, Any]):
        """Add a media captioning request to the queue."""
        self._media_queue.put_nowait(media_data)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SWIZZ Voice Media Agent")
    parser.add_argument('--action', choices=['caption', 'story', 'carousel', 'alt', 'suggest', 'status'],
                       default='status', help='Action to perform')
    parser.add_argument('--description', type=str, help='Media description')
    parser.add_argument('--context', type=str, default='', help='Additional context')
    parser.add_argument('--platform', type=str, default='instagram',
                       help='Target platform')
    parser.add_argument('--persona', type=str, default='professional',
                       choices=['professional', 'personal'],
                       help='Persona mode')
    parser.add_argument('--slides', type=str, nargs='+',
                       help='Slide descriptions for carousel')

    args = parser.parse_args()

    config = {
        'persona_mode': args.persona,
        'default_platform': args.platform,
    }

    agent = MediaAgent(config)

    if args.action == 'status':
        stats = agent.get_stats()
        print("\nMedia Agent Status:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    elif args.action == 'caption':
        if not args.description:
            print("[ERROR] --description required")
            return

        print(f"\n[INFO] Generating caption for {args.platform}...\n")
        caption = agent.generate_reel_caption(
            args.description, args.context, args.persona
        )
        print(f"Caption:\n{caption}")

    elif args.action == 'story':
        if not args.description:
            print("[ERROR] --description required (as context)")
            return

        print(f"\n[INFO] Generating story text...\n")
        text = agent.generate_story_text(args.description, persona_mode=args.persona)
        print(f"Story text: {text}")

    elif args.action == 'carousel':
        slides = args.slides or [args.description or "Slide content"]
        print(f"\n[INFO] Generating {len(slides)}-slide carousel captions...\n")
        result = agent.generate_carousel_captions(
            slides, args.platform, args.persona
        )
        print(result['main_caption'])

    elif args.action == 'alt':
        if not args.description:
            print("[ERROR] --description required")
            return

        alt = agent.generate_alt_text(args.description)
        print(f"\nAlt text: {alt}")

    elif args.action == 'suggest':
        if not args.description:
            print("[ERROR] --description required (as content idea)")
            return

        result = agent.suggest_media_format(args.description, args.platform)
        print(f"\n{result['recommendation']}")


if __name__ == "__main__":
    main()
