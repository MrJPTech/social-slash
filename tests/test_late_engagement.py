"""
Unit tests for Late engagement client.

Tests the unified Late API inbox operations.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from engagement.late_engagement_client import LateEngagementClient


class TestLateEngagementClientInit:
    """Test client initialization."""

    def test_init_with_api_key(self):
        """Initialize with explicit API key."""
        client = LateEngagementClient(api_key='test_key')
        assert client.api_key == 'test_key'

    def test_init_from_env(self):
        """Initialize from environment variable."""
        with patch.dict(os.environ, {'LATE_API_KEY': 'env_key'}):
            client = LateEngagementClient()
            assert client.api_key == 'env_key'

    def test_init_raises_without_key(self):
        """Raise error when no API key available."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove LATE_API_KEY if it exists
            if 'LATE_API_KEY' in os.environ:
                del os.environ['LATE_API_KEY']
            with pytest.raises(ValueError) as exc:
                LateEngagementClient()
            assert 'LATE_API_KEY' in str(exc.value)


class TestPlatformSupport:
    """Test platform support constants."""

    def test_comment_platforms(self):
        """Verify comment-supported platforms."""
        expected = ['facebook', 'instagram', 'youtube', 'linkedin',
                   'reddit', 'bluesky', 'tiktok']
        assert LateEngagementClient.COMMENT_PLATFORMS == expected

    def test_dm_platforms(self):
        """Verify DM-supported platforms."""
        expected = ['facebook', 'instagram', 'bluesky', 'reddit', 'telegram']
        assert LateEngagementClient.DM_PLATFORMS == expected


