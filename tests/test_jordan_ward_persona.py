"""
Unit tests for Jordan Ward CEO persona.

Tests the JordanWardPersona class, SwizzPersona CEO mode routing,
content format prompts, and integration with the writing agent.
"""

import pytest
import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.persona.swizz_persona import (
    BasePersona,
    JordanWardPersona,
    SwizzPersona,
)


class TestJordanWardToneConfig:
    """Test CEO tone configuration values."""

    def setup_method(self):
        self.persona = JordanWardPersona()

    def test_tone_config_keys(self):
        """All required tone keys are present."""
        config = self.persona.get_tone_config()
        expected_keys = {'formality', 'verbosity', 'emoji_frequency', 'directness', 'enthusiasm', 'caps_emphasis'}
        assert set(config.keys()) == expected_keys

    def test_formality_is_high(self):
        """CEO voice is more formal than SWIZZ voices."""
        config = self.persona.get_tone_config()
        assert config['formality'] == 0.7

    def test_emoji_frequency_is_low(self):
        """CEO voice uses emojis sparingly."""
        config = self.persona.get_tone_config()
        assert config['emoji_frequency'] == 0.15

    def test_directness_is_high(self):
        """CEO voice is direct."""
        config = self.persona.get_tone_config()
        assert config['directness'] == 0.85

    def test_caps_emphasis_is_low(self):
        """CEO voice rarely uses caps for emphasis."""
        config = self.persona.get_tone_config()
        assert config['caps_emphasis'] == 0.02


class TestJordanWardVocabMap:
    """Test CEO vocabulary map excludes slang."""

    def setup_method(self):
        self.persona = JordanWardPersona()

    def test_vocab_map_has_entries(self):
        """Vocab map is not empty."""
        vocab = self.persona.get_vocab_map()
        assert len(vocab) > 0

    def test_no_shared_vocab_slang(self):
        """CEO vocab does NOT include SHARED_VOCAB slang contractions."""
        vocab = self.persona.get_vocab_map()
        shared_slang = {"gonna", "wanna", "gotta", "kinda", "sorta", "lemme", "gimme"}
        vocab_values = set(vocab.values())
        assert vocab_values.isdisjoint(shared_slang), (
            f"CEO vocab should not contain slang: {vocab_values & shared_slang}"
        )

    def test_polished_transforms(self):
        """Vocab transforms are polished/professional."""
        vocab = self.persona.get_vocab_map()
        assert vocab.get("I think") == "the data shows"
        assert vocab.get("stuff") == "systems"
        assert vocab.get("fix") == "optimize"

    def test_apply_vocab_transform(self):
        """Vocab transform applies correctly to text."""
        result = self.persona.apply_vocab_transform("I think we should fix the stuff")
        assert "the data shows" in result
        assert "optimize" in result
        assert "systems" in result


class TestJordanWardContentFormats:
    """Test all 7 CEO content formats."""

    def setup_method(self):
        self.persona = JordanWardPersona()

    def test_formats_defined(self):
        """All 8 content formats are defined (7 CEO + vibe_coder)."""
        expected = {
            'problem_solution', 'myth_busting', 'quick_tips',
            'day_in_life', 'case_study', 'industry_commentary', 'quick_wins',
            'vibe_coder',
        }
        assert set(self.persona.CONTENT_FORMATS.keys()) == expected

    def test_each_format_has_structure(self):
        """Each format defines a structure list."""
        for name, fmt in self.persona.CONTENT_FORMATS.items():
            assert 'structure' in fmt, f"{name} missing structure"
            assert isinstance(fmt['structure'], list), f"{name} structure is not a list"
            assert len(fmt['structure']) >= 3, f"{name} structure has fewer than 3 steps"

    def test_each_format_has_duration(self):
        """Each format defines a duration string."""
        for name, fmt in self.persona.CONTENT_FORMATS.items():
            assert 'duration' in fmt, f"{name} missing duration"
            assert 'seconds' in fmt['duration'], f"{name} duration doesn't mention seconds"

    def test_each_format_has_description(self):
        """Each format has a description."""
        for name, fmt in self.persona.CONTENT_FORMATS.items():
            assert 'description' in fmt, f"{name} missing description"
            assert len(fmt['description']) > 10, f"{name} description too short"

    def test_response_lengths_for_all_formats(self):
        """Each content format has matching response length config."""
        for name in self.persona.CONTENT_FORMATS:
            length = self.persona.RESPONSE_LENGTHS.get(name)
            assert length is not None, f"No response length for format '{name}'"
            assert 'min' in length and 'max' in length


