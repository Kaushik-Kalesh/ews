import os
import requests
from urllib.parse import quote

def get_arrow_offer(part_no):
    try:
        login = os.environ["ARROW_LOGIN"]
        api_key = os.environ["ARROW_ACCESS_TOKEN"]
        url = f"http://api.arrow.com/itemservice/v4/en/search/token?login={login}&apikey={api_key}&search_token={quote(part_no)}&utm_currency=INR"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()

        for part_data in data.get("itemserviceresult", {}).get("data", []):
            for part in part_data.get("PartList", []):
                inv_org = part.get("InvOrg")
                if not inv_org:
                    continue
                for site in inv_org.get("webSites", []):
                    if site.get("name") == "arrow.com":
                        for source in site.get("sources", []):
                            for sp in source.get("sourceParts", []):
                                for price in sp.get("Prices", {}).get("resaleList", []):
                                    if price.get("minQty") == 1:
                                        detail_url = next((r["uri"] for r in sp.get("resources", []) if r.get("type") == "detail"), None)
                                        return {
                                            "currency": "INR",
                                            "price": price["price"],
                                            "site": "Arrow",
                                            "url": detail_url
                                        }
    except Exception:
        return None
