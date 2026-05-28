# 1. बिल्कुल लेटेस्ट और स्टेबल पाइथन इमेज (Debian Bookworm पर आधारित)
FROM python:3.11-slim

# 2. वर्किंग डायरेक्टरी सेट करें
WORKDIR /app

# 3.requirements.txt कॉपी करें और लाइब्रेरीज़ इंस्टॉल करें
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# 4. लेटेस्ट एक्टिव सर्वर से ffmpeg, ffprobe और git को बिना किसी एरर के इंस्टॉल करना
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg ffprobe git && \
    rm -rf /var/lib/apt/lists/*

# 5. आपकी भेजी हुई सभी फाइलें (main.py, handlers.py, utils.py आदि) कॉपी करना
COPY . .

# 6. बॉट को चालू करने की सही कमांड (main.py के हिसाब से)
CMD ["python3", "main.py"]
