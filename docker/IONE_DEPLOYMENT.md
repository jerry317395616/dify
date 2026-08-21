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

Keep `IONE_BRANDED_UI=true` to hide the Help button, the external template
catalog link, and the Integrations and Marketplace navigation entries. This is
a presentation boundary only: direct administrative routes remain available
for model and plugin maintenance.

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
FRAPPE_OAUTH_INTERNAL_BASE_URL=http://frontend:8080
FRAPPE_OAUTH_CLIENT_ID=<oauth-client-id>
FRAPPE_OAUTH_CLIENT_SECRET=<oauth-client-secret>
FRAPPE_OAUTH_ALLOWED_ROLES=I-ONE Agent Manager,System Manager
FRAPPE_OAUTH_JIT_ENABLED=true
FRAPPE_OAUTH_JIT_TENANT_ID=7cdfa690-411d-425d-a3b3-c19bf338c2f5
FRAPPE_OAUTH_JIT_TENANT_ROLE=admin
```

`FRAPPE_OAUTH_BASE_URL` remains the public browser authorization origin and the
expected OpenID issuer. `FRAPPE_OAUTH_INTERNAL_BASE_URL` is used only by the
Dify API container for the code/token and userinfo calls; the Compose override
joins that container to `IONE_FRAPPE_NETWORK` and preserves
`Host: child.myyr.top` for Frappe site routing. Keep the internal value on a
private IP or a single-label Docker service name.

The I-ONE Compose override deliberately sets Weaviate's accepted API key from
`WEAVIATE_API_KEY`, the same variable used by the Dify API and workers. Do not
override `WEAVIATE_AUTHENTICATION_APIKEY_ALLOWED_KEYS` separately in this
deployment; separate values cause knowledge indexing to fail with HTTP 401.

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

## Private knowledge-base embedding service

The chat model is not used as a knowledge-base embedding model. Deploy the
separate BGE-M3 pooling service from `docker/embedding/`; it exposes the
OpenAI-compatible `/v1/embeddings` API only on `ione-qwen-internal` and does
not publish a host port:

```bash
mkdir -p ~/services/ione-embedding/current
cp docker/embedding/compose.yaml ~/services/ione-embedding/current/compose.yaml
cp docker/embedding/.env.example ~/services/ione-embedding/current/.env
chmod 600 ~/services/ione-embedding/current/.env
docker compose --project-directory ~/services/ione-embedding/current \
  --env-file ~/services/ione-embedding/current/.env up -d
```

Generate a unique `IONE_EMBEDDING_API_KEY` in the untracked `.env`. In Dify,
add an OpenAI-API-compatible **Text Embedding** model with these settings:

- model: `bge-m3`
- API Base URL: `http://ione-embedding-bge-m3:8000/v1`
- context size: `8192`
- max chunks per batch: `16`
- encoding format: `float`

Set it as the workspace default Text Embedding model. The model outputs
1024-dimensional dense vectors. Existing datasets must be re-indexed if their
embedding model or vector dimension changes.

## Start with the I-ONE platform

Keep a stable `current` symlink pointing at the active release, then install the
included user service. Dify remains operationally independent from Bench, while
both stacks start automatically with the server:

```bash
release=/path/to/active/dify-release
data_root="$HOME/services/ione-dify/data"

# Bootstrap persistent data once from the release defaults. Every later
# release must link to this same directory before Compose is started.
if [ ! -e "$data_root/volumes" ]; then
  mkdir -p "$data_root"
  cp -a "$release/docker/volumes" "$data_root/volumes"
fi
if [ ! -L "$release/docker/volumes" ]; then
  mv "$release/docker/volumes" "$release/docker/volumes.release-defaults"
  ln -s "$data_root/volumes" "$release/docker/volumes"
fi
test "$(readlink -f "$release/docker/volumes")" = "$(readlink -f "$data_root/volumes")"

ln -sfn "$release" "$HOME/services/ione-dify/current"
install -Dm644 docker/systemd/ione-dify.service \
  ~/.config/systemd/user/ione-dify.service
systemctl --user daemon-reload
systemctl --user enable --now ione-dify.service
```

Do not start a release with a release-local `docker/volumes` directory. It
would isolate tenant RSA keys, uploads, Redis state, and plugin data from the
persistent deployment. After switching an already-running release from a local
directory to the persistent symlink, use `docker compose up -d --force-recreate`
once so existing bind mounts are reattached to the corrected path.

The Compose services use restart policies for process-level recovery. The
systemd unit provides a stable lifecycle entry point for startup, reload and
controlled shutdown; Dify is intentionally not placed inside a Bench container.
