#!/usr/bin/env python3
"""
SWIZZ Voice Persona System

Dual-mode persona configuration for social media content generation.
Captures speech patterns and voice style from @swizzimatic (professional)
and @BigSwizzi (personal) Instagram accounts.
"""

from lib.persona.swizz_persona import (
    BasePersona,
    SwizzimaticPersona,
    BigSwizziPersona,
    SwizzPersona,
)
from lib.persona.instagram_parser import InstagramParser

__all__ = [
    'BasePersona',
    'SwizzimaticPersona',
    'BigSwizziPersona',
    'SwizzPersona',
    'InstagramParser',
]
