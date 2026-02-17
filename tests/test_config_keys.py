from backend.config import Settings


def test_prefers_new_supabase_keys_over_legacy() -> None:
    settings = Settings(
        supabase_publishable_key="sb_publishable_new",
        supabase_anon_key="legacy_anon",
        supabase_secret_key="sb_secret_new",
        supabase_service_role_key="legacy_service",
    )
    assert settings.effective_supabase_publishable_key == "sb_publishable_new"
    assert settings.effective_supabase_secret_key == "sb_secret_new"
