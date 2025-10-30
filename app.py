from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_migrate import Migrate
from flask_babel import Babel, _, get_locale
from datetime import datetime
from dotenv import load_dotenv
import qrcode, os
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# === Import interne ===
from models import db, Employee, Skill, EmployeeSkill, User, AuditLog
from config import Config
from github_uploader import upload_to_github
from utils import audit  # 🔹 helper d’audit

# === Initialisation de Flask ===
load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)

# === Authentification ===
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# === Babel (traduction) ===
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_SUPPORTED_LOCALES"] = ["en", "es_MX"]
app.config["BABEL_DEFAULT_TIMEZONE"] = "UTC"

def select_locale():
    return request.args.get("lang") or "en"

babel = Babel(app, locale_selector=select_locale)

# === Base de données ===
db.init_app(app)
migrate = Migrate(app, db)

# === Utilitaires ===
def admin_required():
    if not current_user.is_authenticated or current_user.role != "admin":
        abort(403)

@app.context_processor
def inject_get_locale():
    return dict(get_locale=get_locale)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# === ROUTES AUTH ===
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if User.query.filter(db.func.lower(User.email) == email.lower()).first():
            flash("This email is already registered.", "warning")
            return render_template("register.html")

        u = User(username=username, email=email)
        u.set_password(password)
        u.role = "user"

        db.session.add(u)
        db.session.commit()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.pop('_flashes', None)  # nettoie les anciens messages
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        user = User.query.filter(db.func.lower(User.email) == email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("✅ Successfully logged in", "success")
            return redirect(url_for("index"))

        flash("❌ Invalid email or password", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out 👋", "logout")
    return redirect(url_for("login"))


# === ROUTES PRINCIPALES ===
@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    return redirect(url_for("login"))


@app.route("/index")
@login_required
def index():
    search = request.args.get("search", "").strip()
    position = request.args.get("position", "").strip()
    department = request.args.get("department", "").strip()

    query = Employee.query
    if search:
        query = query.filter(
            (Employee.first_name.ilike(f"%{search}%")) |
            (Employee.last_name.ilike(f"%{search}%"))
        )
    if position:
        query = query.filter(Employee.position == position)
    if department:
        query = query.filter(Employee.department == department)

    employees = query.all()
    positions = [p[0] for p in db.session.query(Employee.position).distinct().all() if p[0]]
    departments = [d[0] for d in db.session.query(Employee.department).distinct().all() if d[0]]

    return render_template("index.html", employees=employees, positions=positions, departments=departments)


# === AJOUT EMPLOYÉ ===
@app.route("/add_employee", methods=["GET", "POST"])
@login_required
def add_employee():
    if request.method == "POST":
        try:
            emp = Employee(
                id=int(request.form["id"]),
                first_name=request.form["first_name"],
                last_name=request.form["last_name"],
                position=request.form.get("position"),
                department=request.form.get("department"),
                hire_date=datetime.strptime(request.form["hire_date"], "%Y-%m-%d").date() if request.form.get("hire_date") else None
            )
            db.session.add(emp)
            db.session.commit()

            # 🧾 Audit
            audit("add_employee", "Employee", emp.id, {
                "name": f"{emp.first_name} {emp.last_name}",
                "position": emp.position,
                "department": emp.department
            })

            # 📸 Photo upload (GitHub)
            photo = request.files.get("photo")
            if photo and photo.filename:
                photos_folder = os.path.join(app.static_folder, "photos")
                os.makedirs(photos_folder, exist_ok=True)
                photo_filename = f"employee_{emp.id}.jpg"
                photo_path = os.path.join(photos_folder, photo_filename)
                photo.save(photo_path)

                html_url, raw_url = upload_to_github(photo_path, f"media/photos/{photo_filename}")
                emp.photo_path = raw_url
                db.session.commit()
                os.remove(photo_path)

            # 🔳 QR Code upload (GitHub)
            os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
            qr_data = url_for('employee_public', employee_id=emp.id, _external=True)
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_path = os.path.join(app.config["UPLOAD_FOLDER"], f"employee_{emp.id}.png")
            qr_img.save(qr_path)

            html_url, raw_url = upload_to_github(qr_path, f"media/qrcodes/employee_{emp.id}.png")
            emp.qr_code_path = raw_url
            db.session.commit()
            os.remove(qr_path)

            flash(_("✅ Employee added successfully!"), "success")
            return redirect(url_for("index"))

        except Exception as e:
            db.session.rollback()
            print(f"Error adding employee: {e}")
            flash(f"❌ Error: {str(e)}", "danger")

    return render_template("add_employee.html")


# === SUPPRESSION EMPLOYÉ ===
@app.route("/employee/<int:employee_id>/delete", methods=["POST"])
@login_required
def delete_employee(employee_id):
    admin_required()

    employee = Employee.query.get_or_404(employee_id)
    EmployeeSkill.query.filter_by(employee_id=employee.id).delete()

    db.session.delete(employee)
    db.session.commit()

    # 🧾 Audit
    audit("delete_employee", "Employee", employee_id, {
        "name": f"{employee.first_name} {employee.last_name}",
        "position": employee.position,
        "department": employee.department,
    })

    flash(_("🗑️ Employee deleted successfully!"), "info")
    return redirect(url_for("index"))


# === DÉTAIL EMPLOYÉ ===
@app.route("/employee/<int:employee_id>")
@login_required
def employee_detail(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    skills = Skill.query.all()
    return render_template("employee_detail.html", employee=employee, skills=skills)


# === ADMIN DASHBOARD ===
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    admin_required()
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(50).all()
    users = User.query.all()
    return render_template("admin_dashboard.html", logs=logs, users=users)


# === AUTRES ROUTES (skills, badge, etc.) ===
@app.route("/skills")
@login_required
def skills_list():
    line = request.args.get("line", "").strip()
    query = Skill.query
    if line:
        query = query.filter(Skill.category == line)
    skills = query.all()
    lines = [l[0] for l in db.session.query(Skill.category).distinct().all() if l[0]]
    return render_template("skills.html", skills=skills, lines=lines)


@app.route("/skill/<int:skill_id>/delete", methods=["POST"])
@login_required
def delete_skill(skill_id):
    admin_required()
    skill = Skill.query.get_or_404(skill_id)
    EmployeeSkill.query.filter_by(skill_id=skill.id).delete()
    db.session.delete(skill)
    db.session.commit()

    # 🧾 Audit
    audit("delete_skill", "Skill", skill_id, {
        "name": skill.skill_name,
        "category": skill.category
    })
    flash(_("🗑️ Skill deleted successfully!"), "info")
    return redirect(url_for("skills_list"))


# === PUBLIC PAGE (QR) ===
@app.route("/employee/<int:employee_id>/public")
def employee_public(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    return render_template("employee_public.html", employee=employee)


# === LANCEMENT ===
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
