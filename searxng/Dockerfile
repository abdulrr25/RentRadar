FROM searxng/searxng:latest

COPY settings.yml /etc/searxng/settings.yml

# Bake a unique secret_key into this build instead of shipping the git
# placeholder — SearXNG uses it to sign its own session tokens. Low-stakes
# for a private, single-caller instance, but free to do properly. Uses
# python3 (already in the base image) rather than openssl, which may not be.
RUN python3 -c "import secrets; print(secrets.token_hex(32))" > /tmp/secret && \
    sed -i "s/secret_key: \"changeme\"/secret_key: \"$(cat /tmp/secret)\"/" /etc/searxng/settings.yml && \
    rm /tmp/secret

# The base image already EXPOSEs 8080 and runs uwsgi on it — Render's Docker
# runtime auto-detects the exposed port and routes to it, no $PORT wiring
# needed (unlike Render's native Python/Node runtimes).
