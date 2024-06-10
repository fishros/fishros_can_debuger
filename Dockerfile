FROM ubuntu:jammy

RUN apt-get update && apt-get install -y \
    wget \
    fonts-wqy-zenhei \
    libgl1 \
    libegl1 \
    && apt-get clean && apt-get autoclean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY "dist-for-docker/fishros_can_debuger_linux_amd64" /fishros_can_debuger
RUN chmod +x /fishros_can_debuger
ENTRYPOINT ["/fishros_can_debuger"]

# docker run -it --rm --privileged -v /dev:/dev  -v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=unix$DISPLAY fishbot-tool