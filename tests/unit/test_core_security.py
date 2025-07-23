import time
from gateway.core.security import create_access_token, verify_token



def test_jwt_roundtrip():
    tok = create_access_token({"sub": "user-123"}, exp_seconds=2)
    claims = verify_token(tok)
    assert claims["sub"] == "user-123"

    # token should expire
    time.sleep(2)
    import pytest, jwt
    with pytest.raises(jwt.InvalidTokenError):
        verify_token(tok)