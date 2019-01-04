Installation
=======

Operating system is Ubuntu 16.04

First install Google Chrome dependencies

```
apt-get update && apt-get install --no-install-recommends -y \
  ca-certificates \
  curl \
  fontconfig \
  fonts-liberation \
  gconf-service \
  git \
  libappindicator1 \
  libasound2 \
  libatk1.0-0 \
  libc6 \
  libcairo2 \
  libcups2 \
  libdbus-1-3 \
  libexpat1 \
  libfontconfig1 \
  libgcc1 \
  libgconf-2-4 \
  libgdk-pixbuf2.0-0 \
  libglib2.0-0 \
  libgtk-3-0 \
  libnspr4 \
  libnss3 \
  libpango-1.0-0 \
  libpangocairo-1.0-0 \
  libstdc++6 \
  lib\x11-6 \
  libx11-xcb1 \
  libxcb1 \
  libxcomposite1 \
  libxcursor1 \
  libxdamage1 \
  libxext6 \
  libxfixes3 \
  libxi6 \
  libxrandr2 \
  libxrender1 \
  libxss1 \
  libxtst6 \
  locales \
  lsb-release \
  unzip \
  wget \
  xdg-utils
```

The following packages are required if using Pocketsphinx for deciphering

```
apt-get update && apt-get install --no-install-recommends -y \
  build-essential \
  ffmpeg \
  swig \
  software-properties-common \
  curl
```

Install Python 3.6 if it's not already

```
add-apt-repository ppa:jonathonf/python-3.6 \
  && apt-get remove -y software-properties-common \
  && apt autoremove -y \
  && apt-get update \
  && apt-get install -y python3.6 \
     python3.6-dev
```

Install PyPI
```
 curl -o /tmp/get-pip.py "https://bootstrap.pypa.io/get-pip.py" \
   && python3.6 /tmp/get-pip.py \
   && apt-get remove -y curl \
   && apt autoremove -y
```

Finally, install nonoCAPTCHA

   `pip install nonocaptcha`
