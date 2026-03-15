#!/bin/sh
set -eu

require_var() {
  var_name="$1"
  eval "var_value=\${$var_name:-}"

  if [ -z "$var_value" ]; then
    echo "Required variable is missing: $var_name" >&2
    exit 1
  fi
}

require_var DEPLOY_HOST
require_var DEPLOY_USER
require_var DEPLOY_BASE_PATH
require_var DEPLOY_TARGET_DIR

REMOTE="${DEPLOY_USER}@${DEPLOY_HOST}"
SSH_OPTIONS="-o StrictHostKeyChecking=yes"

echo "Preparing remote directory ${DEPLOY_TARGET_DIR}"
ssh $SSH_OPTIONS "$REMOTE" "mkdir -p '$DEPLOY_TARGET_DIR' '$DEPLOY_TARGET_DIR/backend/app/data'"

echo "Syncing project files to ${REMOTE}:${DEPLOY_TARGET_DIR}"
rsync -az --delete \
  --exclude ".git" \
  --exclude ".env" \
  --exclude ".docker-tmp" \
  --exclude ".venv/" \
  --exclude "__pycache__/" \
  --exclude "backend/app/data/" \
  --exclude "web/node_modules/" \
  --exclude "web/.svelte-kit/" \
  --exclude "web/build/" \
  ./ "${REMOTE}:${DEPLOY_TARGET_DIR}/"
ssh $SSH_OPTIONS "$REMOTE" "cd '$DEPLOY_TARGET_DIR' && pwd && ls -la"


if [ -n "${DEPLOY_ENV_FILE:-}" ]; then
  tmp_env_file="$(mktemp)"
  if [ -f "$DEPLOY_ENV_FILE" ]; then
    cp "$DEPLOY_ENV_FILE" "$tmp_env_file"
  else
    printf '%s' "$DEPLOY_ENV_FILE" > "$tmp_env_file"
  fi
  scp $SSH_OPTIONS "$tmp_env_file" "${REMOTE}:${DEPLOY_TARGET_DIR}/.env"
  rm -f "$tmp_env_file"
  echo "Uploaded .env from DEPLOY_ENV_FILE"
else
  echo "DEPLOY_ENV_FILE is not set, keeping existing remote .env if present"
fi

REMOTE_APP_UP_CMD="${REMOTE_APP_UP_CMD:-docker compose up -d --build --pull always --remove-orphans}"

echo "Starting deployment on remote server"
ssh $SSH_OPTIONS "$REMOTE" "cd '$DEPLOY_TARGET_DIR' && $REMOTE_APP_UP_CMD"

echo "Deployment finished successfully"
