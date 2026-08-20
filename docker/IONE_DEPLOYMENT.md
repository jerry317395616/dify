# I-ONE deployment

This deployment keeps Dify independent from Frappe while allowing trusted Dify
services to reach the private Qwen network. Frappe users access Dify through the
`ione_agent` server-side integration; the Dify console remains available to AI
administrators.

## Build from this fork

Run these commands from the repository root and replace `local` with an immutable
commit tag in production:

```bash
docker build -f api/Dockerfile -t ione/dify-api:local .
docker build -f web/Dockerfile -t ione/dify-web:local .
docker build -f dify-agent/Dockerfile -t ione/dify-agent-backend:local .
```

## Configure

From `docker/`:

```bash
cp .env.example .env
cp envs/ione.env.example ione.env
```

Set production secrets only in the untracked `.env` or `ione.env` files and
restrict both files to the service account (`chmod 600 .env ione.env`). Set the
public Dify URL and immutable image tags in `ione.env`. The external network
configured by `IONE_QWEN_NETWORK` must already exist; do not publish the Qwen
container port.

Keep `HOSTED_FETCH_APP_TEMPLATES_MODE=db` in `ione.env` for branded
deployments. The create-from-template dialog then uses only listed, public
templates in the local `recommended_apps` catalog instead of Dify's remote or
built-in application templates. Plugin Marketplace access is configured
separately and remains available.

### Frappe console SSO

Create an OAuth Client on `https://child.myyr.top` with these values:

- redirect URI: `https://dify.myyr.top/console/api/oauth/authorize/frappe`
- response type: `Code`
- scope: `openid`
- allowed roles: `I-ONE Agent Manager` and `System Manager`
- skip authorization: enabled, if the app icon should enter Dify without an
  additional consent screen

Put the generated client ID and secret in the untracked `ione.env`. The
production-specific settings are:

```dotenv
FRAPPE_OAUTH_BASE_URL=https://child.myyr.top
FRAPPE_OAUTH_CLIENT_ID=<oauth-client-id>
FRAPPE_OAUTH_CLIENT_SECRET=<oauth-client-secret>
FRAPPE_OAUTH_ALLOWED_ROLES=I-ONE Agent Manager,System Manager
FRAPPE_OAUTH_JIT_ENABLED=true
FRAPPE_OAUTH_JIT_TENANT_ID=7cdfa690-411d-425d-a3b3-c19bf338c2f5
FRAPPE_OAUTH_JIT_TENANT_ROLE=admin
```

Role names are exact, comma-separated Frappe role names. JIT is disabled in the
example file by default. When enabled, it bypasses neither the Frappe role
allowlist nor Dify seat limits: it creates an account only after Frappe has
authenticated an allowed user, adds that account to the one existing tenant
above, and never creates a personal workspace. `owner` is deliberately rejected
as a JIT role. Keep Dify's global `ALLOW_REGISTER=false`.

The Frappe userinfo issuer must exactly match the HTTPS base URL. OAuth state is
signed with Dify's persistent `SECRET_KEY`, expires after ten minutes, and is
bound to the initiating browser with a short-lived `Secure`, `HttpOnly`,
`SameSite=Lax` cookie. All API replicas must use the same secret. The app icon
can link directly to:

```text
https://dify.myyr.top/console/api/oauth/login/frappe?redirect_url=/apps
```

After the callback, Dify issues its own console session cookies. This SSO path
does not share Frappe cookies, Dify app keys, Codex sessions, or Codex App Server
ports.

## Start

```bash
docker compose \
  --env-file .env \
  --env-file ione.env \
  -f docker-compose.yaml \
  -f docker-compose.ione.yaml \
  up -d
```

Do not expose Dify app keys in Frappe JavaScript. Store them in Frappe site
configuration and call Dify only through `ione_agent` server methods.

## Start with the I-ONE platform

Keep a stable `current` symlink pointing at the active release, then install the
included user service. Dify remains operationally independent from Bench, while
both stacks start automatically with the server:

```bash
ln -sfn /path/to/active/dify-release ~/services/ione-dify/current
install -Dm644 docker/systemd/ione-dify.service \
  ~/.config/systemd/user/ione-dify.service
systemctl --user daemon-reload
systemctl --user enable --now ione-dify.service
```

The Compose services use restart policies for process-level recovery. The
systemd unit provides a stable lifecycle entry point for startup, reload and
controlled shutdown; Dify is intentionally not placed inside a Bench container.
