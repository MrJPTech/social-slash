#!/usr/bin/env python3
"""
Content Curator Agent

Intelligence layer between personal curation and public content.
When Jordan screenshots something, saves an article, or has an idea,
this agent figures out:

- WHY it resonates with his brand/story (the Jordan Ward angle)
- Which content format fits best (bridge_builder, real_talk, ask_the_audience, etc.)
- How to frame it for his audience (accessible, educational, never bragging)
- What trending context connects to it
- Draft posts in his voice across platforms

This is NOT a file upload tool. This is the brain that turns
"I found something interesting" into "here's what to post about it."
"""

from typing import Any

from lib.persona.swizz_persona import SwizzPersona


class ContentCurator:
    """
    Content intelligence agent for Jordan Ward's social presence.

    Takes raw input (a description of something Jordan found valuable)
    and produces content strategy + drafts through his persona lens.
    """

    # Maps content characteristics to best CEO formats
    FORMAT_SIGNALS = {
        "bridge_builder": {
            "signals": [
                "everyday use",
                "anyone can",
                "simple",
                "accessible",
                "small business",
                "non-technical",
                "regular people",
                "save time",
                "save money",
                "practical",
                "real world",
                "barber",
                "restaurant",
                "aunt",
                "uncle",
                "neighbor",
            ],
            "description": "Make tech accessible to everyday people",
            "when": "Content shows how AI/tech helps normal people — not just developers",
        },
        "real_talk": {
            "signals": [
                "personal",
                "story",
                "lesson",
                "grew up",
                "experience",
                "changed",
                "perspective",
                "journey",
                "struggle",
                "growth",
                "reinvent",
                "rebuild",
                "faith",
                "grateful",
                "humble",
            ],
            "description": "Personal story tied to a lesson",
            "when": "Content connects to Jordan's real life — Novi, videography, reinvention, faith",
        },
        "ask_the_audience": {
            "signals": [
                "question",
                "opinion",
                "debate",
                "controversial",
                "poll",
                "what would you",
                "agree or disagree",
                "hot take",
                "unpopular opinion",
                "discussion",
                "thoughts",
            ],
            "description": "Question-first format that starts discussion",
            "when": "Content sparks a question or debate worth having publicly",
        },
        "problem_solution": {
            "signals": [
                "problem",
                "solution",
                "fix",
                "broken",
                "inefficient",
                "waste",
                "cost",
                "expensive",
                "manual",
                "automate",
            ],
            "description": "Show the problem, then show the fix",
            "when": "Content reveals a pain point that AI/tech solves",
        },
        "myth_busting": {
            "signals": [
                "myth",
                "wrong",
                "misconception",
                "actually",
                "truth",
                "people think",
                "assume",
                "overrated",
                "underrated",
            ],
            "description": "Challenge a common misconception",
            "when": "Content contradicts popular belief or conventional wisdom",
        },
        "quick_tips": {
            "signals": [
                "tips",
                "list",
                "steps",
                "ways",
                "rules",
                "lessons",
                "hack",
                "shortcut",
                "framework",
                "checklist",
            ],
            "description": "Actionable list of tips people can use immediately",
            "when": "Content distills into clear, numbered takeaways",
        },
        "industry_commentary": {
            "signals": [
                "trend",
                "industry",
                "market",
                "prediction",
                "future",
                "shift",
                "disruption",
                "competition",
                "landscape",
                "announcement",
                "launch",
                "acquisition",
                "funding",
            ],
            "description": "Jordan's take on what's happening in tech/AI",
            "when": "Content is about industry news or trends worth commenting on",
        },
        "vibe_coder": {
            "signals": [
                "code",
                "built",
                "shipped",
                "commit",
                "deploy",
                "cli",
                "terminal",
                "dev",
                "programming",
                "self-taught",
                "no degree",
                "learned",
                "stack",
                "framework",
            ],
            "description": "Show the build process — self-taught dev energy",
            "when": "Content is about building, coding, or the dev journey",
        },
        "case_study": {
            "signals": [
                "client",
                "results",
                "before after",
                "transformation",
                "roi",
                "outcome",
                "delivered",
                "project",
                "built for",
            ],
            "description": "Show real results without bragging",
            "when": "Content demonstrates real impact from real work",
        },
        "day_in_life": {
            "signals": [
                "morning",
                "routine",
                "behind the scenes",
                "day",
                "workflow",
                "setup",
                "workspace",
                "process",
            ],
            "description": "Pull back the curtain on CEO/dev life",
            "when": "Content shows the actual work, not just the results",
        },
    }

    # Jordan's story anchors — real experiences to reference
    STORY_ANCHORS = {
        "suburban_outsider": "Grew up in Novi MI — rich suburb, did his own thing (skateboarding, snowboarding) while everyone else followed the expected path",
        "videography_perspective": "Shot music videos for rappers across America (Opa Locka, Little Haiti, Memphis, Bronx, Detroit) — seeing all those perspectives changed everything",
        "reinvention": "Last 7 years: rapper, videographer, personality. Last 1.5 years: locked in on AI, Python, automation. Sat down, understood himself, rebuilt",
        "faith": "Christian — no God complex (there's only one God). Humbled by lessons. Grateful for opportunities. God is Good",
        "mission": "Give everybody an opportunity. AI shouldn't only advance a certain class of people. Be the AI foundation for people who don't have access",
        "ted_proof": "Tutored a kid at 17 whose dad is near-billionaire. Met the family again a year ago. Now closing $20K+ deal. Authenticity compounds",
        "accessibility": "Tech shouldn't depend on your zip code. Some people want the wrong things because that's all they see or feel capable of",
    }

    def __init__(self, persona_mode: str = "ceo"):
        """
        Initialize the content curator.

        Args:
            persona_mode: Voice mode (usually "ceo" for Jordan Ward)
        """
        self.persona = SwizzPersona(mode=persona_mode)
        self._ceo = self.persona._ceo if persona_mode == "ceo" else None

    def curate(
        self,
        description: str,
        context: str = "",
        platforms: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Full curation pipeline: take raw input, return content strategy.

        Args:
            description: What Jordan found valuable (screenshot description,
                        article summary, observation, idea)
            context: Additional context (where he saw it, why it caught his eye)
            platforms: Target platforms (default: linkedin, twitter, instagram)

        Returns:
            Dict with angle, suggested_formats, story_connections,
            trending_hooks, and draft_angles
        """
        if platforms is None:
            platforms = ["linkedin", "twitter", "instagram"]

        # 1. Analyze the angle through Jordan's lens
        angle = self.analyze_angle(description, context)

        # 2. Suggest best content formats
        formats = self.suggest_formats(description)

        # 3. Find story connections (what from Jordan's life connects)
        story_connections = self._find_story_connections(description)

        # 4. Generate content angles for each format
        draft_angles = []
        top_format = formats[0]["format"] if formats else "bridge_builder"
        for platform in platforms:
            draft_angles.append(
                {
                    "platform": platform,
                    "format": top_format,
                    "angle": self._generate_angle(description, top_format, platform, context),
                }
            )

        return {
            "input": description,
            "context": context,
            "angle": angle,
            "suggested_formats": formats[:3],
            "story_connections": story_connections,
            "draft_angles": draft_angles,
            "platforms": platforms,
        }

    def analyze_angle(
        self,
        description: str,
        context: str = "",
    ) -> dict[str, Any]:
        """
        Determine the Jordan Ward angle on this content.

        Answers: WHY does this matter through Jordan's lens?
        How does his background make him uniquely positioned to talk about this?

        Args:
            description: What was found
            context: Why it caught his eye

        Returns:
            Dict with why_it_matters, jordan_connection, audience_value, tone_suggestion
        """
        desc_lower = description.lower()

        # Determine core theme
        themes = []
        if any(w in desc_lower for w in ["ai", "tech", "tool", "software", "app", "automate"]):
            themes.append("technology")
        if any(
            w in desc_lower for w in ["business", "startup", "revenue", "client", "money", "hustle"]
        ):
            themes.append("business")
        if any(
            w in desc_lower for w in ["learn", "school", "education", "teach", "student", "access"]
        ):
            themes.append("education_access")
        if any(w in desc_lower for w in ["community", "help", "people", "neighborhood", "impact"]):
            themes.append("community")
        if any(w in desc_lower for w in ["creative", "video", "music", "art", "design", "content"]):
            themes.append("creative")
        if any(w in desc_lower for w in ["faith", "god", "blessed", "grateful", "prayer"]):
            themes.append("faith")
        if any(w in desc_lower for w in ["grow", "change", "reinvent", "pivot", "rebuild"]):
            themes.append("reinvention")

        if not themes:
            themes.append("general")

        # Find the strongest Jordan connection
        connection = self._find_strongest_connection(desc_lower, themes)

        # Determine audience value
        audience_value = self._assess_audience_value(desc_lower, themes)

        # Suggest tone
        tone = self._suggest_tone(themes)

        return {
            "themes": themes,
            "why_it_matters": f"This connects to {', '.join(themes)} — core to Jordan's mission of making tech accessible and helping people see what's possible.",
            "jordan_connection": connection,
            "audience_value": audience_value,
            "tone_suggestion": tone,
        }

    def suggest_formats(
        self,
        description: str,
    ) -> list[dict[str, Any]]:
        """
        Rank which content formats best fit this content.

        Args:
            description: Content description

        Returns:
            List of format suggestions, ranked by fit score
        """
        desc_lower = description.lower()
        scored = []

        for fmt, config in self.FORMAT_SIGNALS.items():
            # Count signal matches
            matches = sum(1 for s in config["signals"] if s in desc_lower)
            score = matches / len(config["signals"]) if config["signals"] else 0

            # Bonus for strong matches (3+ signals)
            if matches >= 3:
                score += 0.2

            scored.append(
                {
                    "format": fmt,
                    "score": round(min(score, 1.0), 2),
                    "matches": matches,
                    "description": config["description"],
                    "when": config["when"],
                }
            )

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)

        # Always return at least bridge_builder as fallback if nothing scores high
        if scored[0]["score"] == 0:
            # Default to bridge_builder for accessibility-first content
            for item in scored:
                if item["format"] == "bridge_builder":
                    item["score"] = 0.1
                    item["reason"] = "Default: when in doubt, make it accessible"
                    break
            scored.sort(key=lambda x: x["score"], reverse=True)

        return scored

    def _find_story_connections(self, description: str) -> list[dict[str, str]]:
        """Find which parts of Jordan's story connect to this content."""
        desc_lower = description.lower()
        connections = []

        # Technology/AI access → mission + accessibility
        if any(w in desc_lower for w in ["ai", "tech", "tool", "access", "opportunity"]):
            connections.append(
                {
                    "anchor": "mission",
                    "story": self.STORY_ANCHORS["mission"],
                    "connection": "This is exactly what PRSMTECH exists for — getting these tools to people who need them",
                }
            )

        # Seeing different perspectives → videography
        if any(
            w in desc_lower
            for w in [
                "perspective",
                "different",
                "community",
                "neighborhood",
                "environment",
                "culture",
            ]
        ):
            connections.append(
                {
                    "anchor": "videography_perspective",
                    "story": self.STORY_ANCHORS["videography_perspective"],
                    "connection": "Jordan's videography work across America gave him this exact lens",
                }
            )

        # Reinvention / learning / growth → reinvention
        if any(
            w in desc_lower
            for w in ["learn", "grow", "change", "reinvent", "self-taught", "pivot", "career"]
        ):
            connections.append(
                {
                    "anchor": "reinvention",
                    "story": self.STORY_ANCHORS["reinvention"],
                    "connection": "Jordan lived this — rapper to CEO to full-stack dev",
                }
            )

        # Business / relationships / trust → ted_proof
        if any(
            w in desc_lower
            for w in ["relationship", "client", "trust", "authentic", "long-term", "compound"]
        ):
            connections.append(
                {
                    "anchor": "ted_proof",
                    "story": self.STORY_ANCHORS["ted_proof"],
                    "connection": "A longtime client relationship proves this — authenticity over years compounds into real business",
                }
            )

        # Standing out / doing your own thing → suburban_outsider
        if any(
            w in desc_lower
            for w in ["different", "stand out", "unique", "own path", "unconventional", "versatile"]
        ):
            connections.append(
                {
                    "anchor": "suburban_outsider",
                    "story": self.STORY_ANCHORS["suburban_outsider"],
                    "connection": "Jordan was the skateboarding kid in a suburb where everybody hooped — he knows about standing out",
                }
            )

        # Inequality / access gaps → accessibility
        if any(
            w in desc_lower
            for w in ["inequality", "gap", "underserved", "funding", "zip code", "privilege"]
        ):
            connections.append(
                {
                    "anchor": "accessibility",
                    "story": self.STORY_ANCHORS["accessibility"],
                    "connection": "Tech access shouldn't depend on your zip code — this is the fight",
                }
            )

        # Faith / gratitude → faith
        if any(
            w in desc_lower for w in ["faith", "god", "blessed", "grateful", "humble", "prayer"]
        ):
            connections.append(
                {
                    "anchor": "faith",
                    "story": self.STORY_ANCHORS["faith"],
                    "connection": "Central to who Jordan is — genuine, not performative",
                }
            )

        return connections

    def _find_strongest_connection(self, desc_lower: str, themes: list[str]) -> str:
        """Determine the strongest connection to Jordan's story."""
        if "education_access" in themes or "community" in themes:
            return "Jordan's mission: AI shouldn't only advance a certain class of people. He's been to neighborhoods where people don't have access to these tools."
        if "technology" in themes:
            return "Self-taught dev who went from rapper/videographer to building AI tools. He makes tech feel approachable because he came from outside the tech world."
        if "business" in themes:
            return "CEO who learned business by doing — shooting videos in people's hometowns, building relationships that compound over years."
        if "creative" in themes:
            return "Built Swizzimatic videography from scratch, shot videos across America. Creativity is in the DNA."
        if "reinvention" in themes:
            return "Living proof of reinvention — rapper to videographer to CEO to full-stack dev. Not Superman, just someone who sat down and rebuilt."
        if "faith" in themes:
            return "Faith is core identity. No God complex — there's only one God. Humbled by lessons, grateful for opportunities."
        return "Jordan's versatility — got along with everybody in Novi (jocks, gamers, hoopers, alternative kids) and still does. Connects across worlds."

    def _assess_audience_value(self, desc_lower: str, themes: list[str]) -> str:
        """Determine what value this gives Jordan's audience."""
        if "education_access" in themes:
            return "Shows people that these tools are for THEM — not just Silicon Valley engineers"
        if "technology" in themes:
            return (
                "Makes AI/tech feel doable. Your aunt could use this. Your barber could use this."
            )
        if "business" in themes:
            return "Real business lessons from someone who's building — not theoretical, proven"
        if "reinvention" in themes:
            return "Inspiration with substance — not motivational poster energy, real examples of rebuilding"
        if "community" in themes:
            return "Shows what's possible when someone bridges the gap between tech and community"
        if "creative" in themes:
            return "Creative process and tools that everyday creators can actually use"
        return "Real perspective from someone who's seen both sides — suburbs and the streets through work"

    def _suggest_tone(self, themes: list[str]) -> str:
        """Suggest the right tone based on content themes."""
        if "faith" in themes:
            return "authentic"
        if "education_access" in themes or "community" in themes:
            return "educational"
        if "reinvention" in themes:
            return "reflective"
        if "business" in themes:
            return "direct"
        if "creative" in themes:
            return "inspiring"
        return "authentic"

    def _generate_angle(
        self,
        description: str,
        format_type: str,
        platform: str,
        context: str = "",
    ) -> str:
        """
        Generate a specific content angle for a platform.

        This is the hook + framing, not the full post.
        """
        active = self.persona.get_active_persona()
        format_config = active.CONTENT_FORMATS.get(format_type, {})
        structure = format_config.get("structure", [])

        # Build the angle based on format structure
        if format_type == "bridge_builder":
            return (
                f"ANGLE: Show how this is for everybody, not just tech people.\n"
                f"HOOK: Start with an everyday person who could use this.\n"
                f"STRUCTURE: {' → '.join(structure)}\n"
                f"KEY: Make the audience feel like AI is for THEM."
            )
        elif format_type == "real_talk":
            connections = self._find_story_connections(description)
            story_ref = connections[0]["story"] if connections else "Connect to your journey"
            return (
                f"ANGLE: Tie this to a personal experience.\n"
                f"STORY HOOK: {story_ref}\n"
                f"STRUCTURE: {' → '.join(structure)}\n"
                f"KEY: Share the lesson, not just the story."
            )
        elif format_type == "ask_the_audience":
            return (
                f"ANGLE: Lead with a question that makes people stop and think.\n"
                f"HOOK: Ask something people have an opinion on but rarely get asked.\n"
                f"STRUCTURE: {' → '.join(structure)}\n"
                f"KEY: Make it easy to answer. Engagement comes from low-friction responses."
            )
        elif format_type == "problem_solution":
            return (
                f"ANGLE: Show the pain first, then the fix.\n"
                f"HOOK: Start with a problem the audience recognizes.\n"
                f"STRUCTURE: {' → '.join(structure)}\n"
                f"KEY: Be specific about the solution — show, don't just tell."
            )
        elif format_type == "vibe_coder":
            return (
                f"ANGLE: Show the build. Self-taught energy.\n"
                f"HOOK: Lead with what you're building or what you just shipped.\n"
                f"STRUCTURE: {' → '.join(structure)}\n"
                f"KEY: Make coding feel accessible — no CS degree required."
            )
        elif format_type == "industry_commentary":
            return (
                f"ANGLE: Jordan's take on what's happening.\n"
                f"HOOK: Lead with the trend/news, then give your perspective.\n"
                f"STRUCTURE: {' → '.join(structure)}\n"
                f"KEY: Have a real opinion. Don't just report — react."
            )
        else:
            return (
                f"ANGLE: Frame through Jordan's lens — accessible, educational, real.\n"
                f"FORMAT: {format_type}\n"
                f"STRUCTURE: {' → '.join(structure) if structure else 'hook → body → cta'}\n"
                f"KEY: Make the audience feel capable, not overwhelmed."
            )


def main():
    """CLI entry point for content curation."""
    import argparse

    parser = argparse.ArgumentParser(description="Content Curator — Jordan Ward Intelligence Layer")
    parser.add_argument(
        "--action",
        choices=["curate", "angle", "formats"],
        default="curate",
        help="Action to perform",
    )
    parser.add_argument(
        "--description",
        "-d",
        type=str,
        required=True,
        help="What you found (screenshot description, article, idea)",
    )
    parser.add_argument("--context", "-c", type=str, default="", help="Why it caught your eye")
    parser.add_argument(
        "--platforms",
        "-p",
        type=str,
        nargs="+",
        default=["linkedin", "twitter", "instagram"],
        help="Target platforms",
    )

    args = parser.parse_args()

    curator = ContentCurator(persona_mode="ceo")

    if args.action == "curate":
        result = curator.curate(args.description, args.context, args.platforms)

        print("\n" + "=" * 70)
        print("  CONTENT CURATION — Jordan Ward Lens")
        print("=" * 70)

        print(f"\n  INPUT: {result['input']}")
        if result["context"]:
            print(f"  CONTEXT: {result['context']}")

        # Angle
        angle = result["angle"]
        print(f"\n  THEMES: {', '.join(angle['themes'])}")
        print(f"  WHY IT MATTERS: {angle['why_it_matters']}")
        print(f"  JORDAN CONNECTION: {angle['jordan_connection']}")
        print(f"  AUDIENCE VALUE: {angle['audience_value']}")
        print(f"  TONE: {angle['tone_suggestion']}")

        # Formats
        print("\n  BEST FORMATS:")
        for i, fmt in enumerate(result["suggested_formats"], 1):
            print(f"    {i}. {fmt['format']} (score: {fmt['score']})")
            print(f"       {fmt['description']}")
            print(f"       When: {fmt['when']}")

        # Story connections
        if result["story_connections"]:
            print("\n  STORY CONNECTIONS:")
            for conn in result["story_connections"]:
                print(f"    [{conn['anchor']}] {conn['connection']}")

        # Draft angles
        print("\n  DRAFT ANGLES:")
        for draft in result["draft_angles"]:
            print(f"\n    [{draft['platform'].upper()}] Format: {draft['format']}")
            for line in draft["angle"].split("\n"):
                print(f"      {line}")

        print("\n" + "=" * 70)

    elif args.action == "angle":
        result = curator.analyze_angle(args.description, args.context)
        print(f"\nThemes: {', '.join(result['themes'])}")
        print(f"Why: {result['why_it_matters']}")
        print(f"Connection: {result['jordan_connection']}")
        print(f"Value: {result['audience_value']}")
        print(f"Tone: {result['tone_suggestion']}")

    elif args.action == "formats":
        results = curator.suggest_formats(args.description)
        print("\nFormat Rankings:")
        for i, fmt in enumerate(results[:5], 1):
            print(f"  {i}. {fmt['format']} — score: {fmt['score']} ({fmt['matches']} matches)")
            print(f"     {fmt['description']}")


if __name__ == "__main__":
    main()
