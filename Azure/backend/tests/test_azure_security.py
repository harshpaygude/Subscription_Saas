from app.providers.azure.security import authorization_url, pkce_pair


def test_pkce_pair_and_authorization_url() -> None:
    verifier, challenge = pkce_pair()
    assert verifier and challenge
    url = authorization_url("common", "client", "http://localhost/callback", "state", challenge, "scope")
    assert "response_type=code" in url
    assert "code_challenge_method=S256" in url

