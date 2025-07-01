import os
import requests
from urllib.parse import quote
from token_cache import get_token, set_token

def get_digikey_token():
    token = get_token("DIGIKEY")
    if token:
        return token

    url = "https://api.digikey.com/v1/oauth2/token"
    data = {
        "client_id": os.environ["DIGIKEY_CLIENT_ID"],
        "client_secret": os.environ["DIGIKEY_CLIENT_SECRET"],
        "grant_type": "client_credentials"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(url, data=data, headers=headers)
    r.raise_for_status()
    token = r.json()["access_token"]
    set_token("DIGIKEY", token, 3600)
    return token

def get_digikey_offer(part_no):
    try:
        token = get_digikey_token()
        url = f"https://api.digikey.com/products/v4/search/{quote(part_no)}/pricing"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-DIGIKEY-Client-Id": os.environ["DIGIKEY_CLIENT_ID"],
            "X-DIGIKEY-Locale-Site": "IN",
            "X-DIGIKEY-Locale-Language": "EN",
            "X-DIGIKEY-Locale-Currency": "INR",
            "Content-Type": "application/json"
        }
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()

        for pb in data["ProductPricings"][0]["ProductVariations"][0]["StandardPricing"]:
            if pb["BreakQuantity"] == 1:
                return {
                    "currency": "INR",
                    "price": pb["UnitPrice"],
                    "site": "DigiKey",
                    "url": data["ProductPricings"][0]["ProductUrl"]
                }
    except Exception:
        return None
