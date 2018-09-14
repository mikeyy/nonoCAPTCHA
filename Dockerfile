FROM ubuntu:16.04

RUN apt-get update \
    && apt-get install -y \
    libpangocairo-1.0-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libcups2 \
    libxss1 \
    libxrandr2 \
    libgconf-2-4 \
    libasound2 \
    libasound2-dev \
    libatk1.0-0 \
    libgtk-3-0 \
    gconf-service \
    libappindicator1 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libnspr4 \
    libpango-1.0-0 \
    lipulse-dev \
    libstdc++6 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxfixes3 \
    libxrender1 \
    libxtst6 \
    ca-certificates \
    fonts-liberation \
    lsb-release \
    xdg-utils \
    build-essential \
    ffmpeg \
    software-properties-common curl \
    && add-apt-repository ppa:jonathonf/python-3.6 \
    && apt-get remove -y software-properties-common \
    && apt autoremove -y \
    && apt-get update \
    && apt-get install -y python3.6 \
    python3.6-dev \
    && curl -o /tmp/get-pip.py "https://bootstrap.pypa.io/get-pip.py" \
    && python3.6 /tmp/get-pip.py \
    && apt-get remove -y curl \
    && apt autoremove -y \
    && pip install nonocaptcha

COPY examples/app.py /nonocaptcha
COPY config.py /nonocaptcha

RUN python3.6 /nonocaptcha/app.py

EXPOSE 5000