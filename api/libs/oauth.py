import base64
import binascii
import hashlib
import json
import logging
import secrets
import urllib.parse
from dataclasses import dataclass
from typing import NotRequired, TypedDict, override

import httpx
from pydantic import TypeAdapter, ValidationError

from core.helper import ssrf_proxy
from core.helper.http_client_pooling import get_pooled_http_client
from libs import jws

logger = logging.getLogger(__name__)

type JsonObject = dict[str, object]
type JsonObjectList = list[JsonObject]

JSON_OBJECT_ADAPTER: TypeAdapter[JsonObject] = TypeAdapter(JsonObject)
JSON_OBJECT_LIST_ADAPTER: TypeAdapter[JsonObjectList] = TypeAdapter(JsonObjectList)

# Reuse a pooled httpx.Client for OAuth flows (public endpoints, no SSRF proxy).
_http_client: httpx.Client = get_pooled_http_client(
    "oauth:default",
    lambda: httpx.Client(limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)),
)


class AccessTokenResponse(TypedDict, total=False):
    access_token: str


class OAuthState(TypedDict, total=False):
    invite_token: str
    timezone: str
    language: str
    redirect_url: str


class GitHubEmailRecord(TypedDict, total=False):
    email: str
    primary: bool
    verified: bool


class GitHubRawUserInfo(TypedDict):
    id: int | str
    login: str
    name: NotRequired[str | None]
    email: NotRequired[str | None]


class GoogleRawUserInfo(TypedDict):
    sub: str
    email: str


class FrappeRawUserInfo(TypedDict):
    sub: str | None
    email: str
    iss: str
    roles: list[str]
    name: NotRequired[str | None]


ACCESS_TOKEN_RESPONSE_ADAPTER = TypeAdapter(AccessTokenResponse)
OAUTH_STATE_ADAPTER = TypeAdapter(OAuthState)
GITHUB_RAW_USER_INFO_ADAPTER = TypeAdapter(GitHubRawUserInfo)
GITHUB_EMAIL_RECORDS_ADAPTER = TypeAdapter(list[GitHubEmailRecord])
GOOGLE_RAW_USER_INFO_ADAPTER = TypeAdapter(GoogleRawUserInfo)
FRAPPE_RAW_USER_INFO_ADAPTER = TypeAdapter(FrappeRawUserInfo)

FRAPPE_OAUTH_STATE_AUDIENCE = "console.oauth.frappe_state"
FRAPPE_OAUTH_STATE_TTL_SECONDS = 10 * 60
_OAUTH_STATE_FIELDS = ("invite_token", "timezone", "language", "redirect_url")


@dataclass
class OAuthUserInfo:
    id: str
    name: str
    email: str


def encode_oauth_state(
    invite_token: str | None = None,
    timezone: str | None = None,
    language: str | None = None,
    redirect_url: str | None = None,
) -> str | None:
    state: OAuthState = {}
    if invite_token:
        state["invite_token"] = invite_token
    if timezone:
        state["timezone"] = timezone
    if language:
        state["language"] = language
    if redirect_url:
        state["redirect_url"] = redirect_url
    if not state:
        return None

    raw_state = json.dumps(state, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw_state).decode("ascii").rstrip("=")


def decode_oauth_state(state: str | None) -> OAuthState:
    if not state:
        return {}

    try:
        padded_state = state + "=" * (-len(state) % 4)
        raw_state = base64.urlsafe_b64decode(padded_state.encode("ascii")).decode("utf-8")
        return OAUTH_STATE_ADAPTER.validate_python(json.loads(raw_state))
    except (binascii.Error, ValueError, UnicodeDecodeError, json.JSONDecodeError, ValidationError):
        return {}


def encode_frappe_oauth_state(
    invite_token: str | None = None,
    timezone: str | None = None,
    language: str | None = None,
    redirect_url: str | None = None,
) -> str:
    payload: dict[str, str] = {"nonce": secrets.token_urlsafe(16)}
    if invite_token:
        payload["invite_token"] = invite_token
    if timezone:
        payload["timezone"] = timezone
    if language:
        payload["language"] = language
    if redirect_url:
        payload["redirect_url"] = redirect_url
    return jws.sign(
        jws.KeySet.from_shared_secret(),
        payload=payload,
        aud=FRAPPE_OAUTH_STATE_AUDIENCE,
        ttl_seconds=FRAPPE_OAUTH_STATE_TTL_SECONDS,
    )


def decode_frappe_oauth_state(state: str | None) -> OAuthState:
    if not state:
        raise ValueError("Frappe OAuth state is required")
    try:
        claims = jws.verify(
            jws.KeySet.from_shared_secret(),
            state,
            expected_aud=FRAPPE_OAUTH_STATE_AUDIENCE,
        )
        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            raise ValueError("Frappe OAuth state nonce is missing")
        payload = {key: claims[key] for key in _OAUTH_STATE_FIELDS if key in claims}
        return OAUTH_STATE_ADAPTER.validate_python(payload)
    except (jws.KeySetError, jws.VerifyError, ValidationError, ValueError) as e:
        raise ValueError("Frappe OAuth state is invalid or expired") from e


