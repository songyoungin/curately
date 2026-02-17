"""Supabase client initialization and helpers."""

from functools import lru_cache

from supabase import Client, create_client

from backend.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Return a cached Supabase client using the effective secret key."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.effective_supabase_secret_key)
