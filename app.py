from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import math

app = Flask(__name__)

# Load associates data from JSON file and ensure barcodes are treated as strings
with open("names.json", "r") as f:
    associates_data = json.load(f)

# Create a mapping from barcode (as a string) to first name and login
barcode_to_info = {str(associate["barcode"]): f"{associate['first_name']} ({associate['login']})" for associate in associates_data}

# Default values for CE, MI, and Trans
total_headcount = 0  # Will be dynamically set
trans_count = 0  # Will be dynamically set

# Predefined roles
roles = {
    "Critical": {
        "Pit": 0,
        "CPT": 0,
        "Ship Clerk": 0,
        "DEA": 0,
        "Fluid PS": 0,
        "Main PS": 0,
        "Robotics Operator": 0,
    },
    "Non-Critical": {
        "Flats": 0,
        "MI": 0,
        "WS": 0,
        "Fluids": 0,
        "Main High Cap": 0,
        "Mid High Cap": 0,
        "Mid Cap": 0,
        "Trans": 0,
        "Carts": 0,
    }
}

# Store checked-in associates (now a dictionary to track roles)
associates = {}
trans_associates = {}  # Store associates working in Trans or Pit

@app.route("/")
def index():
    return render_template("index.html", associates=associates, trans_associates=trans_associates, roles=roles, total_headcount=total_headcount, trans_count=trans_count)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    global total_headcount, trans_count
    if request.method == "POST":
        ce = int(request.form["CE"])
        mi = int(request.form["MI"])
        trans = int(request.form["Trans"])

        total_headcount = math.ceil(ce / 550)  # Adjust total headcount, rounding up
        trans_count = math.ceil(trans / 1000)  # Number of people needed for Trans, rounding up
        
        if trans > trans_count * 1000:
            return jsonify({"error": "Transitional Employees cannot exceed " + str(trans_count * 1000)}), 400
        
        return redirect(url_for("assign_roles"))
    return render_template("settings.html", total_headcount=total_headcount, trans_count=trans_count)

@app.route("/assign_roles", methods=["GET", "POST"])
def assign_roles():
    global roles
    if request.method == "POST":
        assigned_total = sum(int(request.form[role]) for category in roles for role in roles[category])
        if assigned_total != total_headcount:
            return jsonify({"error": "Total assigned must equal total headcount"}), 400

        for category in roles:
            for role in roles[category]:
                roles[category][role] = int(request.form[role])
        return redirect(url_for("index"))
    return render_template("assign_roles.html", roles=roles, total_headcount=total_headcount)

@app.route("/checkin", methods=["POST"])
def checkin():
    badge_id = request.form["badge_id"]
    role = request.form.get("role")
    name = barcode_to_info.get(badge_id, "Unknown")

    if name in associates or name in trans_associates:
        return jsonify({"error": "Badge already scanned"}), 400

    if role in ["Trans", "Pit"]:
        trans_associates[name] = role  # Store associate in trans workers counter
    else:
        associates[name] = role  # Store associate in regular check-ins
    
    return redirect(url_for("index"))

@app.route("/remove", methods=["POST"])
def remove():
    name = request.form["name"]
    if name in associates:
        del associates[name]
    elif name in trans_associates:
        del trans_associates[name]
    return redirect(url_for("index"))

@app.route("/move", methods=["POST"])
def move():
    name = request.form["name"]
    new_role = request.form["new_role"]
    if name in associates:
        del associates[name]
        if new_role in ["Trans", "Pit"]:
            trans_associates[name] = new_role
        else:
            associates[name] = new_role
    elif name in trans_associates:
        del trans_associates[name]
        if new_role in ["Trans", "Pit"]:
            trans_associates[name] = new_role
        else:
            associates[name] = new_role
    return redirect(url_for("index"))

@app.route("/reset", methods=["POST"])
def reset():
    global associates, trans_associates
    associates = {}  # Reset all checked-in associates
    trans_associates = {}  # Reset all trans workers
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
