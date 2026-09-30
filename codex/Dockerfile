# Codex play arm: plays one slot's window with the OpenAI Codex CLI instead of
# the free NVIDIA model, through the same gr.py client and the same prompt.
FROM node:22-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g @openai/codex@0.158.0 \
 && npm cache clean --force
COPY play.sh codex_digest.py /opt/gr-codex/
USER 1000:1000
ENV HOME=/tmp/home CODEX_HOME=/tmp/home/.codex
ENTRYPOINT ["/bin/bash", "/opt/gr-codex/play.sh"]
