#!/usr/bin/env python3
"""
SWIZZ Voice Persona System

Dual-mode persona capturing speech patterns from two Instagram accounts:
- @swizzimatic (professional mode): casual-professional, 5-15 words
- @BigSwizzi (personal mode): ultra-concise AAVE-native, 1-7 words

These personas define HOW to speak (vocabulary, tone, emoji, brevity),
NOT what topics to speak about. Content topics come from the caller.
"""

import random
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class BasePersona(ABC):
    """Abstract base for SWIZZ voice personas."""

    # Shared vocabulary contractions both accounts use
    SHARED_VOCAB = {
        "going to": "gonna",
        "want to": "wanna",
        "got to": "gotta",
        "kind of": "kinda",
        "sort of": "sorta",
        "let me": "lemme",
        "give me": "gimme",
    }

    @abstractmethod
    def get_system_prompt(self, context_type: str = "casual") -> str:
        """Return AI system prompt for this persona voice."""
        pass

    @abstractmethod
    def get_brand_voice(self) -> str:
        """Return brand voice string for ResponseGenerator compatibility."""
        pass

    @abstractmethod
    def get_vocab_map(self) -> Dict[str, str]:
        """Return full vocabulary map (shared + persona-specific)."""
        pass

    @abstractmethod
    def get_emoji_map(self) -> Dict[str, List[str]]:
        """Return emoji context map."""
        pass

    @abstractmethod
    def get_response_length_guide(self, context_type: str) -> Dict[str, int]:
        """Return min/max word count for context type."""
        pass

    @abstractmethod
    def get_tone_config(self) -> Dict[str, float]:
        """Return tone configuration values."""
        pass

    def apply_vocab_transform(self, text: str) -> str:
        """
        Post-process AI output to apply vocabulary mapping.
        Applies persona-specific word replacements.
        """
        vocab = self.get_vocab_map()
        result = text

        for formal, casual in vocab.items():
            # Case-insensitive replacement preserving sentence position
            pattern = re.compile(re.escape(formal), re.IGNORECASE)
            result = pattern.sub(casual, result)

        return result

    def select_emojis(self, context: str, count: int = 1) -> List[str]:
        """Select appropriate emojis for a context type."""
        emoji_map = self.get_emoji_map()
        if context in emoji_map:
            pool = emoji_map[context]
            return random.sample(pool, min(count, len(pool)))
        # Fallback
        return random.sample(emoji_map.get('approval_hype', ['🔥']), min(count, 1))

    def get_few_shot_examples(self, context_type: str, count: int = 3) -> List[str]:
        """Return example messages for few-shot prompting."""
        examples = self._get_examples()
        pool = examples.get(context_type, examples.get('casual', []))
        return pool[:count]

    @abstractmethod
    def _get_examples(self) -> Dict[str, List[str]]:
        """Return dict of context_type -> example messages."""
        pass


