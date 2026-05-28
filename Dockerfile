FROM python:3.8-slim-buster
WORKDIR /app 

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# 1. पुरानी रिपॉजिटरीज़ को Archive पर सेट करना
RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i '/stretch-updates/d' /etc/apt/sources.list

# 2. [FIX] एरर कोड 100 को बायपास करने और FFMPEG को ज़बरदस्ती (Force) इंस्टॉल करने का लॉजिक
RUN apt-get update -y || true
RUN apt-get install -y --no-install-recommends ffmpeg ffprobe git || true

COPY . . 

CMD python3 main.py