class TestJordanWardSystemPrompt:
    """Test system prompt generation."""

    def setup_method(self):
        self.persona = JordanWardPersona()

    def test_system_prompt_contains_voice_rules(self):
        """System prompt includes evidence-based voice rules."""
        prompt = self.persona.get_system_prompt("business")
        assert "Jordan Ward" in prompt
        assert "evidence" in prompt.lower() or "data" in prompt.lower()
        assert "hook" in prompt.lower()
        assert "CTA" in prompt

    def test_system_prompt_includes_format_structure(self):
        """When context_type is a content format, structure is appended."""
        prompt = self.persona.get_system_prompt("problem_solution")
        assert "CONTENT FORMAT" in prompt
        assert "Structure:" in prompt
        assert "hook" in prompt.lower()

    def test_system_prompt_no_format_for_general_types(self):
        """General types like 'casual' don't get content format section."""
        prompt = self.persona.get_system_prompt("casual")
        assert "CONTENT FORMAT" not in prompt

    def test_system_prompt_never_rules(self):
        """System prompt includes NEVER rules for CEO voice."""
        prompt = self.persona.get_system_prompt("business")
        assert "NEVER" in prompt
        # Should not use slang
        assert "slang" in prompt.lower() or "gonna" in prompt.lower()


class TestJordanWardBrandVoice:
    """Test brand voice string."""

    def setup_method(self):
        self.persona = JordanWardPersona()

    def test_brand_voice_mentions_evidence(self):
        """Brand voice emphasizes evidence-based approach."""
        voice = self.persona.get_brand_voice()
        assert "evidence" in voice.lower() or "data" in voice.lower()

    def test_brand_voice_mentions_jordan(self):
        """Brand voice identifies as Jordan Ward."""
        voice = self.persona.get_brand_voice()
        assert "Jordan Ward" in voice

    def test_brand_voice_mentions_prsmtech(self):
        """Brand voice references PRSMTECH."""
        voice = self.persona.get_brand_voice()
        assert "PRSMTECH" in voice


class TestJordanWardExamples:
    """Test few-shot examples for each format."""

    def setup_method(self):
        self.persona = JordanWardPersona()

    def test_examples_exist_for_general_types(self):
        """Examples exist for casual, business, thought_leadership."""
        for ctx in ['casual', 'business', 'thought_leadership']:
            examples = self.persona.get_few_shot_examples(ctx, count=3)
            assert len(examples) > 0, f"No examples for '{ctx}'"

    def test_examples_exist_for_all_formats(self):
        """Examples exist for all 7 content formats."""
        for fmt in self.persona.CONTENT_FORMATS:
            examples = self.persona.get_few_shot_examples(fmt, count=1)
            assert len(examples) > 0, f"No examples for format '{fmt}'"

    def test_examples_contain_specifics(self):
        """Examples include numbers/metrics (evidence-based voice)."""
        # Check a few key format examples for numbers
        for fmt in ['problem_solution', 'case_study', 'myth_busting']:
            examples = self.persona.get_few_shot_examples(fmt, count=1)
            text = examples[0]
            has_number = any(c.isdigit() for c in text)
            assert has_number, f"Example for '{fmt}' should contain numbers/metrics"


class TestJordanWardContentFormatPrompt:
    """Test get_content_format_prompt method."""

    def setup_method(self):
        self.persona = JordanWardPersona()

    def test_returns_prompt_for_valid_format(self):
        """Returns structured prompt for valid format."""
        prompt = self.persona.get_content_format_prompt("problem_solution", "Tech debt costs")
        assert prompt is not None
        assert "Tech debt costs" in prompt
        assert "problem_solution" in prompt.lower().replace("_", "_") or "problem solution" in prompt.lower()

    def test_returns_none_for_invalid_format(self):
        """Returns None for unrecognized format name."""
        result = self.persona.get_content_format_prompt("nonexistent_format", "topic")
        assert result is None

    def test_prompt_includes_structure(self):
        """Prompt includes numbered structure steps."""
        prompt = self.persona.get_content_format_prompt("myth_busting", "AI hype")
        assert "1." in prompt
        assert "2." in prompt

    def test_all_formats_produce_prompts(self):
        """All 7 formats produce non-None prompts."""
        for fmt in self.persona.CONTENT_FORMATS:
            prompt = self.persona.get_content_format_prompt(fmt, "test topic")
            assert prompt is not None, f"Format '{fmt}' returned None"
            assert len(prompt) > 100, f"Format '{fmt}' prompt too short"


class TestJordanWardEmojiMap:
    """Test CEO emoji context map."""

    def setup_method(self):
        self.persona = JordanWardPersona()

    def test_business_appropriate_contexts(self):
        """Emoji map has business-appropriate contexts."""
        emoji_map = self.persona.get_emoji_map()
        expected_contexts = {'business', 'tech', 'success', 'growth', 'insight', 'cta'}
        assert expected_contexts.issubset(set(emoji_map.keys()))

    def test_select_emojis(self):
        """Can select emojis from business context."""
        emojis = self.persona.select_emojis('business', count=2)
        assert len(emojis) == 2
        assert all(isinstance(e, str) for e in emojis)