def _json_object(response: httpx.Response) -> JsonObject:
    return JSON_OBJECT_ADAPTER.validate_python(response.json())


def _json_list(response: httpx.Response) -> JsonObjectList:
    return JSON_OBJECT_LIST_ADAPTER.validate_python(response.json())


class OAuth:
    client_id: str
    client_secret: str
    redirect_uri: str

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(
        self,
        invite_token: str | None = None,
        timezone: str | None = None,
        language: str | None = None,
        redirect_url: str | None = None,
    ) -> str:
        raise NotImplementedError()

    def get_access_token(self, code: str) -> str:
        raise NotImplementedError()

    def get_raw_user_info(self, token: str) -> JsonObject:
        raise NotImplementedError()

    def get_user_info(self, token: str) -> OAuthUserInfo:
        raw_info = self.get_raw_user_info(token)
        return self._transform_user_info(raw_info)

    def _transform_user_info(self, raw_info: JsonObject) -> OAuthUserInfo:
        raise NotImplementedError()


class GitHubOAuth(OAuth):
    _AUTH_URL = "https://github.com/login/oauth/authorize"
    _TOKEN_URL = "https://github.com/login/oauth/access_token"
    _USER_INFO_URL = "https://api.github.com/user"
    _EMAIL_INFO_URL = "https://api.github.com/user/emails"

    @override
    def get_authorization_url(
        self,
        invite_token: str | None = None,
        timezone: str | None = None,
        language: str | None = None,
        redirect_url: str | None = None,
    ) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",  # Request only basic user information
        }
        state = encode_oauth_state(
            invite_token=invite_token,
            timezone=timezone,
            language=language,
            redirect_url=redirect_url,
        )
        if state:
            params["state"] = state
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    @override
    def get_access_token(self, code: str) -> str:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}
        response = _http_client.post(self._TOKEN_URL, data=data, headers=headers)

        response_json = ACCESS_TOKEN_RESPONSE_ADAPTER.validate_python(_json_object(response))
        access_token = response_json.get("access_token")

        if not access_token:
            raise ValueError(f"Error in GitHub OAuth: {response_json}")

        return access_token

    @override
    def get_raw_user_info(self, token: str) -> JsonObject:
        headers = {"Authorization": f"token {token}"}
        response = _http_client.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        user_info = GITHUB_RAW_USER_INFO_ADAPTER.validate_python(_json_object(response))

        # Only call the /user/emails endpoint when the profile email is absent,
        # i.e. the user has "Keep my email addresses private" enabled.
        resolved_email = user_info.get("email") or ""
        if not resolved_email:
            resolved_email = self._get_email_from_emails_endpoint(headers)

        return {**user_info, "email": resolved_email}

    @staticmethod
    def _get_email_from_emails_endpoint(headers: dict[str, str]) -> str:
        """Fetch the best available email from GitHub's /user/emails endpoint.

        Prefers the primary email, then falls back to any verified email.
        Returns an empty string when no usable email is found.
        """
        try:
            email_response = _http_client.get(GitHubOAuth._EMAIL_INFO_URL, headers=headers)
            email_response.raise_for_status()
            email_records = GITHUB_EMAIL_RECORDS_ADAPTER.validate_python(_json_list(email_response))
        except (httpx.HTTPStatusError, ValidationError):
            logger.warning("Failed to retrieve email from GitHub /user/emails endpoint", exc_info=True)
            return ""

        primary = next((r for r in email_records if r.get("primary") is True), None)
        if primary:
            return primary.get("email", "")

        # No primary email; try any verified email as a fallback.
        verified = next((r for r in email_records if r.get("verified") is True), None)
        if verified:
            return verified.get("email", "")

        return ""

    @override
    def _transform_user_info(self, raw_info: JsonObject) -> OAuthUserInfo:
        payload = GITHUB_RAW_USER_INFO_ADAPTER.validate_python(raw_info)
        email = payload.get("email") or ""
        if not email:
            # When no email is available from the profile or /user/emails endpoint,
            # fall back to GitHub's noreply address so sign-in can still proceed.
            # Use only the numeric ID (not the login) so the address stays stable
            # even if the user renames their GitHub account.
            github_id = payload["id"]
            email = f"{github_id}@users.noreply.github.com"
            logger.info("GitHub user %s has no public email; using noreply address", payload["login"])
        return OAuthUserInfo(id=str(payload["id"]), name=str(payload.get("name") or ""), email=email)


