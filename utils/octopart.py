# utils/octopart.py

import os
import requests
from token_cache import get_token, set_token

URL = "https://api.nexar.com/graphql"

def get_octopart_token():
    token = get_token("OCTOPART")
    if token:
        return token

    auth_url = "https://identity.nexar.com/connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.environ["OCTOPART_CLIENT_ID"],
        "client_secret": os.environ["OCTOPART_CLIENT_SECRET"],
        "audience": "https://api.nexar.com"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(auth_url, data=data, headers=headers)
    response.raise_for_status()
    token_data = response.json()

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)
    set_token("OCTOPART", access_token, expires_in)

    return access_token

def get_octopart_offer(part_no):
    try:
        token = get_octopart_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        query = """
        query Search($q: String!) {
          supSearchMpn(q: $q, limit: 1, inStockOnly: true, country: "IN", currency: "INR") {
            results {
              part {
                mpn
                sellers {
                  company {
                    name
                  }
                  offers {
                    moq
                    clickUrl
                    prices {
                      quantity
                      price
                      currency
                      convertedPrice
                      convertedCurrency
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {"q": part_no}
        response = requests.post(URL, headers=headers, json={"query": query, "variables": variables})
        response.raise_for_status()
        data = response.json()

        lowest_price = float("inf")
        best_offer = None

        for result in data["data"]["supSearchMpn"]["results"]:
            for seller in result["part"]["sellers"]:
                site = seller["company"]["name"]
                for offer in seller["offers"]:
                    for p in offer["prices"]:
                        if p["quantity"] == 1:
                            price = p.get("convertedPrice") or p["price"]
                            if price < lowest_price:
                                lowest_price = price
                                best_offer = {
                                    "currency": p.get("convertedCurrency") or p["currency"],
                                    "price": price,
                                    "site": site,
                                    "url": offer["clickUrl"]
                                }

        return best_offer

    except Exception:
        return None
