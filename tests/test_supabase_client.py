from unittest.mock import patch

from backend.supabase_client import get_supabase_client


def test_uses_effective_secret_key() -> None:
    with (
        patch("backend.supabase_client.get_settings") as mock_settings,
        patch("backend.supabase_client.create_client") as mock_create,
    ):
        mock_settings.return_value.supabase_url = "https://example.supabase.co"
        mock_settings.return_value.effective_supabase_secret_key = "sb_secret_new"

        get_supabase_client.cache_clear()
        get_supabase_client()

        mock_create.assert_called_once_with(
            "https://example.supabase.co",
            "sb_secret_new",
        )
