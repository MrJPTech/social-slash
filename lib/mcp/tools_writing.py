"""Writing agent tools — post, caption, and thread generation in SWIZZ/CEO voice."""

from __future__ import annotations

from ._client_helpers import build_agent_config, suppress_stdout
from ._shared import mcp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_writing_agent(persona_mode: str = "professional", platform: str = "instagram"):
    """Create a WritingAgent with stdout suppression."""
    with suppress_stdout():
        from lib.agents.writing_agent import WritingAgent

        config = build_agent_config(persona_mode, platform)
        return WritingAgent(config)


def _persona_label(persona_mode: str) -> str:
    """Return the display handle for a persona mode."""
    return {"professional": "@swizzimatic", "personal": "@BigSwizzi", "ceo": "Jordan Ward"}.get(
        persona_mode, persona_mode
    )


def _format_post_result(result: dict) -> str:
    """Format a generate_post result dict as clean readable markdown."""
    platform = result.get("platform", "unknown").title()
    persona = _persona_label(result.get("persona_mode", "professional"))
    post_type = result.get("post_type", "casual").replace("_", " ").title()
    tone = result.get("tone", "authentic").title()
    energy = result.get("energy", "medium").title()
    char_count = result.get("char_count", 0)
    char_limit = result.get("char_limit", 2200)
    headroom = char_limit - char_count
    content = result.get("content", "")
    hashtags = result.get("hashtags", [])
    emojis = result.get("emojis", [])

    lines = [
        f"**Platform**: {platform} | **Persona**: {persona} | **Type**: {post_type}",
        f"**Tone**: {tone} | **Energy**: {energy} | **Length**: {char_count}/{char_limit} ({headroom} chars left)",
        "",
        "---",
        "",
        content,
        "",
        "---",
    ]
    if hashtags:
        lines.append(f"**Hashtags**: {' '.join(hashtags)}")
    if emojis:
        lines.append(f"**Emojis**: {' '.join(emojis)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def writing_generate_post(
    topic: str,
    platform: str = "instagram",
    post_type: str = "casual",
    persona_mode: str = "professional",
    tone: str = "authentic",
    energy: str = "medium",
) -> str:
    """Generate a social media post in the SWIZZ or CEO voice.

    Args:
        topic: What the post should be about
        platform: Target platform (instagram, twitter, linkedin, tiktok, youtube, reddit, etc.)
        post_type: Style - casual, announcement, resource_share, business, promo, hype,
                   or CEO formats: problem_solution, myth_busting, quick_tips, day_in_life,
                   case_study, industry_commentary, quick_wins, vibe_coder
                   Use "auto" to detect best type from topic keywords.
        persona_mode: professional (swizzimatic), personal (bigswizzi), or ceo (jordan ward)
        tone: Emotional tone - authentic, motivational, humorous, reflective, educational,
              hype, emotional, direct, raw, inspiring
        energy: Energy level - low (calm/measured), medium (balanced), high (bold/loud)
    """
    try:
        # Auto-detect post_type from topic keywords when "auto" is passed
        resolved_post_type = post_type
        if post_type == "auto":
            with suppress_stdout():
                from lib.persona.swizz_persona import SwizzPersona

                router = SwizzPersona(mode=persona_mode)
                resolved_post_type = router.determine_response_type(topic)

        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            result = agent.generate_post(
                topic=topic,
                platform=platform,
                post_type=resolved_post_type,
                persona_mode=persona_mode,
                tone=tone,
                energy=energy,
            )
        return _format_post_result(result)
    except Exception as e:
        return f"Error generating post: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def writing_generate_caption(
    media_description: str,
    platform: str = "instagram",
    persona_mode: str = "professional",
    tone: str = "authentic",
    energy: str = "medium",
) -> str:
    """Generate a caption for media content in SWIZZ or CEO voice.

    Args:
        media_description: What the photo/video shows
        platform: Target platform
        persona_mode: professional, personal, or ceo
        tone: Emotional tone - authentic, motivational, humorous, hype, emotional, direct, raw
        energy: Energy level - low, medium, high
    """
    try:
        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            result = agent.generate_post(
                topic=f"Caption for this media: {media_description}",
                platform=platform,
                post_type="casual",
                persona_mode=persona_mode,
                tone=tone,
                energy=energy,
            )
        content = result.get("content", "")
        char_count = result.get("char_count", 0)
        char_limit = result.get("char_limit", 2200)
        persona = _persona_label(persona_mode)
        hashtags = result.get("hashtags", [])
        out = [
            f"**Caption** | {persona} | {platform.title()} | {char_count}/{char_limit} chars",
            "",
            content,
        ]
        if hashtags:
            out.append(f"\n**Hashtags**: {' '.join(hashtags)}")
        return "\n".join(out)
    except Exception as e:
        return f"Error generating caption: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def writing_generate_thread(
    topic: str,
    platform: str = "twitter",
    num_posts: int = 3,
    persona_mode: str = "professional",
    tone: str = "authentic",
    energy: str = "medium",
) -> str:
    """Generate a multi-post thread in SWIZZ or CEO voice.

    Args:
        topic: Thread topic
        platform: Target platform (twitter/threads recommended)
        num_posts: Number of posts in thread (2-10)
        persona_mode: professional, personal, or ceo
        tone: Emotional tone - authentic, motivational, humorous, educational, hype, direct
        energy: Energy level - low, medium, high
    """
    try:
        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            posts = agent.generate_thread(
                topic=topic,
                platform=platform,
                num_posts=num_posts,
                persona_mode=persona_mode,
                tone=tone,
                energy=energy,
            )
        if not posts:
            return "No posts generated. Try a different topic."

        persona = _persona_label(persona_mode)
        char_limit = posts[0].get("char_limit", 280) if posts else 280
        lines = [
            f"**Thread**: {len(posts)} posts | **Platform**: {platform.title()} | **Persona**: {persona}",
            f"**Tone**: {tone.title()} | **Energy**: {energy.title()} | **Limit**: {char_limit} chars/post",
            "",
        ]
        for i, post in enumerate(posts, 1):
            lines.append(f"**{i}/{len(posts)}** ({post['char_count']} chars)")
            lines.append(post["content"])
            if i < len(posts):
                lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error generating thread: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."
