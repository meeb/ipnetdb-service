FROM openresty/openresty:1.19.9.1-4-bullseye

ARG ARCH="amd64"
ARG S6_VERSION="2.2.0.3"

ENV DEBIAN_FRONTEND="noninteractive" \
    HOME="/root" \
    LANGUAGE="en_US.UTF-8" \
    LANG="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8" \
    TERM="xterm" \
    S6_EXPECTED_SHA256="a7076cf205b331e9f8479bbb09d9df77dbb5cd8f7d12e9b74920902e0c16dd98" \
    S6_DOWNLOAD="https://github.com/just-containers/s6-overlay/releases/download/v${S6_VERSION}/s6-overlay-${ARCH}.tar.gz"


# Install third party software
RUN set -x && \
    apt-get update && \
    apt-get -y --no-install-recommends install locales && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen en_US.UTF-8 && \
    # Install required distro packages
    apt-get -y --no-install-recommends install curl ca-certificates binutils && \
    # Install s6
    curl -L ${S6_DOWNLOAD} --output /tmp/s6-overlay-${ARCH}.tar.gz && \
    sha256sum /tmp/s6-overlay-${ARCH}.tar.gz && \
    echo "${S6_EXPECTED_SHA256}  /tmp/s6-overlay-${ARCH}.tar.gz" | sha256sum -c - && \
    tar xzf /tmp/s6-overlay-${ARCH}.tar.gz -C / && \
    # Clean up
    rm -rf /tmp/s6-overlay-${ARCH}.tar.gz && \
    apt-get -y autoremove --purge curl binutils

# Copy app
COPY app /app

# Add Pipfile
COPY Pipfile /app/Pipfile
COPY Pipfile.lock /app/Pipfile.lock

# Switch workdir to the the app
WORKDIR /app

# Set up the app
RUN set -x && \
    apt-get update && \
    # Install required distro packages
    apt-get -y --no-install-recommends install \
        cron \
        anacron \
        python3 \
        python3-setuptools \
        python3-pip \
        openresty-opm \
        libmaxminddb-dev && \
    # Install pipenv
    pip3 --disable-pip-version-check install pipenv && \
    # Create a 'app' user which the application will run as
    groupadd app && \
    useradd -M -d /app -s /bin/bash -g app app && \
    # Install Pipenv Python packages
    pipenv install --system && \
    # Install opm packages
    opm install leafo/geoip && \
    # Make sure required directories are created
    mkdir -p /ipnetdb && \
    chmod 0755 /ipnetdb && \
    chown app:app /ipnetdb && \
    # Clean up
    rm -rf /etc/cron.*/* && \
    rm /app/Pipfile && \
    rm /app/Pipfile.lock && \
    pipenv --clear && \
    pip3 --disable-pip-version-check uninstall -y pipenv virtualenv && \
    apt-get -y autoremove && \
    apt-get -y autoclean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /var/cache/apt/* && \
    rm -rf /tmp/* && \
    # Pipenv leaves a bunch of stuff in /root, as we're not using it recreate it
    rm -rf /root && \
    mkdir -p /root && \
    chown root:root /root && \
    chmod 0700 /root

# Copy root
COPY config/root /

# Install the app into OpenResty
RUN set -x && \
    rm -rf /usr/local/openresty/nginx/conf/nginx.conf && \
    ln -s /app/nginx.conf /usr/local/openresty/nginx/conf/nginx.conf

# Create a healthcheck
HEALTHCHECK --interval=1m --timeout=10s CMD /app/healthcheck.py http://127.0.0.1/healthcheck

# ENVS and ports
EXPOSE 80

# Entrypoint, start s6 init
ENTRYPOINT ["/init"]
