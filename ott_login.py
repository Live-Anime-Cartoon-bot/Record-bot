# ott_login.py

import requests
import json

# =========================
# Common Headers
# =========================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
    "Accept": "application/json",
    "Content-Type": "application/json"
}


# =========================
# SonyLiv
# =========================
def login_sonyliv(phone):
    try:
        url = "https://apiv2.sonyliv.com/AGL/1.6/A/IN/ENG/WEB/LOGIN"
        payload = {"mobileNumber": phone, "countryCode": "91"}
        r = requests.post(url, headers=HEADERS, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# Discovery+
# =========================
def login_discovery(phone):
    try:
        url = "https://ap2-prod-direct.discoveryplus.in/login"
        payload = {"mobileNumber": phone, "countryCode": "+91"}
        r = requests.post(url, headers=HEADERS, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# JioHotstar
# =========================
def login_jiohotstar(phone):
    try:
        url = "https://api.hotstar.com/login"
        payload = {"phone": phone}
        r = requests.post(url, headers=HEADERS, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# Tata Play
# =========================
def login_tataplay(phone):
    try:
        url = "https://api.tataplay.com/login"
        payload = {"mobile": phone}
        r = requests.post(url, headers=HEADERS, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# JioTV
# =========================
def login_jiotv(phone):
    try:
        url = "https://api.jiotv.com/login"
        payload = {"mobile": phone}
        r = requests.post(url, headers=HEADERS, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# Zee5
# =========================
def login_zee5(phone):
    try:
        url = "https://useraction.zee5.com/token"
        payload = {"phone": phone}
        r = requests.post(url, headers=HEADERS, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# Airtel Xstream
# =========================
def login_airtel(phone):
    try:
        url = "https://api.airtelxstream.in/login"
        payload = {"mobile": phone}
        r = requests.post(url, headers=HEADERS, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# Netflix
# =========================
def login_netflix(email, password):
    try:
        url = "https://www.netflix.com/login"
        payload = {
            "email": email,
            "password": password
        }
        r = requests.post(url, headers=HEADERS, data=payload)
        return {"status": "attempted"}
    except Exception as e:
        return {"error": str(e)}


# =========================
# YuppTV
# =========================
def login_yupptv(phone):
    try:
        url = "https://api.yupptv.com/login"
        payload = {"mobile": phone}
        r = requests.post(url, headers=HEADERS, json=payload)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# =========================
# Prime Video
# =========================
def login_prime(email, password):
    try:
        url = "https://www.amazon.in/ap/signin"
        payload = {
            "email": email,
            "password": password
        }
        r = requests.post(url, headers=HEADERS, data=payload)
        return {"status": "attempted"}
    except Exception as e:
        return {"error": str(e)}


# =========================
# All Login
# =========================
def login_all(phone):
    return {
        "SonyLiv": login_sonyliv(phone),
        "Discovery+": login_discovery(phone),
        "JioHotstar": login_jiohotstar(phone),
        "TataPlay": login_tataplay(phone),
        "JioTV": login_jiotv(phone),
        "Zee5": login_zee5(phone),
        "AirtelXstream": login_airtel(phone),
        "YuppTV": login_yupptv(phone)
    }


# =========================
# Direct Run
# =========================
if __name__ == "__main__":
    phone = input("Enter Phone Number: ")
    result = login_all(phone)

    print(json.dumps(result, indent=2))
