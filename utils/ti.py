import os
import requests
from urllib.parse import quote
from token_cache import get_token, set_token

def get_ti_token():
    token = get_token("TI")
    if token:
        return token

    url = "https://transact.ti.com/v1/oauth/accesstoken"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.environ["TI_CLIENT_ID"],
        "client_secret": os.environ["TI_CLIENT_SECRET"]
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(url, data=data, headers=headers)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    set_token("TI", token, 3600)
    return token

def get_ti_offer(part_no):
    try:
        token = get_ti_token()
        url = f'https://transact.ti.com/v2/store/products?gpn={quote(part_no)}&currency=INR&page=0&size=2'
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        p = data["content"][0]["pricing"][0]

        for pb in p["priceBreaks"]:
            if pb["priceBreakQuantity"] == 1:
                return {
                    "currency": p["currency"],
                    "price": pb["price"],
                    "site": "TI",
                    "url": data["content"][0]["buyNowUrl"]
                }
    except Exception:
        return None