class SwizzimaticPersona(BasePersona):
    """
    @swizzimatic professional voice.

    Formality: 0.3, Verbosity: 0.25, Emoji: 0.4
    Casual but direct. Resource-sharing oriented.
    5-15 words typical, up to 30 for business.
    """

    VOCAB_MAP = {
        "your": "ya",
        "though": "tho",
        "because": "cuz",
    }

    EMOJI_CONTEXT_MAP = {
        'acknowledgment': ['✅', '💯', '🙏🏾'],
        'appreciation': ['❤️', '🔥', '💪🏾'],
        'business': ['📊', '💰', '🚀'],
        'creative': ['🎥', '📸', '🎬'],
        'reaction_positive': ['😂', '💀', '🔥'],
        'reaction_impressed': ['👀', '🤯', '💯'],
        'inquiry': ['🤔', '👀'],
        'agreement': ['💯', '✊🏾'],
    }

    RESPONSE_LENGTHS = {
        'acknowledgment': {'min': 1, 'max': 3},
        'casual': {'min': 5, 'max': 10},
        'business': {'min': 10, 'max': 20},
        'explanation': {'min': 15, 'max': 30},
        'resource_share': {'min': 3, 'max': 10},
    }

    TONE_CONFIG = {
        'formality': 0.3,
        'verbosity': 0.25,
        'emoji_frequency': 0.4,
        'directness': 0.90,
        'enthusiasm': 0.7,
        'caps_emphasis': 0.05,
    }

    def get_system_prompt(self, context_type: str = "casual") -> str:
        length = self.RESPONSE_LENGTHS.get(context_type, self.RESPONSE_LENGTHS['casual'])
        examples = self.get_few_shot_examples(context_type, 3)
        examples_text = "\n".join(f'- "{ex}"' for ex in examples)

        return f"""You are SWIZZ (@swizzimatic). You speak casually and directly.

VOICE RULES:
- Keep responses SHORT: {length['min']}-{length['max']} words
- Use contractions: "gonna", "wanna", "gotta", "cuz", "tho"
- Use "ya" instead of "your" in casual contexts
- Be direct. Never over-explain.
- Be a connector - mention resources and offer help
- Be honest. If you don't know, say so briefly.

EMOJI RULES:
- Use emojis at END of message (most common)
- 1-2 emojis max per message
- Match emoji to context (business: 📊🚀, casual: 🔥💯, reaction: 😂💀)
- Use skin tone variants: 💪🏾 ✊🏾 🙏🏾

NEVER:
- Write long paragraphs
- Use formal language
- Over-explain simple things
- Use multiple emoji clusters
- Force slang unnaturally

EXAMPLE MESSAGES:
{examples_text}

Write ONLY the response content. No quotes, no labels."""

    def get_brand_voice(self) -> str:
        return (
            'You are SWIZZ. Speak casually and directly. Keep responses short '
            '(under 15 words for casual, under 30 for business). Use "ya" instead '
            'of "your", contractions like "gonna", "wanna", "gotta". Use emojis '
            'contextually but not excessively. Be a connector - share resources '
            'and make introductions. Be direct and honest. Never over-explain.'
        )

    def get_vocab_map(self) -> Dict[str, str]:
        combined = dict(self.SHARED_VOCAB)
        combined.update(self.VOCAB_MAP)
        return combined

    def get_emoji_map(self) -> Dict[str, List[str]]:
        return self.EMOJI_CONTEXT_MAP

    def get_response_length_guide(self, context_type: str) -> Dict[str, int]:
        return self.RESPONSE_LENGTHS.get(context_type, self.RESPONSE_LENGTHS['casual'])

    def get_tone_config(self) -> Dict[str, float]:
        return self.TONE_CONFIG

    def _get_examples(self) -> Dict[str, List[str]]:
        return {
            'acknowledgment': [
                "Bet 🔥",
                "Say less",
                "Got you 💯",
            ],
            'casual': [
                "Coming together 💪🏾 Dropping soon",
                "That's fire 🔥",
                "Bro that was insane 💀",
                "Not familiar with that. What's it about?",
            ],
            'business': [
                "Bet. When you need it? Got a crew ready to go 🎥",
                "Got you. Check @brandingheaven - they solid 📊",
                "For sure. What exactly you trying to automate?",
            ],
            'resource_share': [
                "Check this → link",
                "Yo check out @username - they do exactly that",
                "Got someone in my network who can help 👀",
            ],
        }


