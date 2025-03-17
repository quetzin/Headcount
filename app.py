from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import math
import os

app = Flask(__name__)

NAMES_FILE = "names.json"
ASSIGNED_ROLES_FILE = "assigned_roles.json"

def load_names():
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r") as f:
            return json.load(f)
    return []

def save_names(data):
    with open(NAMES_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_assigned_roles():
    if os.path.exists(ASSIGNED_ROLES_FILE):
        with open(ASSIGNED_ROLES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_assigned_roles():
    with open(ASSIGNED_ROLES_FILE, "w") as f:
        json.dump(assigned_roles, f, indent=4)

associates_data = load_names()
assigned_roles = load_assigned_roles()

barcode_to_info = {
    str(associate["barcode"]): f"{associate['first_name']} ({associate['login']})"
    for associate in associates_data
}

total_headcount = 0
trans_count = 0
roles = {
    "Critical": ["Pit", "CPT", "Ship Clerk", "DEA", "Fluid PS", "Main PS", "Robotics Operator", "Jackpot PS", "PA"],
    "Non-Critical": ["Flats", "MI", "WS", "Fluids", "Main High Cap", "Mid High Cap", "Mid Cap", "Trans", "Carts"]
}

associates = {}
trans_workers_count = 0
first_pa_checked_in = False

@app.route("/")
def index():
    pa_count = sum(1 for role in associates.values() if role == "PA")
    non_trans_checkins = sum(1 for role in associates.values() if role not in ["Pit", "Trans", "Robotics Operator"])

    if pa_count > 0:
        non_trans_checkins -= 1

    return render_template("index.html", 
                           associates=associates, 
                           assigned_roles=assigned_roles, 
                           total_headcount=total_headcount, 
                           trans_count=trans_count, 
                           trans_workers_count=trans_workers_count,
                           current_checkins=non_trans_checkins,
                           barcode_to_info=barcode_to_info,
                           roles=roles)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    global total_headcount, trans_count
    if request.method == "POST":
        ce = int(request.form.get("CE", 0))
        mi = int(request.form.get("MI", 0))
        trans = int(request.form.get("Trans", 0))
        total_headcount = math.ceil(ce / 550)
        trans_count = math.ceil(trans / 1000)
        return redirect(url_for("assign_roles"))
    return render_template("settings.html", total_headcount=total_headcount, trans_count=trans_count)

@app.route("/assign_roles", methods=["GET", "POST"])
def assign_roles():
    global assigned_roles
    if request.method == "POST":
        assigned_roles = {barcode: role for barcode, role in request.form.items()}
        save_assigned_roles()
        return redirect(url_for("index"))
    return render_template("assign_roles.html", assigned_roles=assigned_roles, roles=roles, associates_data=associates_data, total_headcount=total_headcount)

@app.route("/checkin", methods=["POST"])
def checkin():
    global trans_workers_count, first_pa_checked_in, associates
    badge_id = request.form["badge_id"]
    if badge_id in associates:
        return jsonify({"error": "Badge already scanned"}), 400
    if badge_id not in barcode_to_info:
        return render_template("add_associate.html", barcode=badge_id, roles=roles)
    assigned_role = assigned_roles.get(badge_id, "Unassigned")
    associates = {badge_id: assigned_role, **associates}
    if assigned_role in ["Pit", "Trans", "Robotics Operator"]:
        trans_workers_count += 1
    if assigned_role == "PA" and not first_pa_checked_in:
        first_pa_checked_in = True
    return redirect(url_for("index"))

@app.route("/reassign_role", methods=["POST"])
def reassign_role():
    global trans_workers_count, first_pa_checked_in
    barcode = request.form["barcode"]
    new_role = request.form["new_role"]
    if barcode in associates:
        old_role = associates[barcode]
        if old_role in ["Pit", "Trans", "Robotics Operator"]:
            trans_workers_count -= 1
        if new_role in ["Pit", "Trans", "Robotics Operator"]:
            trans_workers_count += 1
        if old_role == "PA" and new_role != "PA":
            first_pa_checked_in = False
        if new_role == "PA" and not first_pa_checked_in:
            first_pa_checked_in = True
        associates[barcode] = new_role
        assigned_roles[barcode] = new_role
        save_assigned_roles()
    return redirect(url_for("index"))

@app.route("/remove", methods=["POST"])
def remove():
    global trans_workers_count, first_pa_checked_in
    badge_id = request.form["badge_id"]
    if badge_id in associates:
        role = associates[badge_id]
        if role in ["Pit", "Trans", "Robotics Operator"]:
            trans_workers_count -= 1
        if role == "PA":
            first_pa_checked_in = False
        del associates[badge_id]
    return redirect(url_for("index"))

@app.route("/reset", methods=["POST"])
def reset():
    global associates, trans_workers_count, first_pa_checked_in
    associates = {}
    trans_workers_count = 0
    first_pa_checked_in = False
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
