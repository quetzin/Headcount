from flask import Flask, render_template, request, redirect, url_for, jsonify
import json

app = Flask(__name__)

# Load associates data from JSON file
with open("names.json", "r") as f:
    associates_data = json.load(f)

# Create a mapping from barcode to first name and login
barcode_to_info = {str(associate["barcode"]): f"{associate['first_name']} ({associate['login']})" for associate in associates_data}

# Default values for CE, MI, and Trans
total_headcount = 0  # Will be dynamically set
trans_count = 0  # Will be dynamically set

# Store checked-in associates
associates = []
trans_associates = []  # Separate list for associates working in Trans

@app.route("/")
def index():
    return render_template("index.html", associates=associates, trans_associates=trans_associates, total_headcount=total_headcount)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    global total_headcount, trans_count
    if request.method == "POST":
        ce = int(request.form["CE"])
        mi = int(request.form["MI"])
        trans = int(request.form["Trans"])

        total_headcount = ce // 550  # Adjust total headcount
        trans_count = trans // 1000  # Number of people needed for Trans
        return redirect(url_for("index"))
    return render_template("settings.html", total_headcount=total_headcount, trans_count=trans_count)

@app.route("/checkin", methods=["POST"])
def checkin():
    badge_id = request.form["badge_id"]
    in_trans = request.form.get("in_trans") == "on"
    name = barcode_to_info.get(badge_id, "Unknown")

    if name in associates or name in trans_associates:
        return jsonify({"error": "Badge already scanned"}), 400

    if in_trans:
        trans_associates.append(name)
    else:
        if len(associates) >= total_headcount:
            return jsonify({"error": "Headcount limit reached"}), 400
        associates.append(name)

    return redirect(url_for("index"))

@app.route("/remove", methods=["POST"])
def remove():
    name = request.form["name"]
    if name in associates:
        associates.remove(name)
    elif name in trans_associates:
        trans_associates.remove(name)
    return redirect(url_for("index"))

@app.route("/move", methods=["POST"])
def move():
    name = request.form["name"]
    if name in associates:
        associates.remove(name)
        trans_associates.append(name)
    elif name in trans_associates:
        trans_associates.remove(name)
        associates.append(name)
    return redirect(url_for("index"))

@app.route("/reset", methods=["POST"])
def reset():
    global associates, trans_associates
    associates = []
    trans_associates = []
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)