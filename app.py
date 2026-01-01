import os
import secrets
import string
from datetime import datetime
from io import StringIO

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session,
    jsonify, Response
)
from flask_sqlalchemy import SQLAlchemy

# Configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data.db")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")  # CHANGE before production
SITE_TITLE = os.getenv("SITE_TITLE", "Diaz Custom Painting")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = SECRET_KEY

db = SQLAlchemy(app)

# ---------------- Models ----------------
class Referrer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    neighborhood = db.Column(db.String(120))
    code = db.Column(db.String(16), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reward_balance = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "neighborhood": self.neighborhood,
            "code": self.code,
            "reward_balance": self.reward_balance,
            "created_at": self.created_at.isoformat()
        }

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(200))
    referrer_id = db.Column(db.Integer, db.ForeignKey("referrer.id"), nullable=True)
    referrer_name_raw = db.Column(db.String(200))
    project_type = db.Column(db.String(80))
    rooms = db.Column(db.String(120))
    budget_range = db.Column(db.String(80))
    timeline = db.Column(db.String(120))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(40), default="new")

    referrer = db.relationship("Referrer", backref="leads")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "referrer": self.referrer.to_dict() if self.referrer else None,
            "referrer_name_raw": self.referrer_name_raw,
            "project_type": self.project_type,
            "rooms": self.rooms,
            "budget_range": self.budget_range,
            "timeline": self.timeline,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "status": self.status
        }

# ---------------- Helpers ----------------
def generate_code(length=6):
    alphabet = ''.join(c for c in (string.ascii_uppercase + string.digits) if c not in "IO0")
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_unique_code():
    for _ in range(20):
        c = generate_code()
        if not Referrer.query.filter_by(code=c).first():
            return c
    return generate_code(8)

def require_admin():
    return session.get("is_admin", False)

@app.before_first_request
def ensure_tables():
    db.create_all()

# ---------------- Public routes ----------------
@app.route("/")
def index():
    sample_referrers = Referrer.query.order_by(Referrer.created_at.desc()).limit(6).all()
    return render_template("index.html", site_title=SITE_TITLE, referrers=sample_referrers)

@app.route("/gallery")
def gallery():
    photos = [
        {"file": "before1.jpg", "caption": "Kitchen — Elmwood"},
        {"file": "after1.jpg", "caption": "Kitchen — Elmwood"},
        {"file": "exterior1.jpg", "caption": "Exterior repaint — Oak Park"}
    ]
    return render_template("gallery.html", photos=photos)

@app.route("/request-estimate", methods=["GET", "POST"])
def request_estimate():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        ref_code = (request.form.get("referrer_code") or "").strip().upper() or None
        ref_name_raw = (request.form.get("referrer_name") or "").strip() or None
        project_type = request.form.get("project_type")
        rooms = request.form.get("rooms")
        budget_range = request.form.get("budget_range")
        timeline = request.form.get("timeline")
        notes = request.form.get("notes")

        if not name or not phone:
            flash("Please include your name and phone number.", "danger")
            return redirect(url_for("request_estimate"))

        referrer = None
        if ref_code:
            referrer = Referrer.query.filter_by(code=ref_code).first()

        lead = Lead(
            name=name,
            phone=phone,
            email=email,
            referrer_id=referrer.id if referrer else None,
            referrer_name_raw=(ref_name_raw if not referrer else None),
            project_type=project_type,
            rooms=rooms,
            budget_range=budget_range,
            timeline=timeline,
            notes=notes
        )
        db.session.add(lead)
        db.session.commit()
        flash("Thanks — your request was submitted. We'll contact you soon.", "success")
        return redirect(url_for("index"))
    return render_template("request_estimate.html")

# ---------------- API ----------------
@app.route("/api/validate-code/<code>", methods=["GET"])
def api_validate_code(code):
    code = (code or "").strip().upper()
    if not code:
        return jsonify({"valid": False, "reason": "empty"})
    ref = Referrer.query.filter_by(code=code).first()
    if ref:
        return jsonify({"valid": True, "referrer": ref.to_dict()})
    return jsonify({"valid": False, "reason": "not_found"})