class GoogleOAuth(OAuth):
    _AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    _TOKEN_URL = "https://oauth2.googleapis.com/token"
    _USER_INFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

    @override
    def get_authorization_url(
        self,
        invite_token: str | None = None,
        timezone: str | None = None,
        language: str | None = None,
        redirect_url: str | None = None,
    ) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "openid email",
        }
        state = encode_oauth_state(
            invite_token=invite_token,
            timezone=timezone,
            language=language,
            redirect_url=redirect_url,
        )
        if state:
            params["state"] = state
        return f"{self._AUTH_URL}?{urllib.parse.urlencode(params)}"

    @override
    def get_access_token(self, code: str) -> str:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        headers = {"Accept": "application/json"}
        response = _http_client.post(self._TOKEN_URL, data=data, headers=headers)

        response_json = ACCESS_TOKEN_RESPONSE_ADAPTER.validate_python(_json_object(response))
        access_token = response_json.get("access_token")

        if not access_token:
            raise ValueError(f"Error in Google OAuth: {response_json}")

        return access_token

    @override
    def get_raw_user_info(self, token: str) -> JsonObject:
        headers = {"Authorization": f"Bearer {token}"}
        response = _http_client.get(self._USER_INFO_URL, headers=headers)
        response.raise_for_status()
        return _json_object(response)

    @override
    def _transform_user_info(self, raw_info: JsonObject) -> OAuthUserInfo:
        payload = GOOGLE_RAW_USER_INFO_ADAPTER.validate_python(raw_info)
        return OAuthUserInfo(id=str(payload["sub"]), name="", email=payload["email"])


class FrappeOAuth(OAuth):
    """OAuth client for a trusted Frappe site acting as the identity provider."""

    _AUTHORIZE_PATH = "/api/method/frappe.integrations.oauth2.authorize"
    _TOKEN_PATH = "/api/method/frappe.integrations.oauth2.get_token"
    _USER_INFO_PATH = "/api/method/frappe.integrations.oauth2.openid_profile"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        base_url: str,
        allowed_roles: set[str],
    ):
        super().__init__(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
        self.base_url = self._validate_base_url(base_url)
        self.allowed_roles = frozenset(role.strip() for role in allowed_roles if role.strip())
        if not self.allowed_roles:
            raise ValueError("Frappe OAuth requires at least one allowed role")

    @staticmethod
    def _validate_base_url(base_url: str) -> str:
        parsed = urllib.parse.urlsplit(base_url.strip())
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("Frappe OAuth base URL must be an HTTPS origin without credentials, query, or fragment")

        return urllib.parse.urlunsplit(("https", parsed.netloc.lower(), "", "", ""))

    def _endpoint(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @override
    def get_authorization_url(
        self,
        invite_token: str | None = None,
        timezone: str | None = None,
        language: str | None = None,
        redirect_url: str | None = None,
    ) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "openid",
        }
        state = encode_frappe_oauth_state(
            invite_token=invite_token,
            timezone=timezone,
            language=language,
            redirect_url=redirect_url,
        )
        params["state"] = state
        return f"{self._endpoint(self._AUTHORIZE_PATH)}?{urllib.parse.urlencode(params)}"

    @override
    def get_access_token(self, code: str) -> str:
        response = ssrf_proxy.post(
            self._endpoint(self._TOKEN_PATH),
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            },
            headers={"Accept": "application/json"},
            max_retries=0,
        )
        response.raise_for_status()
        response_json = ACCESS_TOKEN_RESPONSE_ADAPTER.validate_python(_json_object(response))
        access_token = response_json.get("access_token")
        if not access_token:
            raise ValueError("Error in Frappe OAuth token response")
        return access_token

    @override
    def get_raw_user_info(self, token: str) -> JsonObject:
        response = ssrf_proxy.get(
            self._endpoint(self._USER_INFO_PATH),
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            max_retries=0,
        )
        response.raise_for_status()
        return _json_object(response)

    @override
    def _transform_user_info(self, raw_info: JsonObject) -> OAuthUserInfo:
        payload = FRAPPE_RAW_USER_INFO_ADAPTER.validate_python(raw_info)
        email = payload["email"].strip()
        if not email:
            raise ValueError("Frappe OAuth returned an incomplete user profile")
        try:
            issuer = self._validate_base_url(payload["iss"])
        except ValueError as e:
            raise ValueError("Frappe OAuth returned an unexpected issuer") from e
        if issuer != self.base_url:
            raise ValueError("Frappe OAuth returned an unexpected issuer")
        if self.allowed_roles.isdisjoint(payload["roles"]):
            raise ValueError("Your Frappe account is not authorized to access Dify")

        subject = (payload["sub"] or "").strip()
        if not subject:
            # Frappe returns a null `sub` until a User Social Login row for the
            # built-in `frappe` provider exists. Keep the identity opaque and
            # issuer-scoped while remaining compatible with those accounts.
            identity = f"{issuer}\0{email.casefold()}".encode()
            subject = f"frappe-email:{hashlib.sha256(identity).hexdigest()}"
        return OAuthUserInfo(
            id=subject,
            name=payload.get("name") or "",
            email=email,
        )