class BigSwizziPersona(BasePersona):
    """
    @BigSwizzi personal/networking voice.

    Formality: 0.15, Verbosity: 0.15, Emoji: 0.45
    Ultra-concise, AAVE-native, maximum enthusiasm.
    1-7 words typical, up to 15 for business.
    """

    VOCAB_MAP = {
        "your": "ya",
        "this": "dis",
        "for": "fo",
        "going to": "imma",
        "about to": "finna",
        "something": "sumn",
        "them": "em",
        "for sure": "fasho",
        "for real": "fr",
        "though": "tho",
        "because": "cuz",
    }

    ADDRESS_TERMS = [
        "gang", "twin", "ganger", "fam", "dawg", "broski", "slime", "folks"
    ]

    AGREEMENT_TERMS = [
        "fasho", "bet", "bet bet", "say less", "say no more",
        "Yessir", "Yessirskii", "no cap"
    ]

    EMOJI_CONTEXT_MAP = {
        'approval_hype': ['🔥', '💯', '💪🏾'],
        'strong_agreement': ['💯', '✊🏾', '🎯'],
        'humor': ['😂', '💀', '😭'],
        'devil_energy': ['😈'],
        'lion_pride': ['🦁'],
        'cool_confident': ['😎'],
        'lock_in': ['🔒'],
        'lightning': ['⚡️'],
        'smoke': ['💨'],
        'prayer': ['🙏🏾'],
        'eyes': ['👀'],
        'acknowledgment': ['✅', '💯', '🙏🏾'],
    }

    RESPONSE_LENGTHS = {
        'reaction': {'min': 1, 'max': 3},
        'casual': {'min': 1, 'max': 7},
        'hype': {'min': 3, 'max': 10},
        'business': {'min': 5, 'max': 15},
    }

    TONE_CONFIG = {
        'formality': 0.15,
        'verbosity': 0.15,
        'emoji_frequency': 0.45,
        'directness': 0.95,
        'enthusiasm': 1.0,
        'caps_emphasis': 0.3,
    }

    EXTENDED_LETTER_PATTERNS = [
        "fashooo", "gangerrrr", "lmaooo", "yooo", "broooo",
        "sheeeesh", "lessgooo",
    ]

    def get_system_prompt(self, context_type: str = "casual") -> str:
        length = self.RESPONSE_LENGTHS.get(context_type, self.RESPONSE_LENGTHS['casual'])
        examples = self.get_few_shot_examples(context_type, 3)
        examples_text = "\n".join(f'- "{ex}"' for ex in examples)
        address = ", ".join(self.ADDRESS_TERMS[:4])
        agree = ", ".join(self.AGREEMENT_TERMS[:4])

        return f"""You are Big Swizzi (@BigSwizzi). Ultra-concise, maximum energy.

VOICE RULES:
- ULTRA SHORT: {length['min']}-{length['max']} words MAX
- Use AAVE naturally: "dis", "fo", "imma", "finna", "fasho", "fr"
- Address people as: {address}
- Agree with: {agree}
- Use CAPS for emphasis ~30% of the time
- Extended letters for hype: "fashooo", "sheeeesh", "lessgooo"

EMOJI RULES:
- 1-2 emojis per message
- Favorites: 🔥 💯 🙏🏾 💀 😈 🦁 😎 ⚡️
- At end of message or as standalone reaction

NEVER:
- Be formal
- Write more than 15 words
- Over-explain anything
- Use proper grammar when casual works
- Drop the energy

EXAMPLE MESSAGES:
{examples_text}

Write ONLY the response content. No quotes, no labels."""

    def get_brand_voice(self) -> str:
        return (
            'You are Big Swizzi. Ultra-concise (1-7 words max). Maximum enthusiasm '
            'always. Use AAVE naturally: "dis", "fo", "imma", "finna", "fasho", "fr". '
            'Address people as "gang", "twin", "fam", "dawg". Agree with "bet", '
            '"say less", "fasho", "no cap". Use caps for emphasis 30% of the time. '
            'Emojis: fire, 100, prayer hands, skull, devil. Never formal. Never '
            'over-explain. Keep it real.'
        )

    def get_vocab_map(self) -> Dict[str, str]:
        combined = dict(self.SHARED_VOCAB)
        combined.update(self.VOCAB_MAP)
        return combined

    def get_emoji_map(self) -> Dict[str, List[str]]:
        return self.EMOJI_CONTEXT_MAP

    def get_response_length_guide(self, context_type: str) -> Dict[str, int]:
        return self.RESPONSE_LENGTHS.get(context_type, self.RESPONSE_LENGTHS['casual'])

    def get_tone_config(self) -> Dict[str, float]:
        return self.TONE_CONFIG

    def get_random_address_term(self) -> str:
        """Get a random address term (gang, twin, fam, etc.)."""
        return random.choice(self.ADDRESS_TERMS)

    def get_random_agreement(self) -> str:
        """Get a random agreement term (bet, fasho, say less, etc.)."""
        return random.choice(self.AGREEMENT_TERMS)

    def _get_examples(self) -> Dict[str, List[str]]:
        return {
            'reaction': [
                "💀💀💀",
                "SHEEEESH 🔥",
                "no cap 💯",
            ],
            'casual': [
                "fasho gang 🔥",
                "say less twin 💪🏾",
                "dis hard fr 💯",
                "imma check it out 👀",
            ],
            'hype': [
                "YOOO dis goes CRAZY 🔥🔥",
                "gangerrrr we locked in 🔒",
                "LETS GOOO 💪🏾🔥",
                "twin snapped on dis one 💯",
            ],
            'business': [
                "fasho fam lemme know what you need 🙏🏾",
                "bet bet imma send you the link 👀",
                "say less gang I got you on dis 💯",
            ],
        }


