# 1. लेटेस्ट और बिल्कुल स्टेबल पाइथन इमेज (Debian Bookworm आधारित)
FROM python:3.11-slim

# 2. वर्किंग डायरेक्टरी सेट करें
WORKDIR /app

# 3. requirements.txt को कॉपी करें और लाइब्रेरीज़ इंस्टॉल करें
COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# 4. सिर्फ ffmpeg और git इंस्टॉल करें (ffprobe इसके साथ अपने आप आ जाएगा)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# 5. आपके प्रोजेक्ट का सारा कोड कॉपी करना
COPY . .

# 6. बॉट को शुरू करने की मुख्य कमांड
CMD ["python3", "main.py"]
