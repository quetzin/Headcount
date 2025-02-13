from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import math

app = Flask(__name__)

# Load associates data from JSON file and ensure barcodes are treated as strings
with open("names.json", "r") as f:
    associates_data = json.load(f)

# Create mappings from barcode to first name and login
barcode_to_info = {str(associate["barcode"]): f"{associate['first_name']} ({associate['login']})" for associate in associates_data}

# Default values for CE, MI, and Trans
total_headcount = 0
trans_count = 0

# Predefined roles
roles = {
    "Critical": ["Pit", "CPT", "Ship Clerk", "DEA", "Fluid PS", "Main PS", "Robotics Operator"],
    "Non-Critical": ["Flats", "MI", "WS", "Fluids", "Main High Cap", "Mid High Cap", "Mid Cap", "Trans", "Carts"]
}

# Store checked-in associates with assigned roles
associates = {}
assigned_roles = {}
trans_workers_count = 0  # Counter for Trans Workers

@app.route("/")
def index():
    non_trans_checkins = sum(1 for role in associates.values() if role not in ["Pit", "Trans", "Robotics Operator"])
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
        
        if trans > trans_count * 1000:
            return jsonify({"error": "Transitional Employees cannot exceed " + str(trans_count * 1000)}), 400
        
        return redirect(url_for("assign_roles"))
    
    return render_template("settings.html", total_headcount=total_headcount, trans_count=trans_count)

@app.route("/assign_roles", methods=["GET", "POST"])
def assign_roles():
    global assigned_roles
    if request.method == "POST":
        assigned_roles = {barcode: role for barcode, role in request.form.items()}
        return redirect(url_for("index"))
    
    return render_template("assign_roles.html", assigned_roles=assigned_roles, roles=roles, associates_data=associates_data, total_headcount=total_headcount)

@app.route("/checkin", methods=["POST"])
def checkin():
    global trans_workers_count

    badge_id = request.form["badge_id"]

    if badge_id in associates:
        return jsonify({"error": "Badge already scanned"}), 400

    name = barcode_to_info.get(badge_id, f"Unknown ({badge_id})")
    assigned_role = assigned_roles.get(badge_id, "Unassigned")
    associates[badge_id] = assigned_role

    if assigned_role in ["Pit", "Trans", "Robotics Operator"]:
        trans_workers_count += 1

    return redirect(url_for("index"))

@app.route("/remove", methods=["POST"])
def remove():
    global trans_workers_count
    
    badge_id = request.form["badge_id"]
    if badge_id in associates:
        role = associates[badge_id]
        if role in ["Pit", "Trans", "Robotics Operator"]:
            trans_workers_count -= 1
        del associates[badge_id]

    return redirect(url_for("index"))

@app.route("/reset", methods=["POST"])
def reset():
    global associates, assigned_roles, trans_workers_count
    associates = {}
    trans_workers_count = 0
    return redirect(url_for("index"))

@app.route("/reassign_role", methods=["POST"])
def reassign_role():
    global trans_workers_count

    barcode = request.form["barcode"]
    new_role = request.form["new_role"]

    if barcode in associates:
        old_role = associates[barcode]

        # Adjust Trans Worker count based on role change
        if old_role in ["Pit", "Trans", "Robotics Operator"]:
            trans_workers_count -= 1
        if new_role in ["Pit", "Trans", "Robotics Operator"]:
            trans_workers_count += 1

        associates[barcode] = new_role  # Update role assignment
    
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
