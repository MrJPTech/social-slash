#!/usr/bin/env python3
"""
Research Agent for Content Strategy

Researches trending topics, hashtags, and content ideas for social media.
Outputs research summaries in the SWIZZ voice persona style.

Features:
- Trending topic analysis
- Hashtag research with engagement estimates
- Content idea generation
- Content calendar building
- Platform-specific insights
"""

import asyncio
from typing import Dict, Any, Optional, List

from lib.agents.base_agent import BaseAgent, AgentState
from lib.persona.swizz_persona import SwizzPersona


class ResearchAgent(BaseAgent):
    """
    Agent that researches content strategy and suggests ideas.

    Uses AI to analyze trends and generate content suggestions
    formatted in the SWIZZ voice style.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        persona: Optional[SwizzPersona] = None,
        ai_provider: str = "gemini"
    ):
        """
        Initialize the research agent.

        Args:
            config: Agent configuration dictionary
            persona: SwizzPersona instance (optional, creates default)
            ai_provider: AI provider for research
        """
        super().__init__(config, ai_provider, name="ResearchAgent")

        self.persona = persona or SwizzPersona(
            mode=config.get('persona_mode', 'professional')
        )

        self.default_platform = config.get('default_platform', 'instagram')
        self.poll_interval = config.get('poll_interval_seconds', 60)

        # Research task queue
        self._task_queue: asyncio.Queue = asyncio.Queue()

        self.logger.info(f"Configured: platform={self.default_platform}")

    async def start(self):
        """Start the research task loop."""
        self.transition(AgentState.MONITORING)
        self._running = True

        while self._running:
            try:
                try:
                    task = self._task_queue.get_nowait()
                    await self.process_item(task)
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
                self.logger.error(f"Research error: {e}")
                await asyncio.sleep(self.poll_interval * 2)
                self.transition(AgentState.MONITORING)

        self.transition(AgentState.STOPPING)

    async def stop(self):
        """Gracefully stop the agent."""
        self.logger.info("Stop requested")
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    async def process_item(self, research_task: Dict[str, Any]) -> bool:
        """
        Execute a research task.

        Args:
            research_task: Dict with task_type, params

        Returns:
            True if completed successfully
        """
        try:
            task_type = research_task.get('task_type', 'suggest')
            self.transition(AgentState.PROCESSING)

            if task_type == 'trending_topics':
                platform = research_task.get('platform', self.default_platform)
                result = self.analyze_trending(platform)
            elif task_type == 'hashtag_research':
                topic = research_task.get('topic', '')
                platform = research_task.get('platform', self.default_platform)
                result = self.research_hashtags(topic, platform)
            elif task_type == 'content_ideas':
                theme = research_task.get('theme', '')
                count = research_task.get('count', 5)
                result = self.suggest_content_ideas(theme, count)
            elif task_type == 'content_calendar':
                days = research_task.get('days', 7)
                platforms = research_task.get('platforms', [self.default_platform])
                result = self.build_content_calendar(days, platforms)
            else:
                self.logger.warning(f"Unknown task type: {task_type}")
                return False

            self.stats['items_processed'] += 1
            self.format_console_output('success', f"Completed {task_type} research")
            self.transition(AgentState.MONITORING)
            return True

        except Exception as e:
            self.logger.error(f"Research task failed: {e}")
            self.stats['errors'] += 1
            return False

    def research_hashtags(
        self,
        topic: str,
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """
        Find relevant hashtags for a topic.

        Args:
            topic: Content topic
            platform: Target platform

        Returns:
            Dict with hashtags list, categories, and usage tips
        """
        active = self.persona.get_active_persona()
        system_prompt = active.get_system_prompt("business")
        platform_config = self.persona.get_platform_config(platform)
        max_hashtags = platform_config.get('hashtag_limit', 30)

        prompt = (
            f"{system_prompt}\n\n"
            f"Research hashtags for {platform} about: {topic}\n\n"
            f"Provide {min(max_hashtags, 20)} hashtags organized as:\n"
            f"- 5 high-volume (broad reach)\n"
            f"- 5 medium-volume (targeted)\n"
            f"- 5 niche (specific community)\n"
            f"- 5 branded/trending\n\n"
            f"Format: #hashtag - brief reason\n"
            f"Keep explanations concise (SWIZZ style - direct, no fluff)."
        )

        raw = self.response_generator._generate(prompt, max_length=1500)
        content = active.apply_vocab_transform(raw)

        return {
            'topic': topic,
            'platform': platform,
            'max_hashtags': max_hashtags,
            'research': content,
        }

    def suggest_content_ideas(
        self,
        theme: str,
        count: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate content ideas for a theme.

        Args:
            theme: Content theme or niche
            count: Number of ideas to generate

        Returns:
            Dict with ideas list and metadata
        """
        active = self.persona.get_active_persona()
        system_prompt = active.get_system_prompt("business")

        prompt = (
            f"{system_prompt}\n\n"
            f"Suggest {count} social media content ideas about: {theme}\n\n"
            f"For each idea provide:\n"
            f"1. Content idea (one line)\n"
            f"2. Best format (reel/post/story/carousel)\n"
            f"3. Best platform\n"
            f"4. Hook line (in SWIZZ voice - short, punchy)\n\n"
            f"Keep it direct. No fluff."
        )

        raw = self.response_generator._generate(prompt, max_length=2000)
        content = active.apply_vocab_transform(raw)

        return {
            'theme': theme,
            'count': count,
            'ideas': content,
        }

    def analyze_trending(
        self,
        platform: str = "instagram",
    ) -> Dict[str, Any]:
        """
        Identify trending topics on a platform.

        Args:
            platform: Platform to analyze

        Returns:
            Dict with trending topics and recommendations
        """
        active = self.persona.get_active_persona()
        system_prompt = active.get_system_prompt("business")

        prompt = (
            f"{system_prompt}\n\n"
            f"What content formats and topics are trending on {platform} right now?\n\n"
            f"Cover:\n"
            f"- Top 5 content formats performing well\n"
            f"- Top 5 topic categories getting engagement\n"
            f"- 3 emerging trends to watch\n"
            f"- 2 formats to avoid (declining engagement)\n\n"
            f"Be direct and actionable. SWIZZ style."
        )

        raw = self.response_generator._generate(prompt, max_length=2000)
        content = active.apply_vocab_transform(raw)

        return {
            'platform': platform,
            'analysis': content,
        }

    def build_content_calendar(
        self,
        days: int = 7,
        platforms: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a content calendar.

        Args:
            days: Number of days to plan
            platforms: Target platforms

        Returns:
            Dict with calendar entries
        """
        if platforms is None:
            platforms = [self.default_platform]

        active = self.persona.get_active_persona()
        system_prompt = active.get_system_prompt("business")
        platforms_str = ", ".join(platforms)

        prompt = (
            f"{system_prompt}\n\n"
            f"Create a {days}-day content calendar for: {platforms_str}\n\n"
            f"For each day provide:\n"
            f"- Day number\n"
            f"- Platform\n"
            f"- Content type (reel/post/story/carousel)\n"
            f"- Topic/theme\n"
            f"- Caption hook (in SWIZZ voice)\n"
            f"- Best posting time\n\n"
            f"Mix formats. Keep hooks punchy. Be strategic."
        )

        raw = self.response_generator._generate(prompt, max_length=3000)
        content = active.apply_vocab_transform(raw)

        return {
            'days': days,
            'platforms': platforms,
            'calendar': content,
        }

    def queue_task(self, task_data: Dict[str, Any]):
        """Add a research task to the queue."""
        self._task_queue.put_nowait(task_data)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SWIZZ Voice Research Agent")
    parser.add_argument('--action', choices=['hashtags', 'suggest', 'trending', 'calendar', 'status'],
                       default='status', help='Action to perform')
    parser.add_argument('--topic', type=str, help='Research topic')
    parser.add_argument('--theme', type=str, help='Content theme')
    parser.add_argument('--platform', type=str, default='instagram',
                       help='Target platform')
    parser.add_argument('--count', type=int, default=5,
                       help='Number of results')
    parser.add_argument('--days', type=int, default=7,
                       help='Calendar days')
    parser.add_argument('--persona', type=str, default='professional',
                       choices=['professional', 'personal'],
                       help='Persona mode')

    args = parser.parse_args()

    config = {
        'persona_mode': args.persona,
        'default_platform': args.platform,
    }

    agent = ResearchAgent(config)

    if args.action == 'status':
        stats = agent.get_stats()
        print("\nResearch Agent Status:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    elif args.action == 'hashtags':
        if not args.topic:
            print("[ERROR] --topic required for hashtag research")
            return

        print(f"\n[INFO] Researching hashtags for '{args.topic}' on {args.platform}...\n")
        result = agent.research_hashtags(args.topic, args.platform)
        print(result['research'])

    elif args.action == 'suggest':
        theme = args.theme or args.topic
        if not theme:
            print("[ERROR] --theme or --topic required")
            return

        print(f"\n[INFO] Generating {args.count} content ideas for '{theme}'...\n")
        result = agent.suggest_content_ideas(theme, args.count)
        print(result['ideas'])

    elif args.action == 'trending':
        print(f"\n[INFO] Analyzing trends on {args.platform}...\n")
        result = agent.analyze_trending(args.platform)
        print(result['analysis'])

    elif args.action == 'calendar':
        print(f"\n[INFO] Building {args.days}-day content calendar...\n")
        result = agent.build_content_calendar(args.days, [args.platform])
        print(result['calendar'])


if __name__ == "__main__":
    main()
