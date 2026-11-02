#!/usr/bin/env bash
# DirectCare blog: set up the DGX Spark to write and publish the daily post for free.
#   - Ollama + gpt-oss:120b (local model, ~65 GB, served on 127.0.0.1:11434)
#   - Node.js (the workflow deploys with `npx vercel`)
#   - GitHub Actions self-hosted runner labelled "dgx", installed as a service
#
# Usage on the DGX:  RUNNER_TOKEN=<registration token> bash dgx-blog-setup.sh
# The registration token comes from:
#   gh api -X POST repos/directcareai26/directcare-home/actions/runners/registration-token -q .token
# (valid for one hour, single use).
set -euo pipefail

REPO_URL="https://github.com/directcareai26/directcare-home"
MODEL="${MODEL:-gpt-oss:120b}"
RUNNER_DIR="$HOME/actions-runner"
: "${RUNNER_TOKEN:?Set RUNNER_TOKEN to a fresh runner registration token}"

[ "$(uname -m)" = "aarch64" ] || echo "warning: expected aarch64 (DGX Spark), got $(uname -m)"

echo "==> System packages"
sudo apt-get update -qq
sudo apt-get install -y -qq curl git jq python3 python3-venv ca-certificates >/dev/null

echo "==> Node.js 22 (for npx vercel)"
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - >/dev/null
  sudo apt-get install -y -qq nodejs >/dev/null
fi
node --version

echo "==> Ollama"
if ! command -v ollama >/dev/null; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
# Keep the model loaded between the daily run's retries; listen on localhost only.
sudo mkdir -p /etc/systemd/system/ollama.service.d
printf '[Service]\nEnvironment="OLLAMA_HOST=127.0.0.1:11434"\nEnvironment="OLLAMA_KEEP_ALIVE=30m"\n' \
  | sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
sudo systemctl restart ollama
sleep 3

echo "==> Pulling $MODEL (large download, one time)"
ollama pull "$MODEL"

echo "==> Smoke test: model returns JSON"
curl -sf http://127.0.0.1:11434/v1/chat/completions -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"response_format\":{\"type\":\"json_object\"},\"messages\":[{\"role\":\"user\",\"content\":\"Return {\\\"ok\\\": true} as JSON.\"}]}" \
  | jq -r '.choices[0].message.content'

echo "==> GitHub Actions runner"
mkdir -p "$RUNNER_DIR" && cd "$RUNNER_DIR"
if [ ! -f ./config.sh ]; then
  VER=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/^v//')
  curl -fsSL -o runner.tgz "https://github.com/actions/runner/releases/download/v${VER}/actions-runner-linux-arm64-${VER}.tar.gz"
  tar xzf runner.tgz && rm runner.tgz
  sudo ./bin/installdependencies.sh >/dev/null
fi
if [ ! -f .runner ]; then
  ./config.sh --unattended --url "$REPO_URL" --token "$RUNNER_TOKEN" \
    --name dgx-spark --labels dgx --work _work --replace
fi
sudo ./svc.sh install "$USER" >/dev/null 2>&1 || true
sudo ./svc.sh start
sudo ./svc.sh status | head -5

echo
echo "DONE. Runner 'dgx-spark' (label: dgx) is online and $MODEL is served on 127.0.0.1:11434."