class TestSwizzPersonaCEOMode:
    """Test SwizzPersona router accepts and routes CEO mode."""

    def test_init_with_ceo_mode(self):
        """Can initialize SwizzPersona with 'ceo' mode."""
        persona = SwizzPersona(mode="ceo")
        assert persona.mode == "ceo"
        assert isinstance(persona.get_active_persona(), JordanWardPersona)

    def test_set_mode_ceo(self):
        """Can switch to ceo mode."""
        persona = SwizzPersona(mode="professional")
        persona.set_mode("ceo")
        assert persona.mode == "ceo"
        assert isinstance(persona.get_active_persona(), JordanWardPersona)

    def test_set_mode_invalid_raises(self):
        """Invalid mode raises ValueError."""
        persona = SwizzPersona()
        with pytest.raises(ValueError, match="Invalid mode"):
            persona.set_mode("invalid")

    def test_ceo_delegates_system_prompt(self):
        """CEO mode delegates get_system_prompt to JordanWardPersona."""
        persona = SwizzPersona(mode="ceo")
        prompt = persona.get_system_prompt("business")
        assert "Jordan Ward" in prompt

    def test_ceo_delegates_brand_voice(self):
        """CEO mode delegates get_brand_voice to JordanWardPersona."""
        persona = SwizzPersona(mode="ceo")
        voice = persona.get_brand_voice()
        assert "Jordan Ward" in voice

    def test_ceo_delegates_vocab_transform(self):
        """CEO mode applies CEO vocab transforms."""
        persona = SwizzPersona(mode="ceo")
        result = persona.apply_vocab_transform("I think the stuff is bad")
        assert "the data shows" in result
        assert "systems" in result
        assert "ineffective" in result

    def test_switch_between_all_three_modes(self):
        """Can switch between all three modes."""
        persona = SwizzPersona(mode="professional")
        assert "SWIZZ" in persona.get_brand_voice()

        persona.set_mode("personal")
        assert "Big Swizzi" in persona.get_brand_voice()

        persona.set_mode("ceo")
        assert "Jordan Ward" in persona.get_brand_voice()

        persona.set_mode("professional")
        assert "SWIZZ" in persona.get_brand_voice()


class TestSwizzPersonaCEOResponseRouting:
    """Test determine_response_type routes CEO keywords correctly."""

    def setup_method(self):
        self.persona = SwizzPersona(mode="ceo")

    def test_problem_solution_detection(self):
        """Detects problem_solution keywords."""
        assert self.persona.determine_response_type("The cost of tech debt is a problem") == "problem_solution"

    def test_myth_busting_detection(self):
        """Detects myth_busting keywords."""
        assert self.persona.determine_response_type("The myth about enterprise software") == "myth_busting"

    def test_quick_tips_detection(self):
        """Detects quick_tips keywords."""
        assert self.persona.determine_response_type("3 tips for scaling your startup") == "quick_tips"

    def test_day_in_life_detection(self):
        """Detects day_in_life keywords."""
        assert self.persona.determine_response_type("A day in the life of a tech CEO") == "day_in_life"

    def test_case_study_detection(self):
        """Detects case_study keywords."""
        assert self.persona.determine_response_type("Case study: how we helped a client") == "case_study"

    def test_industry_commentary_detection(self):
        """Detects industry_commentary keywords."""
        assert self.persona.determine_response_type("The latest industry trend in AI") == "industry_commentary"

    def test_quick_wins_detection(self):
        """Detects quick_wins keywords."""
        assert self.persona.determine_response_type("A quick win for your dev team") == "quick_wins"

    def test_default_thought_leadership(self):
        """Unmatched content defaults to thought_leadership in CEO mode."""
        assert self.persona.determine_response_type("Leadership is about making decisions") == "thought_leadership"

    def test_non_ceo_mode_ignores_ceo_keywords(self):
        """Professional mode does NOT route to CEO formats."""
        persona = SwizzPersona(mode="professional")
        # "myth" would trigger myth_busting in CEO mode, but not in professional
        result = persona.determine_response_type("The myth about budgets")
        assert result != "myth_busting"


class TestJordanWardIsBasePersona:
    """Test JordanWardPersona properly implements BasePersona."""

    def test_is_subclass(self):
        """JordanWardPersona is a BasePersona subclass."""
        assert issubclass(JordanWardPersona, BasePersona)

    def test_all_abstract_methods_implemented(self):
        """Can instantiate (all abstract methods implemented)."""
        persona = JordanWardPersona()
        assert persona is not None

    def test_get_response_length_guide_returns_dict(self):
        """get_response_length_guide returns dict with min/max."""
        persona = JordanWardPersona()
        guide = persona.get_response_length_guide("business")
        assert isinstance(guide, dict)
        assert 'min' in guide
        assert 'max' in guide
        assert guide['min'] < guide['max']

    def test_unknown_context_falls_back_to_business(self):
        """Unknown context type falls back to business defaults."""
        persona = JordanWardPersona()
        guide = persona.get_response_length_guide("nonexistent_type")
        assert guide == persona.RESPONSE_LENGTHS['business']
