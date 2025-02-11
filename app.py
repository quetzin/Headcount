from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# Default values for CE, MI, and Trans
total_headcount = 50  # Will be dynamically set
critical_role_count = 10  # Will be dynamically set

# Predefined roles with constraints
roles = {
    "Critical": {
        "Pit": {"required_training": True, "assigned": [], "max": 1},
        "CPT": {"required_training": True, "assigned": []},
        "Ship Clerk": {"required_training": True, "assigned": []},
        "DEA": {"required_training": True, "assigned": []},
        "Fluid PS": {"required_training": True, "assigned": [], "max": 1},
        "Main PS": {"required_training": True, "assigned": [], "max": 1},
        "Robotics Operator": {"required_training": True, "assigned": [], "max": 1},
    },
    "Non-Critical": {
        "Flats": {"required_training": False, "assigned": []},
        "MI": {"required_training": False, "assigned": []},
        "WS": {"required_training": False, "assigned": []},
        "Fluids": {"required_training": False, "assigned": []},
        "Main High Cap": {"required_training": False, "assigned": []},
        "Mid High Cap": {"required_training": False, "assigned": []},
        "Mid Cap": {"required_training": False, "assigned": []},
        "Trans": {"required_training": False, "assigned": []},
        "Carts": {"required_training": False, "assigned": []},
    }
}

associates = []

@app.route("/")
def index():
    return render_template("index.html", associates=associates, roles=roles, total_headcount=total_headcount)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    global total_headcount, critical_role_count
    if request.method == "POST":
        ce = int(request.form["CE"])
        mi = int(request.form["MI"])
        trans = int(request.form["Trans"])

        total_headcount = ce // 550 + mi  # Adjust total headcount
        critical_role_count = trans // 1000  # Adjust critical role count based on Trans value
        return redirect(url_for("index"))
    return render_template("settings.html", total_headcount=total_headcount, critical_role_count=critical_role_count)

@app.route("/checkin", methods=["POST"])
def checkin():
    if len(associates) >= total_headcount:
        return jsonify({"error": "Headcount limit reached"}), 400

    name = request.form["name"]
    has_training = request.form.get("has_training") == "on"

    associate = {"name": name, "has_training": has_training}
    associates.append(associate)

    assigned = False
    for category, role_list in roles.items():
        for role, details in role_list.items():
            if details["required_training"] == has_training and ("max" not in details or len(details["assigned"]) < details["max"]):
                details["assigned"].append(name)
                assigned = True
                break
        if assigned:
            break

    if not assigned:
        for role, details in roles["Non-Critical"].items():
            if len(details["assigned"]) < total_headcount:
                details["assigned"].append(name)
                break

    return redirect(url_for("index"))

@app.route("/reset", methods=["POST"])
def reset():
    global associates
    for category in roles.values():
        for role in category.values():
            role["assigned"] = []
    associates = []
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
