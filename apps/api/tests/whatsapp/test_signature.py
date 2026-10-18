from custodio.whatsapp.signature import sign, signature_valid, token_matches

BODY = b'{"object":"whatsapp_business_account","entry":[]}'


def test_a_body_signed_with_the_app_secret_is_valid() -> None:
    assert signature_valid(BODY, sign(BODY, "secret"), "secret")


def test_another_secret_a_changed_body_or_no_header_is_invalid() -> None:
    assert not signature_valid(BODY, sign(BODY, "other"), "secret")
    assert not signature_valid(BODY + b" ", sign(BODY, "secret"), "secret")
    assert not signature_valid(BODY, None, "secret")
    assert not signature_valid(BODY, "", "secret")


def test_a_bare_digest_without_the_sha256_prefix_is_invalid() -> None:
    assert not signature_valid(BODY, sign(BODY, "secret").removeprefix("sha256="), "secret")


def test_the_verify_token_must_match_exactly() -> None:
    assert token_matches("token", "token")
    assert not token_matches("token ", "token")
    assert not token_matches(None, "token")
