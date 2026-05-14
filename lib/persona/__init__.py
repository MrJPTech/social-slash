#!/usr/bin/env python3
"""
Multi-Mode Voice Persona System

Three voice personas for social media content generation:
@swizzimatic (professional), @BigSwizzi (personal), and Jordan Ward (ceo).
"""

from lib.persona.instagram_parser import InstagramParser
from lib.persona.swizz_persona import (
    BasePersona,
    BigSwizziPersona,
    JordanWardPersona,
    SwizzimaticPersona,
    SwizzPersona,
)

__all__ = [
    "BasePersona",
    "SwizzimaticPersona",
    "BigSwizziPersona",
    "JordanWardPersona",
    "SwizzPersona",
    "InstagramParser",
]
