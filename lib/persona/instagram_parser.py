#!/usr/bin/env python3
"""
Instagram Export Parser for Speech Pattern Extraction

Parses Instagram data export JSON files to extract speech patterns,
vocabulary usage, emoji frequency, and response style metrics.
This is a one-time data extraction utility, NOT a runtime component.

Usage:
    python -m lib.persona.instagram_parser --path /path/to/instagram/export
"""

import json
import os
import re
from collections import Counter
from typing import Dict, Any, List, Optional
from pathlib import Path


class InstagramParser:
    """
    Parser for extracting speech patterns from Instagram data export.

    Analyzes message conversations to extract:
    - Vocabulary patterns (contractions, slang frequency)
    - Emoji usage patterns and frequency
    - Response length distributions
    - Address terms (gang, twin, fam, etc.)
    - Agreement patterns (bet, fasho, say less, etc.)
    """

    def __init__(self, base_path: str):
        """
        Initialize parser with path to Instagram export directory.

        Args:
            base_path: Path to Instagram data export root
        """
        self.base_path = Path(base_path)
        self.messages: List[Dict[str, Any]] = []
        self.owner_messages: List[str] = []
        self._parsed = False

    def parse_conversations(self, limit: int = 0) -> List[Dict[str, Any]]:
        """
        Extract messages from inbox/*/message_*.json files.

        Args:
            limit: Max conversations to parse (0 = all)

        Returns:
            List of message dicts with sender, content, timestamp
        """
        inbox_path = self.base_path / "inbox"
        if not inbox_path.exists():
            # Try alternate paths
            for alt in ["messages/inbox", "your_instagram_activity/messages/inbox"]:
                alt_path = self.base_path / alt
                if alt_path.exists():
                    inbox_path = alt_path
                    break
            else:
                print(f"No inbox directory found in {self.base_path}")
                return []

        conversations = sorted(inbox_path.iterdir()) if inbox_path.is_dir() else []
        if limit > 0:
            conversations = conversations[:limit]

        all_messages = []
        for convo_dir in conversations:
            if not convo_dir.is_dir():
                continue

            # Parse all message_*.json files in conversation
            for msg_file in sorted(convo_dir.glob("message_*.json")):
                try:
                    with open(msg_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    participants = [p.get('name', '') for p in data.get('participants', [])]
                    for msg in data.get('messages', []):
                        content = msg.get('content', '')
                        if not content:
                            continue

                        # Fix Instagram's UTF-8 encoding
                        try:
                            content = content.encode('latin-1').decode('utf-8')
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            pass

                        all_messages.append({
                            'sender': msg.get('sender_name', ''),
                            'content': content,
                            'timestamp': msg.get('timestamp_ms', 0),
                            'type': msg.get('type', 'Generic'),
                            'participants': participants,
                        })

                except (json.JSONDecodeError, OSError) as e:
                    print(f"Error reading {msg_file}: {e}")

        self.messages = all_messages
        self._parsed = True
        print(f"Parsed {len(all_messages)} messages from {len(conversations)} conversations")
        return all_messages

    def _get_owner_messages(self) -> List[str]:
        """Get messages sent by the account owner (first participant or most frequent sender)."""
        if self.owner_messages:
            return self.owner_messages

        if not self._parsed:
            self.parse_conversations()

        # Find owner by most frequent sender
        sender_counts = Counter(m['sender'] for m in self.messages)
        if not sender_counts:
            return []

        owner = sender_counts.most_common(1)[0][0]
        self.owner_messages = [
            m['content'] for m in self.messages
            if m['sender'] == owner and m['content']
        ]
        print(f"Owner identified as '{owner}' with {len(self.owner_messages)} messages")
        return self.owner_messages

    def extract_vocabulary_patterns(self) -> Dict[str, int]:
        """
        Analyze messages for vocabulary and slang frequency.

        Returns:
            Dict mapping vocabulary terms to usage count
        """
        messages = self._get_owner_messages()
        vocab_patterns = {
            'ya': r'\bya\b',
            'gonna': r'\bgonna\b',
            'wanna': r'\bwanna\b',
            'gotta': r'\bgotta\b',
            'tho': r'\btho\b',
            'cuz': r'\bcuz\b',
            'dis': r'\bdis\b',
            'fo': r'\bfo\b',
            'imma': r'\bimma\b',
            'finna': r'\bfinna\b',
            'sumn': r'\bsumn\b',
            'fasho': r'\bfasho+\b',
            'fr': r'\bfr\b',
            'nah': r'\bnah\b',
            'ion': r'\bion\b',
            'ight': r'\bight\b',
            'aight': r'\baight\b',
        }

        results = {}
        text_blob = ' '.join(messages).lower()
        for term, pattern in vocab_patterns.items():
            results[term] = len(re.findall(pattern, text_blob, re.IGNORECASE))

        return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))

    def extract_emoji_patterns(self) -> Dict[str, int]:
        """
        Count and categorize emoji usage.

        Returns:
            Dict mapping emoji to usage count (sorted by frequency)
        """
        messages = self._get_owner_messages()
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA00-\U0001FA6F"  # chess symbols
            "\U0001FA70-\U0001FAFF"  # symbols extended-A
            "\U00002600-\U000026FF"  # misc symbols
            "]+",
            flags=re.UNICODE,
        )

        emoji_counts: Counter = Counter()
        for msg in messages:
            for match in emoji_pattern.finditer(msg):
                # Count individual emojis from clusters
                for char in match.group():
                    emoji_counts[char] += 1

        return dict(emoji_counts.most_common(50))

    def extract_response_patterns(self) -> Dict[str, Any]:
        """
        Analyze response length and style distributions.

        Returns:
            Dict with length stats, word count distribution, style metrics
        """
        messages = self._get_owner_messages()
        if not messages:
            return {}

        word_counts = [len(m.split()) for m in messages]
        char_counts = [len(m) for m in messages]

        # Categorize by length
        ultra_short = sum(1 for wc in word_counts if wc <= 3)
        short = sum(1 for wc in word_counts if 4 <= wc <= 10)
        medium = sum(1 for wc in word_counts if 11 <= wc <= 25)
        long = sum(1 for wc in word_counts if wc > 25)

        total = len(messages)
        caps_messages = sum(1 for m in messages if m.isupper() and len(m) > 1)

        return {
            'total_messages': total,
            'avg_word_count': round(sum(word_counts) / total, 1) if total else 0,
            'avg_char_count': round(sum(char_counts) / total, 1) if total else 0,
            'median_word_count': sorted(word_counts)[total // 2] if total else 0,
            'distribution': {
                'ultra_short_pct': round(ultra_short / total * 100, 1) if total else 0,
                'short_pct': round(short / total * 100, 1) if total else 0,
                'medium_pct': round(medium / total * 100, 1) if total else 0,
                'long_pct': round(long / total * 100, 1) if total else 0,
            },
            'caps_emphasis_pct': round(caps_messages / total * 100, 1) if total else 0,
        }

    def extract_address_terms(self) -> Dict[str, int]:
        """
        Find address term frequency (gang, twin, fam, etc.).

        Returns:
            Dict mapping address terms to usage count
        """
        messages = self._get_owner_messages()
        terms = [
            'gang', 'twin', 'ganger', 'fam', 'dawg', 'broski',
            'slime', 'folks', 'bro', 'bruh', 'cuz', 'homie',
            'king', 'queen', 'g', 'big dawg',
        ]

        text_blob = ' '.join(messages).lower()
        results = {}
        for term in terms:
            pattern = r'\b' + re.escape(term) + r'\b'
            count = len(re.findall(pattern, text_blob))
            if count > 0:
                results[term] = count

        return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))

    def extract_agreement_patterns(self) -> Dict[str, int]:
        """
        Find agreement term frequency (bet, fasho, say less, etc.).

        Returns:
            Dict mapping agreement terms to usage count
        """
        messages = self._get_owner_messages()
        terms = [
            'bet', 'fasho', 'say less', 'say no more', 'no cap',
            'facts', 'real talk', 'on god', 'ong', 'yessir',
            'yessirskii', 'for sure', 'hundred percent', 'word',
        ]

        text_blob = ' '.join(messages).lower()
        results = {}
        for term in terms:
            pattern = r'\b' + re.escape(term) + r'\b'
            count = len(re.findall(pattern, text_blob))
            if count > 0:
                results[term] = count

        return dict(sorted(results.items(), key=lambda x: x[1], reverse=True))

    def get_training_samples(self, count: int = 20) -> List[str]:
        """
        Return formatted message samples for few-shot prompting.

        Args:
            count: Number of samples to return

        Returns:
            List of representative messages (diverse lengths, styles)
        """
        messages = self._get_owner_messages()
        if not messages:
            return []

        # Filter for quality: not too short (1 char), not too long (100+ words)
        quality = [m for m in messages if 2 <= len(m.split()) <= 40 and len(m) > 3]

        # Sample diverse lengths
        short = [m for m in quality if len(m.split()) <= 5]
        medium = [m for m in quality if 6 <= len(m.split()) <= 15]
        longer = [m for m in quality if len(m.split()) > 15]

        samples = []
        per_bucket = count // 3

        for bucket in [short, medium, longer]:
            step = max(1, len(bucket) // per_bucket) if bucket else 1
            samples.extend(bucket[::step][:per_bucket])

        return samples[:count]

    def export_persona_data(self, output_path: str) -> Dict[str, Any]:
        """
        Export all extracted speech patterns as JSON.

        Args:
            output_path: File path to write JSON output

        Returns:
            The exported data dict
        """
        if not self._parsed:
            self.parse_conversations()

        data = {
            'source': str(self.base_path),
            'total_messages_parsed': len(self.messages),
            'owner_messages_count': len(self._get_owner_messages()),
            'vocabulary_patterns': self.extract_vocabulary_patterns(),
            'emoji_patterns': self.extract_emoji_patterns(),
            'response_patterns': self.extract_response_patterns(),
            'address_terms': self.extract_address_terms(),
            'agreement_patterns': self.extract_agreement_patterns(),
            'training_samples': self.get_training_samples(20),
        }

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Exported persona data to {output_path}")
        return data


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Instagram Export Speech Pattern Parser")
    parser.add_argument('--path', required=True, help='Path to Instagram data export directory')
    parser.add_argument('--output', default='persona_data.json', help='Output JSON file path')
    parser.add_argument('--limit', type=int, default=0, help='Max conversations to parse (0=all)')
    parser.add_argument('--action', choices=['full', 'vocab', 'emoji', 'response', 'address', 'agreement', 'samples'],
                       default='full', help='What to extract')

    args = parser.parse_args()

    ig_parser = InstagramParser(args.path)
    ig_parser.parse_conversations(limit=args.limit)

    if args.action == 'full':
        data = ig_parser.export_persona_data(args.output)
        print(f"\nExported {len(data)} categories to {args.output}")

    elif args.action == 'vocab':
        results = ig_parser.extract_vocabulary_patterns()
        print("\nVocabulary Patterns:")
        for term, count in results.items():
            print(f"  {term}: {count}")

    elif args.action == 'emoji':
        results = ig_parser.extract_emoji_patterns()
        print("\nEmoji Patterns:")
        for emoji, count in list(results.items())[:20]:
            print(f"  {emoji}: {count}")

    elif args.action == 'response':
        results = ig_parser.extract_response_patterns()
        print("\nResponse Patterns:")
        for key, value in results.items():
            print(f"  {key}: {value}")

    elif args.action == 'address':
        results = ig_parser.extract_address_terms()
        print("\nAddress Terms:")
        for term, count in results.items():
            print(f"  {term}: {count}")

    elif args.action == 'agreement':
        results = ig_parser.extract_agreement_patterns()
        print("\nAgreement Patterns:")
        for term, count in results.items():
            print(f"  {term}: {count}")

    elif args.action == 'samples':
        samples = ig_parser.get_training_samples(20)
        print(f"\nTraining Samples ({len(samples)}):")
        for i, s in enumerate(samples, 1):
            print(f"  {i}. {s}")
