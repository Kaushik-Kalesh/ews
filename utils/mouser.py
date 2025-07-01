import os
import requests
from token_cache import get_token, set_token

def get_mouser_token():
    return os.environ.get("MOUSER_ACCESS_TOKEN")  # permanent API key

def get_mouser_offer(part_no):
    try:
        token = get_mouser_token()
        url = f"https://api.mouser.com/api/v1/search/partnumber?apiKey={token}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "SearchByPartRequest": {
                "mouserPartNumber": part_no,
                "mouserPaysCustomsAndDuties": False
            }
        }
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

        for pb in data["SearchResults"]["Parts"][0]["PriceBreaks"]:
            if pb["Quantity"] == 1:
                return {
                    "currency": pb["Currency"],
                    "price": pb["Price"][1:].replace(",", ""),
                    "site": "Mouser",
                    "url": data["SearchResults"]["Parts"][0]["ProductDetailUrl"]
                }
    except Exception:
        return None
