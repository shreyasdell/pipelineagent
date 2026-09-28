# Base image – Microsoft's base devcontainer image (git, curl, zsh, vscode user).
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04
ENV DEBIAN_FRONTEND=noninteractive

# ── System packages and Python ───────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
      ripgrep \
      jq \
      tree \
      ca-certificates \
      gnupg \
      python3 \
      python3-pip \
      python3-venv \
    && rm -rf /var/lib/apt/lists/*


# ── Node 22 via NodeSource ────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN npm config set strict-ssl false

# Useful developer tools
RUN npm install -g \
    typescript \
    ts-node \
    eslint \
    prettier \
    npm-check-updates

# ── GitHub CLI ────────────────────────────────────────────────────────────────
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# ── Devin CLI ─────────────────────────────────────────────
USER vscode
RUN curl -fsSL https://cli.devin.ai/install.sh -o /tmp/devin-install.sh \
    && sed -i '${/^"\$VERSION_DIR\/bin\/\$COMPILED_BIN_NAME" setup$/d}' /tmp/devin-install.sh \
    && ! tail -n 1 /tmp/devin-install.sh | grep -q 'setup$' \
    && bash /tmp/devin-install.sh \
    && rm -f /tmp/devin-install.sh \
    && test -x "$(readlink -f "$HOME/.local/bin/devin")"

USER root

# Node ships its own compiled-in CA list and ignores /etc/ssl/certs, so this is
# required in addition to whatever install-corp-ca.sh puts in the trust store.
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt \
    GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

ENV PATH=/home/vscode/.local/bin:${PATH}

WORKDIR /workspaces