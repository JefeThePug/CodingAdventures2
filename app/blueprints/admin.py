from flask import Blueprint, render_template

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin", methods=["GET", "POST"])
def admin():
    return render_template("admin/default.html")

@admin_bp.route("/admin/home")
def admin_home():
    return render_template("admin/home.html")