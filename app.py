# Import necessary modules from Flask and Python standard libraries
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json  # For reading/writing JSON files to store data
import math  # For ceiling function in calculations
import os  # For checking if files exist

# Initialize Flask app
app = Flask(__name__)

# Constants for file paths where associate names and assigned roles are stored
NAMES_FILE = "names.json"
ASSIGNED_ROLES_FILE = "assigned_roles.json"

# Function to load associate names from JSON file
def load_names():
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE, "r") as f:
            return json.load(f)  # Return the parsed JSON data
    return []  # If file doesn't exist, return empty list (no associates yet)

# Function to save associate names into the JSON file
def save_names(data):
    with open(NAMES_FILE, "w") as f:
        json.dump(data, f, indent=4)  # Save with indentation for readability

# Function to load assigned roles from JSON file
def load_assigned_roles():
    if os.path.exists(ASSIGNED_ROLES_FILE):
        with open(ASSIGNED_ROLES_FILE, "r") as f:
            return json.load(f)
    return {}  # If file doesn't exist, return empty dictionary (no roles assigned)

# Function to save assigned roles to the file
def save_assigned_roles():
    with open(ASSIGNED_ROLES_FILE, "w") as f:
        json.dump(assigned_roles, f, indent=4)

# Load initial data at app startup
associates_data = load_names()  # Load all associates from file
assigned_roles = load_assigned_roles()  # Load all assigned roles

# Create a lookup dictionary: barcode -> "First Name (Login)"
barcode_to_info = {
    str(associate["barcode"]): f"{associate['first_name']} ({associate['login']})"
    for associate in associates_data
}

# Initialize default values for key counts
total_headcount = 0  # Total required headcount
trans_count = 0  # Required Trans headcount

# Define critical and non-critical roles in the system
roles = {
    "Critical": ["Pit", "CPT", "Ship Clerk", "DEA", "Fluid PS", "Main PS", "Robotics Operator", "PA"],
    "Non-Critical": ["Flats", "MI", "WS", "Fluids", "Main High Cap", "Mid High Cap", "Mid Cap", "Trans", "Carts"]
}

# Dictionary to track currently checked-in associates and their roles
associates = {}
trans_workers_count = 0  # Track how many "Trans" workers are currently checked in
first_pa_checked_in = False  # Special flag for tracking PA check-in status

# Route for the main page (dashboard)
@app.route("/")
def index():
    # Count how many PAs are currently checked in
    pa_count = sum(1 for role in associates.values() if role == "PA")

    # Count non-trans associates, excluding Pit, Trans, Robotics Operator
    non_trans_checkins = sum(1 for role in associates.values() if role not in ["Pit", "Trans", "Robotics Operator"])

    # If at least one PA is checked in, remove one from the non-trans count
    if pa_count > 0:
        non_trans_checkins -= 1

    # Render main dashboard, passing all needed variables to template
    return render_template("index.html", 
                           associates=associates, 
                           assigned_roles=assigned_roles, 
                           total_headcount=total_headcount, 
                           trans_count=trans_count, 
                           trans_workers_count=trans_workers_count,
                           current_checkins=non_trans_checkins,
                           barcode_to_info=barcode_to_info,
                           roles=roles)

# Route for configuring headcount and trans count
@app.route("/settings", methods=["GET", "POST"])
def settings():
    global total_headcount, trans_count  # Modify global variables

    if request.method == "POST":
        # Parse inputs from form
        ce = int(request.form.get("CE", 0))
        mi = int(request.form.get("MI", 0))
        trans = int(request.form.get("Trans", 0))

        # Calculate headcounts using rules provided
        total_headcount = math.ceil(ce / 550)
        trans_count = math.ceil(trans / 1000)

        # Ensure trans headcount doesn't exceed limit
        if trans > trans_count * 1000:
            return jsonify({"error": "Transitional Employees cannot exceed " + str(trans_count * 1000)}), 400

        return redirect(url_for("assign_roles"))

    return render_template("settings.html", total_headcount=total_headcount, trans_count=trans_count)

# Route for assigning roles to associates
@app.route("/assign_roles", methods=["GET", "POST"])
def assign_roles():
    global assigned_roles

    if request.method == "POST":
        # Save submitted roles into assigned_roles dictionary
        assigned_roles = {barcode: role for barcode, role in request.form.items()}
        save_assigned_roles()
        return redirect(url_for("index"))

    return render_template("assign_roles.html", assigned_roles=assigned_roles, roles=roles, associates_data=associates_data, total_headcount=total_headcount)

# Route for checking in associates by scanning badge
@app.route("/checkin", methods=["POST"])
def checkin():
    global trans_workers_count, first_pa_checked_in

    badge_id = request.form["badge_id"]

    # Prevent duplicate check-in
    if badge_id in associates:
        return jsonify({"error": "Badge already scanned"}), 400

    # If the badge is unrecognized, redirect to add associate form
    if badge_id not in barcode_to_info:
        return render_template("add_associate.html", barcode=badge_id, roles=roles)

    assigned_role = assigned_roles.get(badge_id, "Unassigned")
    associates[badge_id] = assigned_role

    # Special handling for trans roles
    if assigned_role in ["Pit", "Trans", "Robotics Operator"]:
        trans_workers_count += 1

    if assigned_role == "PA" and not first_pa_checked_in:
        first_pa_checked_in = True

    return redirect(url_for("index"))

# Route for adding new associate to the system
@app.route("/add_associate", methods=["POST"])
def add_associate():
    barcode = request.form["barcode"]
    first_name = request.form["first_name"]
    login = request.form["login"]
    assigned_role = request.form["assigned_role"]

    new_associate = {"barcode": barcode, "first_name": first_name, "login": login}
    associates_data.append(new_associate)
    save_names(associates_data)

    barcode_to_info[barcode] = f"{first_name} ({login})"
    assigned_roles[barcode] = assigned_role
    save_assigned_roles()

    return redirect(url_for("index"))

# Route for removing checked-in associate
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

# Route to reset all check-ins
@app.route("/reset", methods=["POST"])
def reset():
    global associates, trans_workers_count, first_pa_checked_in
    associates = {}
    trans_workers_count = 0
    first_pa_checked_in = False
    return redirect(url_for("index"))

# Route to reassign a role to a checked-in associate
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

# Run the Flask app in debug mode
if __name__ == "__main__":
    app.run(debug=True)