class TestCommentsAPI:
    """Test comments API methods."""

    @pytest.fixture
    def client(self):
        """Create client with mocked httpx."""
        with patch('engagement.late_engagement_client.httpx.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            client = LateEngagementClient(api_key='test_key')
            client._client = mock_instance
            yield client

    def test_list_posts_with_comments(self, client):
        """List posts with comments."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [{'id': 'post_1', 'platform': 'instagram'}],
            'cursor': 'next_cursor'
        }
        mock_response.raise_for_status = Mock()
        client._client.get.return_value = mock_response

        result = client.list_posts_with_comments(platform='instagram')

        assert 'data' in result
        assert len(result['data']) == 1
        client._client.get.assert_called_once()

    def test_list_posts_with_comments_params(self, client):
        """Verify parameters are passed correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {'data': []}
        mock_response.raise_for_status = Mock()
        client._client.get.return_value = mock_response

        client.list_posts_with_comments(
            platform='instagram',
            min_comments=5,
            limit=25,
            cursor='abc123'
        )

        call_args = client._client.get.call_args
        params = call_args[1]['params']
        assert params['platform'] == 'instagram'
        assert params['minComments'] == 5
        assert params['limit'] == 25
        assert params['cursor'] == 'abc123'

    def test_get_post_comments(self, client):
        """Get comments for a post."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'id': 'comment_1', 'text': 'Great!'},
                {'id': 'comment_2', 'text': 'Nice post!'}
            ]
        }
        mock_response.raise_for_status = Mock()
        client._client.get.return_value = mock_response

        result = client.get_post_comments('post_123')

        assert len(result['data']) == 2
        client._client.get.assert_called_once()

    def test_reply_to_comment(self, client):
        """Reply to a comment."""
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'reply_123', 'status': 'created'}
        mock_response.raise_for_status = Mock()
        client._client.post.return_value = mock_response

        result = client.reply_to_comment(
            post_id='post_123',
            account_id='acc_123',
            message='Thank you!',
            comment_id='comment_123'
        )

        assert result['status'] == 'created'
        call_args = client._client.post.call_args
        payload = call_args[1]['json']
        assert payload['message'] == 'Thank you!'
        assert payload['accountId'] == 'acc_123'
        assert payload['commentId'] == 'comment_123'

    def test_reply_to_comment_reddit_subreddit(self, client):
        """Reply with subreddit for Reddit."""
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'reply_123'}
        mock_response.raise_for_status = Mock()
        client._client.post.return_value = mock_response

        client.reply_to_comment(
            post_id='post_123',
            account_id='acc_123',
            message='Thanks!',
            subreddit='r/test'
        )

        call_args = client._client.post.call_args
        payload = call_args[1]['json']
        assert payload['subreddit'] == 'r/test'

    def test_delete_comment(self, client):
        """Delete a comment."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'deleted'}
        mock_response.raise_for_status = Mock()
        client._client.delete.return_value = mock_response

        result = client.delete_comment('post_123', 'comment_123')

        assert result['status'] == 'deleted'

    def test_hide_comment(self, client):
        """Hide a comment (Facebook/Instagram)."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'hidden'}
        mock_response.raise_for_status = Mock()
        client._client.post.return_value = mock_response

        result = client.hide_comment('post_123', 'comment_123')

        assert result['status'] == 'hidden'

    def test_like_comment(self, client):
        """Like a comment."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'liked'}
        mock_response.raise_for_status = Mock()
        client._client.post.return_value = mock_response

        result = client.like_comment('post_123', 'comment_123')

        assert result['status'] == 'liked'


class TestMessagesAPI:
    """Test messages/DMs API methods."""

    @pytest.fixture
    def client(self):
        """Create client with mocked httpx."""
        with patch('engagement.late_engagement_client.httpx.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            client = LateEngagementClient(api_key='test_key')
            client._client = mock_instance
            yield client

    def test_list_conversations(self, client):
        """List DM conversations."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'id': 'conv_1', 'platform': 'instagram'},
                {'id': 'conv_2', 'platform': 'telegram'}
            ]
        }
        mock_response.raise_for_status = Mock()
        client._client.get.return_value = mock_response

        result = client.list_conversations()

        assert len(result['data']) == 2

    def test_list_conversations_with_filters(self, client):
        """List conversations with platform filter."""
        mock_response = Mock()
        mock_response.json.return_value = {'data': []}
        mock_response.raise_for_status = Mock()
        client._client.get.return_value = mock_response

        client.list_conversations(
            platform='instagram',
            status='active',
            limit=25
        )

        call_args = client._client.get.call_args
        params = call_args[1]['params']
        assert params['platform'] == 'instagram'
        assert params['status'] == 'active'
        assert params['limit'] == 25

    def test_get_conversation(self, client):
        """Get conversation details."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 'conv_123',
            'participant': {'name': 'John Doe'}
        }
        mock_response.raise_for_status = Mock()
        client._client.get.return_value = mock_response

        result = client.get_conversation('conv_123', 'acc_123')

        assert result['id'] == 'conv_123'

    def test_get_messages(self, client):
        """Get messages in a conversation."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'messages': [
                {'id': 'msg_1', 'message': 'Hello!'},
                {'id': 'msg_2', 'message': 'Hi there!'}
            ]
        }
        mock_response.raise_for_status = Mock()
        client._client.get.return_value = mock_response

        result = client.get_messages('conv_123', 'acc_123')

        assert len(result['messages']) == 2

    def test_send_message(self, client):
        """Send a DM reply."""
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'msg_new', 'status': 'sent'}
        mock_response.raise_for_status = Mock()
        client._client.post.return_value = mock_response

        result = client.send_message(
            conversation_id='conv_123',
            account_id='acc_123',
            message='Thanks for reaching out!'
        )

        assert result['status'] == 'sent'
        call_args = client._client.post.call_args
        payload = call_args[1]['json']
        assert payload['message'] == 'Thanks for reaching out!'

    def test_archive_conversation(self, client):
        """Archive a conversation."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'archived'}
        mock_response.raise_for_status = Mock()
        client._client.put.return_value = mock_response

        result = client.archive_conversation('conv_123', 'acc_123')

        assert result['status'] == 'archived'


class TestWebhooksAPI:
    """Test webhooks API methods."""

    @pytest.fixture
    def client(self):
        """Create client with mocked httpx."""
        with patch('engagement.late_engagement_client.httpx.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            client = LateEngagementClient(api_key='test_key')
            client._client = mock_instance
            yield client

    def test_register_webhook(self, client):
        """Register a webhook."""
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'webhook_123', 'url': 'https://example.com/webhook'}
        mock_response.raise_for_status = Mock()
        client._client.post.return_value = mock_response

        result = client.register_webhook(
            url='https://example.com/webhook',
            events=['message.received', 'post.published'],
            secret='mysecret'
        )

        assert result['id'] == 'webhook_123'
        call_args = client._client.post.call_args
        payload = call_args[1]['json']
        assert payload['url'] == 'https://example.com/webhook'
        assert 'message.received' in payload['events']

    def test_list_webhooks(self, client):
        """List registered webhooks."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [{'id': 'wh_1'}, {'id': 'wh_2'}]
        }
        mock_response.raise_for_status = Mock()
        client._client.get.return_value = mock_response

        result = client.list_webhooks()

        assert len(result['data']) == 2

    def test_delete_webhook(self, client):
        """Delete a webhook."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'deleted'}
        mock_response.raise_for_status = Mock()
        client._client.delete.return_value = mock_response

        result = client.delete_webhook('webhook_123')

        assert result['status'] == 'deleted'


class TestClientContextManager:
    """Test client context manager."""

    def test_context_manager(self):
        """Use client as context manager."""
        with patch('engagement.late_engagement_client.httpx.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            with LateEngagementClient(api_key='test_key') as client:
                assert client is not None

            mock_instance.close.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
