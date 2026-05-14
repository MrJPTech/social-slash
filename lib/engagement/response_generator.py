#!/usr/bin/env python3
"""
AI Response Generator for Engagement Automation

Uses Gemini (default) or Anthropic to generate contextual replies
for comments and DMs across social media platforms.

Features:
- Platform-aware responses
- Brand voice customization
- Sentiment detection
- Context-aware threading
"""

import json
import os
from typing import Any


class ResponseGenerator:
    """
    AI-powered response generator for social media engagement.

    Generates contextual, platform-appropriate replies using
    Gemini or Anthropic as the AI backend.
    """

    # Platform-specific guidelines
    PLATFORM_GUIDELINES = {
        "instagram": {
            "max_length": 2200,
            "tone": "friendly, visual-focused",
            "use_emojis": True,
            "mention_style": "@username",
        },
        "twitter": {
            "max_length": 280,
            "tone": "concise, punchy",
            "use_emojis": True,
            "mention_style": "@username",
        },
        "linkedin": {
            "max_length": 3000,
            "tone": "professional, thoughtful",
            "use_emojis": False,
            "mention_style": "formal name",
        },
        "reddit": {
            "max_length": 10000,
            "tone": "conversational, community-focused",
            "use_emojis": False,
            "mention_style": "u/username",
        },
        "youtube": {
            "max_length": 10000,
            "tone": "engaging, appreciative",
            "use_emojis": True,
            "mention_style": "@username",
        },
        "facebook": {
            "max_length": 8000,
            "tone": "friendly, conversational",
            "use_emojis": True,
            "mention_style": "first name",
        },
        "tiktok": {
            "max_length": 1000,
            "tone": "casual, fun, trendy",
            "use_emojis": True,
            "mention_style": "@username",
        },
        "bluesky": {
            "max_length": 300,
            "tone": "conversational, thoughtful",
            "use_emojis": True,
            "mention_style": "@handle",
        },
        "telegram": {
            "max_length": 4096,
            "tone": "direct, helpful",
            "use_emojis": True,
            "mention_style": "@username",
        },
    }

    # Default brand voice templates
    BRAND_VOICES = {
        "professional": "Respond in a professional, helpful tone. Be knowledgeable but approachable.",
        "friendly": "Respond in a warm, friendly tone. Be conversational and personable.",
        "casual": "Respond in a casual, relaxed tone. Keep it light and authentic.",
        "enthusiastic": "Respond with enthusiasm and energy. Show genuine excitement.",
        "supportive": "Respond with empathy and support. Focus on helping and reassuring.",
        "swizz": 'You are SWIZZ. Speak casually and directly. Keep responses short (under 15 words for casual, under 30 for business). Use "ya" instead of "your", contractions like "gonna", "wanna", "gotta". Use emojis contextually but not excessively. Be a connector - share resources and make introductions. Be direct and honest. Never over-explain.',
        "bigswizzi": 'You are Big Swizzi. Ultra-concise (1-7 words max). Maximum enthusiasm always. Use AAVE naturally: "dis", "fo", "imma", "finna", "fasho", "fr". Address people as "gang", "twin", "fam", "dawg". Agree with "bet", "say less", "fasho", "no cap". Use caps for emphasis 30% of the time. Emojis: fire, 100, prayer hands, skull, devil. Never formal. Never over-explain. Keep it real.',
        "jordan_ward": "You are Jordan Ward, CEO of PRSMTECH. Evidence-based thought leader. Speak with authority backed by data and real experience. Lead with hooks. Be contrarian when evidence supports it. Mentorship-oriented: teach from experience, not theory. Every post includes specifics (numbers, metrics, timeframes). Polished but direct — no slang, no hedging. End with a CTA.",
    }

    def __init__(
        self,
        provider: str = "gemini",
        brand_voice: str = "professional",
        api_key: str | None = None,
    ):
        """
        Initialize the response generator.

        Args:
            provider: AI provider ('gemini' or 'anthropic')
            brand_voice: Brand voice style key or custom instructions
            api_key: Optional API key (defaults to env var)
        """
        self.provider = provider.lower()
        self.brand_voice = brand_voice
        self._client = None
        self._api_key = api_key

        # Validate provider
        if self.provider not in ["gemini", "anthropic"]:
            raise ValueError(f"Unsupported provider: {provider}. Use 'gemini' or 'anthropic'.")

        # Lazy init AI client
        self._init_client()

    def _init_client(self):
        """Initialize the AI client based on provider."""
        if self.provider == "gemini":
            try:
                from google import genai

                api_key = self._api_key or os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise ValueError("GOOGLE_API_KEY not found")
                self._genai_client = genai.Client(api_key=api_key)
                self._client = self._genai_client
                print("[INFO] Response generator initialized with Gemini")
            except ImportError:
                raise ImportError("google-genai package required. Run: pip install google-genai")

        elif self.provider == "anthropic":
            try:
                import anthropic

                api_key = self._api_key or os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found")
                self._client = anthropic.Anthropic(api_key=api_key)
                print("[INFO] Response generator initialized with Anthropic")
            except ImportError:
                raise ImportError("anthropic package required. Run: pip install anthropic")

    def _get_brand_voice_instructions(self) -> str:
        """Get brand voice instructions."""
        if self.brand_voice in self.BRAND_VOICES:
            return self.BRAND_VOICES[self.brand_voice]
        return self.brand_voice  # Assume it's custom instructions

    def _get_platform_guidelines(self, platform: str) -> dict[str, Any]:
        """Get platform-specific guidelines."""
        return self.PLATFORM_GUIDELINES.get(
            platform.lower(),
            self.PLATFORM_GUIDELINES["twitter"],  # Default fallback
        )

    # ─────────────────────────────────────────────────────────────
    # COMMENT REPLIES
    # ─────────────────────────────────────────────────────────────

    def generate_comment_reply(
        self,
        comment: str,
        author: str,
        platform: str,
        original_post: str | None = None,
        context: list[dict[str, str]] | None = None,
        custom_instructions: str | None = None,
    ) -> str:
        """
        Generate a reply to a comment.

        Args:
            comment: The comment to reply to
            author: Comment author's name/username
            platform: Platform name
            original_post: The original post content (context)
            context: Previous comments in thread (list of {author, content})
            custom_instructions: Additional instructions

        Returns:
            Generated reply text
        """
        guidelines = self._get_platform_guidelines(platform)
        brand_voice = self._get_brand_voice_instructions()

        # Build context section
        context_text = ""
        if original_post:
            context_text += f"\n\nOriginal post we're replying under:\n{original_post[:500]}"
        if context:
            context_text += "\n\nPrevious comments in thread:"
            for c in context[-5:]:  # Last 5 comments
                context_text += f"\n- @{c.get('author', 'unknown')}: {c.get('content', '')[:200]}"

        prompt = f"""You are a social media community manager responding to a comment on {platform}.

Brand Voice: {brand_voice}

Platform Guidelines for {platform}:
- Maximum length: {guidelines["max_length"]} characters
- Tone: {guidelines["tone"]}
- Use emojis: {"Yes" if guidelines["use_emojis"] else "No"}
- Address user as: {guidelines["mention_style"]}

{custom_instructions or ""}

{context_text}

Comment from @{author}:
"{comment}"

Generate a natural, engaging reply. Be authentic and human.
Keep it concise (1-3 sentences usually).
Don't start with "Hey" or "Hi" every time - vary your openings.
Match the energy of the commenter when appropriate.

Reply only with the response text, nothing else."""

        try:
            return self._generate(prompt, max_length=guidelines["max_length"])
        except Exception as e:
            print(f"[ERROR] Failed to generate comment reply: {e}")
            raise

    # ─────────────────────────────────────────────────────────────
    # DM REPLIES
    # ─────────────────────────────────────────────────────────────

    def generate_dm_reply(
        self,
        message: str,
        sender_name: str,
        platform: str,
        conversation_history: list[dict[str, Any]] | None = None,
        custom_instructions: str | None = None,
    ) -> str:
        """
        Generate a reply to a direct message.

        Args:
            message: The incoming message
            sender_name: Sender's name
            platform: Platform name
            conversation_history: Previous messages [{is_me: bool, content: str}]
            custom_instructions: Additional instructions

        Returns:
            Generated reply text
        """
        guidelines = self._get_platform_guidelines(platform)
        brand_voice = self._get_brand_voice_instructions()

        # Build conversation history
        history_text = ""
        if conversation_history:
            history_text = "\n\nConversation history:"
            for msg in conversation_history[-10:]:  # Last 10 messages
                role = "Me" if msg.get("is_me") else sender_name
                history_text += f"\n{role}: {msg.get('content', '')[:200]}"

        prompt = f"""You are responding to a direct message on {platform}.

Brand Voice: {brand_voice}

Platform Guidelines for {platform}:
- Maximum length: {guidelines["max_length"]} characters
- Tone: {guidelines["tone"]}
- Use emojis: {"Yes" if guidelines["use_emojis"] else "No"}

{custom_instructions or ""}

{history_text}

New message from {sender_name}:
"{message}"

Generate a helpful, conversational reply.
Be personable and address their needs directly.
If they have a question, answer it. If they need help, offer it.
Keep it natural - this is a private conversation.

Reply only with the response text, nothing else."""

        try:
            return self._generate(prompt, max_length=guidelines["max_length"])
        except Exception as e:
            print(f"[ERROR] Failed to generate DM reply: {e}")
            raise

    # ─────────────────────────────────────────────────────────────
    # SENTIMENT ANALYSIS
    # ─────────────────────────────────────────────────────────────

    def analyze_sentiment(self, content: str) -> dict[str, Any]:
        """
        Analyze the sentiment of content.

        Args:
            content: Text to analyze

        Returns:
            Dictionary with sentiment, score, and keywords
        """
        prompt = f"""Analyze the sentiment of this social media message.

Message:
"{content}"

Respond in JSON format only:
{{
    "sentiment": "positive" | "neutral" | "negative",
    "score": 0.0-1.0 (0 = very negative, 0.5 = neutral, 1 = very positive),
    "keywords": ["key", "emotional", "words"],
    "requires_attention": true | false (urgent/complaint/issue),
    "category": "question" | "feedback" | "complaint" | "praise" | "general"
}}"""

        try:
            response = self._generate(prompt, max_length=500)
            # Parse JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return json.loads(response.strip())
        except Exception as e:
            print(f"[ERROR] Sentiment analysis failed: {e}")
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "keywords": [],
                "requires_attention": False,
                "category": "general",
            }

    # ─────────────────────────────────────────────────────────────
    # CORE GENERATION
    # ─────────────────────────────────────────────────────────────

    def _generate(self, prompt: str, max_length: int = 1000) -> str:
        """
        Generate text using the configured AI provider.

        Args:
            prompt: The prompt to send
            max_length: Maximum response length

        Returns:
            Generated text
        """
        if self.provider == "gemini":
            response = self._client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            text = response.text.strip()
        elif self.provider == "anthropic":
            response = self._client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=max_length,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Enforce max length
        if len(text) > max_length:
            text = text[: max_length - 3] + "..."

        return text

    # ─────────────────────────────────────────────────────────────
    # TEMPLATES
    # ─────────────────────────────────────────────────────────────

    def apply_template(
        self, template_name: str, variables: dict[str, str], templates: dict[str, str] | None = None
    ) -> str:
        """
        Apply a response template with variables.

        Args:
            template_name: Name of template
            variables: Variables to substitute
            templates: Custom templates dict (optional)

        Returns:
            Formatted response
        """
        default_templates = {
            "thank_you": "Thanks for your {type}, {name}! {custom}",
            "question_ack": "Great question, {name}! {answer}",
            "feedback_ack": "We really appreciate your feedback, {name}. {response}",
            "apology": "We're sorry to hear that, {name}. {resolution}",
            "welcome": "Welcome to the community, {name}! {message}",
        }

        all_templates = {**default_templates, **(templates or {})}

        if template_name not in all_templates:
            raise ValueError(f"Template '{template_name}' not found")

        template = all_templates[template_name]
        return template.format(**variables)


# Example usage
if __name__ == "__main__":
    # Test with Gemini
    try:
        generator = ResponseGenerator(provider="gemini", brand_voice="friendly")

        # Test comment reply
        reply = generator.generate_comment_reply(
            comment="Love this! Where can I get one?",
            author="user123",
            platform="instagram",
            original_post="Check out our new product launch! 🚀",
        )
        print(f"\nGenerated comment reply:\n{reply}")

        # Test sentiment analysis
        sentiment = generator.analyze_sentiment("This is amazing! Best purchase ever!")
        print(f"\nSentiment analysis:\n{json.dumps(sentiment, indent=2)}")

    except Exception as e:
        print(f"[ERROR] {e}")
        print("Make sure GOOGLE_API_KEY is set in environment")
