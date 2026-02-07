#!/usr/bin/env python3
"""
Writing Agent for Social Media Content Generation

Generates social media posts in the SWIZZ voice persona.
Supports dual-mode (professional @swizzimatic / personal @BigSwizzi)
with platform-aware formatting and vocabulary post-processing.

Features:
- Dual-persona voice generation (professional/personal)
- Platform-specific formatting (Instagram, TikTok, Twitter, etc.)
- Vocabulary post-processing for authentic speech style
- Human-in-the-loop review queue
- Thread/multi-post generation
"""

import asyncio
from typing import Dict, Any, Optional, List

from lib.agents.base_agent import BaseAgent, AgentState
from lib.persona.swizz_persona import SwizzPersona
from lib.storage.database import EngagementDatabase


class WritingAgent(BaseAgent):
    """
    Agent that generates social media content in the SWIZZ voice.

    Takes topics/prompts and produces platform-ready posts using
    the persona system for voice styling and vocabulary transforms.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        persona: Optional[SwizzPersona] = None,
        db: Optional[EngagementDatabase] = None,
        ai_provider: str = "gemini"
    ):
        """
        Initialize the writing agent.

        Args:
            config: Agent configuration dictionary
            persona: SwizzPersona instance (optional, creates default)
            db: Database instance (optional, creates new if not provided)
            ai_provider: AI provider for content generation
        """
        super().__init__(config, ai_provider, name="WritingAgent")

        self.persona = persona or SwizzPersona(
            mode=config.get('persona_mode', 'professional')
        )
        self.db = db or EngagementDatabase()

        # Configuration
        self.default_platform = config.get('default_platform', 'instagram')
        self.auto_approve = config.get('auto_approve', False)
        self.poll_interval = config.get('poll_interval_seconds', 30)

        # Queue for content generation requests
        self._content_queue: asyncio.Queue = asyncio.Queue()

        self.logger.info(
            f"Configured: persona={self.persona._mode}, "
            f"platform={self.default_platform}"
        )

    async def start(self):
        """Start the content generation loop."""
        self.transition(AgentState.MONITORING)
        self._running = True

        while self._running:
            try:
                # Process queued content requests
                try:
                    item = self._content_queue.get_nowait()
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
                self.logger.error(f"Generation error: {e}")
                await asyncio.sleep(self.poll_interval * 2)
                self.transition(AgentState.MONITORING)

        self.transition(AgentState.STOPPING)

    async def stop(self):
        """Gracefully stop the agent."""
        self.logger.info("Stop requested")
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    async def process_item(self, topic_data: Dict[str, Any]) -> bool:
        """
        Process a content generation request.

        Args:
            topic_data: Dict with topic, platform, post_type, persona_mode

        Returns:
            True if generated successfully
        """
        try:
            topic = topic_data.get('topic', '')
            platform = topic_data.get('platform', self.default_platform)
            post_type = topic_data.get('post_type', 'casual')
            persona_mode = topic_data.get('persona_mode', self.persona._mode)

            self.log_item('content', platform, 'self', topic)
            self.transition(AgentState.GENERATING)

            result = self.generate_post(
                topic=topic,
                platform=platform,
                post_type=post_type,
                persona_mode=persona_mode,
            )

            self.stats['items_processed'] += 1

            if self.auto_approve:
                self.stats['items_responded'] += 1
                self.format_console_output('success', f"Generated {post_type} for {platform}")
            else:
                self.stats['items_queued'] += 1
                self.format_console_output('queued', f"Review needed: {post_type} for {platform}")

            self.transition(AgentState.MONITORING)
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate content: {e}")
            self.stats['errors'] += 1
            return False

    def generate_post(
        self,
        topic: str,
        platform: str = "instagram",
        post_type: str = "casual",
        persona_mode: str = "professional",
    ) -> Dict[str, Any]:
        """
        Generate a social media post in SWIZZ voice.

        Args:
            topic: Content topic or prompt
            platform: Target platform
            post_type: One of: announcement, resource_share, casual, business, promo, hype
            persona_mode: "professional" (swizzimatic) or "personal" (bigswizzi)

        Returns:
            Dict with content, hashtags, emojis, platform, persona_mode, review_status
        """
        # Switch persona mode if needed
        if persona_mode != self.persona._mode:
            self.persona.set_mode(persona_mode)

        active = self.persona.get_active_persona()
        platform_config = self.persona.get_platform_config(platform)
        max_chars = platform_config.get('max_chars', 2200)

        # Build persona-aware prompt
        system_prompt = active.get_system_prompt(post_type)
        length_guide = active.get_response_length_guide(post_type)
        examples = active.get_few_shot_examples(post_type, count=3)

        examples_text = ""
        if examples:
            examples_text = "\n\nExamples of this voice style:\n" + "\n".join(
                f"- \"{ex}\"" for ex in examples
            )

        prompt = (
            f"{system_prompt}\n\n"
            f"Platform: {platform} (max {max_chars} characters)\n"
            f"Target length: {length_guide[0]}-{length_guide[1]} words\n"
            f"Post type: {post_type}\n"
            f"{examples_text}\n\n"
            f"Write a {platform} post about: {topic}\n\n"
            f"Return ONLY the post text. No explanations."
        )

        # Generate via AI
        raw_content = self.response_generator._generate(prompt, max_length=max_chars)

        # Apply vocabulary post-processing
        content = active.apply_vocab_transform(raw_content)

        # Enforce character limit
        if len(content) > max_chars:
            content = content[:max_chars - 3].rsplit(' ', 1)[0] + "..."

        # Select contextual emojis
        emojis = active.select_emojis(post_type, count=3)

        return {
            'content': content,
            'emojis': emojis,
            'platform': platform,
            'persona_mode': persona_mode,
            'post_type': post_type,
            'char_count': len(content),
            'review_status': 'approved' if self.auto_approve else 'pending',
        }

    def generate_caption(
        self,
        media_description: str,
        platform: str = "instagram",
        persona_mode: str = "professional",
    ) -> str:
        """
        Generate a caption for media content.

        Args:
            media_description: Description of the media
            platform: Target platform
            persona_mode: Voice mode

        Returns:
            Caption text
        """
        result = self.generate_post(
            topic=f"Write a caption for this media: {media_description}",
            platform=platform,
            post_type="casual",
            persona_mode=persona_mode,
        )
        return result['content']

    def generate_thread(
        self,
        topic: str,
        platform: str = "twitter",
        num_posts: int = 3,
        persona_mode: str = "professional",
    ) -> List[Dict[str, Any]]:
        """
        Generate a multi-post thread.

        Args:
            topic: Thread topic
            platform: Target platform
            num_posts: Number of posts in thread
            persona_mode: Voice mode

        Returns:
            List of post dicts
        """
        if persona_mode != self.persona._mode:
            self.persona.set_mode(persona_mode)

        active = self.persona.get_active_persona()
        platform_config = self.persona.get_platform_config(platform)
        max_chars = platform_config.get('max_chars', 280)

        system_prompt = active.get_system_prompt("business")

        prompt = (
            f"{system_prompt}\n\n"
            f"Platform: {platform} (max {max_chars} characters per post)\n"
            f"Write a {num_posts}-post thread about: {topic}\n\n"
            f"Return each post on a separate line, numbered 1/ 2/ 3/ etc.\n"
            f"Each post must be under {max_chars} characters.\n"
            f"Return ONLY the posts. No explanations."
        )

        raw = self.response_generator._generate(prompt, max_length=max_chars * num_posts)
        raw = active.apply_vocab_transform(raw)

        # Parse numbered posts
        posts = []
        for line in raw.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            # Remove numbering prefix
            import re
            cleaned = re.sub(r'^\d+[/.)]\s*', '', line)
            if cleaned and len(cleaned) > 5:
                if len(cleaned) > max_chars:
                    cleaned = cleaned[:max_chars - 3].rsplit(' ', 1)[0] + "..."
                posts.append({
                    'content': cleaned,
                    'platform': platform,
                    'persona_mode': persona_mode,
                    'char_count': len(cleaned),
                })

        return posts[:num_posts]

    def queue_content(self, topic_data: Dict[str, Any]):
        """Add a content request to the generation queue."""
        self._content_queue.put_nowait(topic_data)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SWIZZ Voice Writing Agent")
    parser.add_argument('--action', choices=['generate', 'thread', 'caption', 'status'],
                       default='status', help='Action to perform')
    parser.add_argument('--topic', type=str, help='Content topic')
    parser.add_argument('--platform', type=str, default='instagram',
                       help='Target platform')
    parser.add_argument('--post-type', type=str, default='casual',
                       choices=['announcement', 'resource_share', 'casual', 'business', 'promo', 'hype'],
                       help='Post type')
    parser.add_argument('--persona', type=str, default='professional',
                       choices=['professional', 'personal'],
                       help='Persona mode')
    parser.add_argument('--num-posts', type=int, default=3,
                       help='Number of posts for thread')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without posting')

    args = parser.parse_args()

    config = {
        'persona_mode': args.persona,
        'default_platform': args.platform,
        'auto_approve': not args.dry_run,
    }

    agent = WritingAgent(config)

    if args.action == 'status':
        stats = agent.get_stats()
        print("\nWriting Agent Status:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        print(f"\n  Persona Mode: {agent.persona._mode}")
        print(f"  Platform: {agent.default_platform}")

    elif args.action == 'generate':
        if not args.topic:
            print("[ERROR] --topic required for generate action")
            return

        print(f"\n[INFO] Generating {args.post_type} post for {args.platform}...")
        print(f"[INFO] Persona: {args.persona}")
        print(f"[INFO] Topic: {args.topic}\n")

        result = agent.generate_post(
            topic=args.topic,
            platform=args.platform,
            post_type=args.post_type,
            persona_mode=args.persona,
        )

        print("=" * 60)
        print(f"Platform: {result['platform']} | Mode: {result['persona_mode']}")
        print(f"Type: {result['post_type']} | Chars: {result['char_count']}")
        print("=" * 60)
        print(f"\n{result['content']}\n")
        print(f"Emojis: {' '.join(result['emojis'])}")
        print("=" * 60)

    elif args.action == 'thread':
        if not args.topic:
            print("[ERROR] --topic required for thread action")
            return

        print(f"\n[INFO] Generating {args.num_posts}-post thread...")
        posts = agent.generate_thread(
            topic=args.topic,
            platform=args.platform,
            num_posts=args.num_posts,
            persona_mode=args.persona,
        )

        print("=" * 60)
        for i, post in enumerate(posts, 1):
            print(f"\n[{i}/{len(posts)}] ({post['char_count']} chars)")
            print(post['content'])
        print("\n" + "=" * 60)

    elif args.action == 'caption':
        if not args.topic:
            print("[ERROR] --topic required (use as media description)")
            return

        caption = agent.generate_caption(
            media_description=args.topic,
            platform=args.platform,
            persona_mode=args.persona,
        )
        print(f"\nCaption:\n{caption}")


if __name__ == "__main__":
    main()