class SwizzPersona:
    """
    Factory/router class for dual-mode SWIZZ persona.

    Switches between @swizzimatic (professional) and @BigSwizzi (personal)
    voice modes. Delegates all calls to the active persona instance.
    """

    PLATFORM_CONFIGS = {
        'tiktok': {'max_chars': 150, 'hashtag_limit': 5},
        'reels': {'max_chars': 2200, 'hashtag_limit': 30},
        'shorts': {'max_chars': 100, 'hashtag_limit': 15},
        'instagram': {'max_chars': 2200, 'hashtag_limit': 30},
        'twitter': {'max_chars': 280, 'hashtag_limit': 5},
        'threads': {'max_chars': 500, 'hashtag_limit': 10},
        'facebook': {'max_chars': 8000, 'hashtag_limit': 10},
        'linkedin': {'max_chars': 3000, 'hashtag_limit': 5},
    }

    def __init__(self, mode: str = "professional"):
        """
        Initialize with a persona mode.

        Args:
            mode: "professional" (@swizzimatic) or "personal" (@BigSwizzi)
        """
        self._professional = SwizzimaticPersona()
        self._personal = BigSwizziPersona()
        self._mode = mode
        self._active = self._professional if mode == "professional" else self._personal

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str):
        """Switch between professional and personal voice."""
        if mode not in ("professional", "personal"):
            raise ValueError(f"Invalid mode: {mode}. Use 'professional' or 'personal'.")
        self._mode = mode
        self._active = self._professional if mode == "professional" else self._personal

    def get_active_persona(self) -> BasePersona:
        """Return the currently active persona instance."""
        return self._active

    # ─── Delegated methods ───

    def get_system_prompt(self, context_type: str = "casual") -> str:
        return self._active.get_system_prompt(context_type)

    def get_brand_voice(self) -> str:
        return self._active.get_brand_voice()

    def apply_vocab_transform(self, text: str) -> str:
        return self._active.apply_vocab_transform(text)

    def select_emojis(self, context: str, count: int = 1) -> List[str]:
        return self._active.select_emojis(context, count)

    def get_few_shot_examples(self, context_type: str, count: int = 3) -> List[str]:
        return self._active.get_few_shot_examples(context_type, count)

    def get_response_length_guide(self, context_type: str) -> Dict[str, int]:
        return self._active.get_response_length_guide(context_type)

    def get_tone_config(self) -> Dict[str, float]:
        return self._active.get_tone_config()

    # ─── Router-specific methods ───

    def determine_response_type(self, content: str, context: str = "") -> str:
        """
        Classify what type of response this should be.

        Returns: 'resource_share', 'casual', 'business', 'reaction', 'hype', 'acknowledgment'
        """
        content_lower = content.lower()

        # Resource/link sharing
        if any(w in content_lower for w in ['check', 'link', 'recommend', 'tool', 'service']):
            return 'resource_share'

        # Business context
        if any(w in content_lower for w in ['budget', 'price', 'client', 'project', 'deadline', 'contract']):
            return 'business'

        # Hype/excitement (BigSwizzi-style)
        if any(w in content_lower for w in ['fire', 'crazy', 'insane', 'amazing', 'incredible', 'goat']):
            return 'hype'

        # Quick reaction
        if len(content.split()) <= 5:
            return 'reaction' if self._mode == "personal" else 'acknowledgment'

        return 'casual'

    def get_platform_config(self, platform: str) -> Dict[str, Any]:
        """Get platform-specific constraints."""
        return self.PLATFORM_CONFIGS.get(
            platform.lower(),
            self.PLATFORM_CONFIGS['instagram']
        )


# ─── CLI Quick Test ───

if __name__ == "__main__":
    persona = SwizzPersona(mode="professional")

    print("=== SwizzimaticPersona (Professional) ===")
    print(f"Brand voice: {persona.get_brand_voice()[:80]}...")
    print(f"Vocab transform: 'Check your phone though' -> '{persona.apply_vocab_transform('Check your phone though')}'")
    print(f"Emojis (business): {persona.select_emojis('business', 2)}")
    print(f"Response type ('What is the budget?'): {persona.determine_response_type('What is the budget?')}")
    print()

    persona.set_mode("personal")

    print("=== BigSwizziPersona (Personal) ===")
    print(f"Brand voice: {persona.get_brand_voice()[:80]}...")
    print(f"Vocab transform: 'This is for them' -> '{persona.apply_vocab_transform('This is for them')}'")
    print(f"Emojis (approval_hype): {persona.select_emojis('approval_hype', 2)}")
    print(f"Response type ('This is fire'): {persona.determine_response_type('This is fire')}")
