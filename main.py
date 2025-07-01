from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from urllib.parse import quote
from dotenv import load_dotenv
import os
import traceback

app = Flask(__name__)
CORS(app)
load_dotenv()

@app.route("/")
def home():
    return send_from_directory('.', 'index.html')

def print_error(e):
    """
    Print the error message and stack trace.
    Args:
        e (Exception): The exception to print.
    """    
    traceback.print_exc()

def get_octopart(part_no):
    try:
        URL = "https://api.nexar.com/graphql"
        ACCESS_TOKEN = os.getenv("OCTOPART_ACCESS_TOKEN")

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        query = """
        query BasicQuery(
        $searchTerm: String
        $limit: Int
        $inStockOnly: Boolean
        $countryCode: String!
        $currencyCode: String!
        ) {
        supSearchMpn(
            q: $searchTerm
            limit: $limit
            inStockOnly: $inStockOnly
            country: $countryCode
            currency: $currencyCode
        ) {
            hits
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

        variables = {
            "searchTerm": part_no,
            "limit": 1,
            "inStockOnly": True,
            "countryCode": "IN",
            "currencyCode": "INR"
        }

        response = requests.post(URL, headers=headers, json={
            "query": query,
            "variables": variables
        })

        data = response.json()
        
        lowest_price = float('inf')
        best_offer = None

        for result in data["data"]["supSearchMpn"]["results"]:
            for seller in result["part"]["sellers"]:
                company = seller["company"]["name"]
                for offer in seller["offers"]:
                    for price in offer["prices"]:
                        if price["quantity"] == 1:  # MOQ check
                            p = price.get("convertedPrice") or price["price"]
                            if p < lowest_price:
                                lowest_price = p
                                best_offer = {
                                    "currency": "INR",                                    
                                    "price": p,                                                                        
                                    "site": company,
                                    "url": offer["clickUrl"],
                                }
        return best_offer
    except Exception as e:
        print_error(e)
        return None

def update_env_token(var_name, token):
    """
    Update or add a token variable in the .env file.
    Args:
        var_name (str): The environment variable name (e.g., "TI_ACCESS_TOKEN").
        token (str): The token value to set.
    """
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if not line.endswith('\n'):
                    line += '\n'
                if line.startswith(f"{var_name}="):
                    lines.append(f"{var_name}={token}\n")
                    found = True
                else:
                    lines.append(line)
    if not found:
        if lines and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines.append(f"{var_name}={token}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)

def get_ti_access_token():
    """
    Get a fresh TI access token using client credentials.
    """
    url = "https://transact.ti.com/v1/oauth/accesstoken"
    client_id = os.getenv("TI_CLIENT_ID")
    client_secret = os.getenv("TI_CLIENT_SECRET")
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    token = response.json()["access_token"]
    update_env_token("TI_ACCESS_TOKEN", token)
    return token

def get_ti(part_no):
    try:
        ACCESS_TOKEN = os.getenv("TI_ACCESS_TOKEN")
        if not ACCESS_TOKEN:
            ACCESS_TOKEN = get_ti_access_token()
        URL = f'https://transact.ti.com/v2/store/products?gpn={quote(part_no)}&currency=INR&page=0&size=2'   

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.get(URL, headers=headers)
        if response.status_code == 401:
            # Token expired or invalid, fetch a new one and retry
            ACCESS_TOKEN = get_ti_access_token()
            headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
            response = requests.get(URL, headers=headers)

        data = response.json()        
        
        for pb in data["content"][0]["pricing"][0]["priceBreaks"]:
            if pb["priceBreakQuantity"] == 1:                
                return {
                    "currency": data["content"][0]["pricing"][0]["currency"],
                    "price": pb["price"],
                    "site": "TI",
                    "url": data["content"][0]["buyNowUrl"]
                }
    except Exception as e:
        print_error(e)
        return None

def get_mouser(part_no):
    try:
        ACCESS_TOKEN = os.getenv("MOUSER_ACCESS_TOKEN")
        URL = f'https://api.mouser.com/api/v1/search/partnumber?apiKey={ACCESS_TOKEN}'   

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.post(URL, headers=headers, json={
            "SearchByPartRequest": {
                "mouserPartNumber": part_no,                
                "mouserPaysCustomsAndDuties": False
            }
        })
        data = response.json()    

        for pb in data["SearchResults"]["Parts"][0]["PriceBreaks"]:
            if pb["Quantity"] == 1:                
                return {
                    "currency": pb["Currency"],
                    "price": pb["Price"][1:].replace(",", ""),
                    "site": "Mouser",
                    "url": data["SearchResults"]["Parts"][0]["ProductDetailUrl"]
                }
    except Exception as e:
        print_error(e)
        return None

def get_digikey_access_token():
    url = "https://api.digikey.com/v1/oauth2/token"
    client_id = os.getenv("DIGIKEY_CLIENT_ID")
    client_secret = os.getenv("DIGIKEY_CLIENT_SECRET")
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    response = requests.post(url, data=data, headers=headers)
    response.raise_for_status()
    token = response.json()["access_token"]
    update_env_token("DIGIKEY_ACCESS_TOKEN", token)
    return token

def get_digikey(part_no):
    try:
        ACCESS_TOKEN = os.getenv("DIGIKEY_ACCESS_TOKEN")
        if not ACCESS_TOKEN:
            ACCESS_TOKEN = get_digikey_access_token()
        URL = f"https://api.digikey.com/products/v4/search/{quote(part_no)}/pricing"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "X-DIGIKEY-Client-Id": os.getenv("DIGIKEY_CLIENT_ID"),
            "X-DIGIKEY-Locale-Site": "IN",
            "X-DIGIKEY-Locale-Language": "EN",
            "X-DIGIKEY-Locale-Currency": "INR",
            "Content-Type": "application/json"
        }
        response = requests.get(URL, headers=headers)
        if response.status_code == 401:
            # Token expired, refresh and retry
            ACCESS_TOKEN = get_digikey_access_token()
            headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
            response = requests.get(URL, headers=headers)
        
        data = response.json()    

        for pb in data["ProductPricings"][0]["ProductVariations"][0]["StandardPricing"]:
            if pb["BreakQuantity"] == 1:                
                return {
                    "currency": "INR",
                    "price": pb["UnitPrice"],
                    "site": "DigiKey",
                    "url": data["ProductPricings"][0]["ProductUrl"]
                }
    except Exception as e:
        print_error(e)
        return None

def get_arrow(part_no):
    try:
        LOGIN = os.getenv("ARROW_LOGIN")
        ACCESS_TOKEN = os.getenv("ARROW_ACCESS_TOKEN")
        URL = f'http://api.arrow.com/itemservice/v4/en/search/token?login={LOGIN}&apikey={ACCESS_TOKEN}&search_token={quote(part_no)}&utm_currency=INR'  

        response = requests.get(URL)
        data = response.json()    

        itemserviceresult = data.get("itemserviceresult", {})
        data_list = itemserviceresult.get("data", [])
        if not data_list:
            return None

        for part_data in data_list:
            part_list = part_data.get("PartList", [])
            for part in part_list:
                inv_org = part.get("InvOrg")
                if not inv_org:
                    continue
                web_sites = inv_org.get("webSites", [])
                for e in web_sites:
                    if e.get("name") == "arrow.com":
                        sources = e.get("sources", [])
                        for source in sources:
                            source_parts = source.get("sourceParts", [])
                            for source_part in source_parts:
                                prices = source_part.get("Prices", {}).get("resaleList", [])
                                for price in prices:
                                    if price.get("minQty") == 1:
                                        detail_url = None
                                        for r in source_part.get("resources", []):
                                            if r.get("type") == "detail":
                                                detail_url = r.get("uri")
                                                break
                                        return {
                                            "currency": "INR",
                                            "price": price.get("price"),
                                            "site": "Arrow",
                                            "url": detail_url
                                        }
        return None
    except Exception as e:
        print_error(e)
        return None

def get_lcsc(part_no):
    try:
        URL = f'https://transact.ti.com/v2/store/products?gpn={quote(part_no)}&currency=INR&page=0&size=2'   
        ACCESS_TOKEN = os.getenv("TI_ACCESS_TOKEN")

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        response = requests.get(URL, headers=headers)
        data = response.json()        
        
        for pb in data["content"][0]["pricing"][0]["priceBreaks"]:
            if pb["priceBreakQuantity"] == 1:                
                return {
                    "price": pb["price"],
                    "site": "TI",
                    "url": data["content"][0]["buyNowUrl"]
                }
    except Exception as e:
        print(e.message)
        traceback.print_exc()
        return None

@app.route("/search")
def search():
    try:
        res = []
        part_no = request.args.get("part_no")

        offers = [
            # get_octopart(part_no),
            get_ti(part_no),
            get_mouser(part_no),
            get_digikey(part_no),
            get_arrow(part_no),
            # get_lcsc(part_no),
        ]
        print(offers[1])

        # Filter out None offers
        valid_offers = [offer for offer in offers if offer]

        if not valid_offers:
            return jsonify({"error": "No prices found for this part."})

        # Find the best offer
        best_offer = min(valid_offers, key=lambda x: float(x["price"]))

        for offer in valid_offers:
            res.append({
                "is_best": offer == best_offer,
                "currency": offer.get("currency", ""),
                "lowest_price": offer.get("price", ""),
                "site": offer.get("site", ""),
                "url": offer.get("url", ""),
            })

        return jsonify(res)
    except Exception as e:
        print_error(e)
        return jsonify({
            "error": str(e),
        })
    

if __name__ == "__main__":
    app.run(debug=True)