
FROM python:3.8-slim-buster
WORKDIR /app 

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# 1. पुरानी Debian Buster रिपॉजिटरीज़ को Archive URL पर स्विच करने का फिक्स (404 Error का इलाज)
RUN sed -i 's/deb.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/archive.debian.org/g' /etc/apt/sources.list && \
    sed -i '/stretch-updates/d' /etc/apt/sources.list

# 2. अब apt बिना किसी 404 एरर के ffmpeg और ffprobe दोनों को एक साथ इंस्टॉल कर लेगा
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ffprobe git

COPY . . 

CMD python3 main.py
