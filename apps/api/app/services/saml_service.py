"""
SAML 2.0 SP helpers (python3-saml).

Only active when SAML_ENABLED=true. Requires IDP config via env vars:
  SAML_IDP_ENTITY_ID, SAML_IDP_SSO_URL, SAML_IDP_CERT
"""
from __future__ import annotations

from typing import Any


def _saml_settings() -> dict[str, Any]:
    from app.config import settings

    return {
        "strict": True,
        "debug": settings.debug,
        "sp": {
            "entityId": settings.saml_sp_entity_id,
            "assertionConsumerService": {
                "url": settings.saml_sp_acs_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "singleLogoutService": {
                "url": settings.saml_sp_acs_url.replace("/acs", "/sls"),
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "NameIDFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
            "x509cert": settings.saml_sp_cert or "",
            "privateKey": settings.saml_sp_private_key or "",
        },
        "idp": {
            "entityId": settings.saml_idp_entity_id or "",
            "singleSignOnService": {
                "url": settings.saml_idp_sso_url or "",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": settings.saml_idp_cert or "",
        },
    }


def get_sp_metadata() -> tuple[str, list[str]]:
    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    saml = OneLogin_Saml2_Settings(settings=_saml_settings(), sp_validation_only=True)
    metadata = saml.get_sp_metadata()
    errors = saml.validate_metadata(metadata)
    return metadata.decode() if isinstance(metadata, bytes) else metadata, errors


def build_login_url(request_data: dict[str, Any]) -> str:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    auth = OneLogin_Saml2_Auth(request_data, _saml_settings())
    return auth.login()


def process_response(request_data: dict[str, Any]) -> dict[str, str]:
    """Returns {"email": ..., "name_id": ...} or raises ValueError."""
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    auth = OneLogin_Saml2_Auth(request_data, _saml_settings())
    auth.process_response()
    if auth.get_errors():
        raise ValueError(f"SAML validation failed: {auth.get_last_error_reason()}")
    if not auth.is_authenticated():
        raise ValueError("SAML authentication failed")
    name_id = auth.get_nameid()
    attrs = auth.get_attributes()
    email = name_id  # NameID is the email when NameIDFormat is emailAddress
    # Some IdPs send email in attributes
    for key in ("email", "Email", "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"):
        if key in attrs and attrs[key]:
            email = attrs[key][0]
            break
    return {"email": email, "name_id": name_id}