@app.route("/api/leads", methods=["POST"])
def api_leads():
    data = request.get_json(silent=True) or request.form or {}
    # support both JSON payloads and form posting
    name = (data.get("name") or data.get("entry_name") or "").strip()
    phone = (data.get("phone") or data.get("entry_phone") or "").strip()
    email = (data.get("email") or data.get("entry_email") or "").strip()
    ref_code = (data.get("referrer_code") or "").strip().upper() or None
    ref_name_raw = data.get("referrer_name") or None
    project_type = data.get("project_type")
    rooms = data.get("rooms")
    budget_range = data.get("budget_range")
    timeline = data.get("timeline")
    notes = data.get("notes")

    if not name or not phone:
        return jsonify({"ok": False, "error": "missing_name_or_phone"}), 400

    referrer = None
    if ref_code:
        referrer = Referrer.query.filter_by(code=ref_code).first()

    lead = Lead(
        name=name,
        phone=phone,
        email=email,
        referrer_id=referrer.id if referrer else None,
        referrer_name_raw=(ref_name_raw if not referrer else None),
        project_type=project_type,
        rooms=rooms,
        budget_range=budget_range,
        timeline=timeline,
        notes=notes
    )
    db.session.add(lead)
    db.session.commit()
    return jsonify({"ok": True, "lead_id": lead.id})

# ---------------- Admin ----------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        if pw == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Logged in", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Incorrect password", "danger")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Logged out", "info")
    return redirect(url_for("index"))

@app.route("/admin")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("admin_login"))
    leads = Lead.query.order_by(Lead.created_at.desc()).limit(200).all()
    referrers = Referrer.query.order_by(Referrer.created_at.desc()).all()
    return render_template("admin_dashboard.html", leads=leads, referrers=referrers)

@app.route("/admin/referrers/new", methods=["GET", "POST"])
def admin_new_referrer():
    if not require_admin():
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        neighborhood = request.form.get("neighborhood", "").strip()
        code = (request.form.get("code") or "").strip().upper()
        if not code:
            code = create_unique_code()
        if Referrer.query.filter_by(code=code).first():
            flash("Code already exists, try a different one", "danger")
            return redirect(url_for("admin_new_referrer"))
        ref = Referrer(name=name, neighborhood=neighborhood, code=code)
        db.session.add(ref)
        db.session.commit()
        flash(f"Referrer created: {name} — code {code}", "success")
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_new_referrer.html")

@app.route("/admin/referrers/<int:ref_id>/credit", methods=["POST"])
def admin_credit_referrer(ref_id):
    if not require_admin():
        return redirect(url_for("admin_login"))
    ref = Referrer.query.get_or_404(ref_id)
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    ref.reward_balance += amount
    db.session.commit()
    flash(f"Credited {amount} to {ref.name}", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/leads/<int:lead_id>/status", methods=["POST"])
def admin_update_lead_status(lead_id):
    if not require_admin():
        return redirect(url_for("admin_login"))
    lead = Lead.query.get_or_404(lead_id)
    new_status = request.form.get("status", lead.status)
    lead.status = new_status
    if new_status == "won" and lead.referrer:
        lead.referrer.reward_balance += 1
    db.session.commit()
    flash("Lead updated", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/export/leads.csv")
def admin_export_leads():
    if not require_admin():
        return redirect(url_for("admin_login"))
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    si = StringIO()
    si.write("id,created_at,name,phone,email,referrer_code,referrer_name_raw,project_type,rooms,budget_range,timeline,status,notes\n")
    for l in leads:
        ref_code = l.referrer.code if l.referrer else ""
        notes = (l.notes or "").replace("\n", " ").replace("\r", " ")
        line = f'{l.id},"{l.created_at.isoformat()}","{(l.name or "").replace(\'"\', \'""\')}","{(l.phone or "").replace(\'"\', \'""\')}","{(l.email or "").replace(\'"\', \'""\')}","{ref_code}","{(l.referrer_name_raw or "").replace(\'"\', \'""\')}","{(l.project_type or "").replace(\'"\', \'""\')}","{(l.rooms or "").replace(\'"\', \'""\')}","{(l.budget_range or "").replace(\'"\', \'""\')}","{(l.timeline or "").replace(\'"\', \'""\')}","{(l.status or "").replace(\'"\', \'""\')}","{notes.replace(\'"\', \'""\')}"\n'
        si.write(line)
    csv_output = si.getvalue()
    return Response(csv_output, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=leads.csv"})

# ---------------- Errors ----------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# ---------------- Run ----------------
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug)