from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from utils.ti import get_ti_offer
from utils.mouser import get_mouser_offer
from utils.digikey import get_digikey_offer
from utils.arrow import get_arrow_offer
from utils.octopart import get_octopart_offer

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/search")
def search():
    part_no = request.args.get("part_no")
    offers = [
        get_octopart_offer(part_no),
        get_ti_offer(part_no),
        get_mouser_offer(part_no),
        get_digikey_offer(part_no),
        get_arrow_offer(part_no)
    ]
    offers = [o for o in offers if o]
    if not offers:
        return jsonify({"error": "No offers found."})
    best = min(offers, key=lambda x: float(x["price"]))
    return jsonify([
        {**o, "is_best": o == best}
        for o in offers
    ])
