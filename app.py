from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort 
from flask_login import LoginManager, login_user, logout_user, current_user, login_required, UserMixin
from flask_migrate import Migrate
from flask_babel import Babel, _, get_locale
from models import db, Employee, Skill, EmployeeSkill,User
from config import Config
from datetime import datetime
import qrcode, os
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from github_uploader import upload_to_github
from dotenv import load_dotenv
from flask_login import current_user,login_user 
from models import AuditLog, db
from utils import audit 
from flask import session, get_flashed_messages

load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)

# === Auth ===
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ======== Configuration multilingue =========
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_SUPPORTED_LOCALES"] = ["en", "es_MX"]
app.config["BABEL_DEFAULT_TIMEZONE"] = "UTC"

def select_locale():
    return request.args.get("lang") or "en"

babel = Babel(app, locale_selector=select_locale)

# === Base de données ===
db.init_app(app)

# Ensure User has get_id
if not hasattr(User, 'get_id'):
    User.get_id = lambda self: str(self.id)

migrate = Migrate(app, db)

#ajout de compt 
def audit(action, entity_type=None, entity_id=None, details=None):
    log = AuditLog(
        user_id = current_user.id if getattr(current_user, "is_authenticated", False) else None,
        action = action,
        entity_type = entity_type,
        entity_id = str(entity_id) if entity_id is not None else None,
        details = details or {},
        ip_address = request.remote_addr,
        user_agent = request.headers.get("User-Agent")
    )
    db.session.add(log)
    db.session.commit()

from flask import request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from models import db, Employee
from utils import audit  # si tu as le helper audit()

@app.route("/employee/<int:employee_id>/update_info", methods=["POST"])
@login_required
def update_employee_info(employee_id):
    # 🔒 Vérifier que l'utilisateur connecté est un admin
    if current_user.role != "admin":
        abort(403)  # renvoie une erreur "Forbidden"

    employee = Employee.query.get_or_404(employee_id)

    new_position = request.form.get("position")
    new_department = request.form.get("department")

    # petite sécurité : éviter les champs vides si tu veux
    if not new_position or not new_department:
        flash("⚠️ Veuillez remplir tous les champs.", "warning")
        return redirect(url_for("employee_detail", employee_id=employee_id))

    # ✅ Mettre à jour les données
    old_position = employee.position
    old_department = employee.department

    employee.position = new_position
    employee.department = new_department

    db.session.commit()

    # 🧾 (Optionnel) journaliser l’action
    try:
        audit("update_employee_info", "Employee", employee_id, {
            "old_position": old_position,
            "new_position": new_position,
            "old_department": old_department,
            "new_department": new_department
        })
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("Audit error:", e)

    flash("✅ Informations de l’employé mises à jour avec succès !", "success")
    return redirect(url_for("employee_detail", employee_id=employee_id))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Vérifie si l'email existe déjà
        if User.query.filter(db.func.lower(User.email) == email.lower()).first():
            flash("This email is already registered.", "warning")
            return render_template("register.html")

        # Crée l'utilisateur
        u = User(username=username, email=email)
        u.set_password(password)
        u.role = "user"

        db.session.add(u)
        db.session.commit()

        flash("Account created successfully! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    admin_required()  # 🔒 accès réservé à l’admin uniquement

    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(50).all()
    users = User.query.all()

    return render_template("admin_dashboard.html", logs=logs, users=users)


# === CONTEXT GLOBAL ===
@app.context_processor
def inject_get_locale():
    return dict(get_locale=get_locale)



# === AUTH ROUTES ===
@login_required
@login_required
@login_required
@login_required
@login_required
@login_required
@login_required


# === AUTH ROUTES ===


@app.route("/login", methods=["GET", "POST"])
def login():
    # ✅ Supprime explicitement les anciens messages de la session
    session.pop('_flashes', None)

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = User.query.filter(db.func.lower(User.email) == email).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Successfully logged in ✅", "success")
            return redirect(url_for("index"))

        flash("Invalid email or password ❌", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out 👋", "logout")
    return redirect(url_for("login"))

# === ROUTES ===
@app.route("/")

def home():
    # Si l'utilisateur est connecté, on le redirige vers la page principale
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    # Sinon, on va vers la page de login
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


@app.route("/add_employee", methods=["GET", "POST"])
@login_required
def add_employee():
    if request.method == "POST":
        try:
            id_value = int(request.form["id"])
            first_name = request.form["first_name"]
            last_name = request.form["last_name"]
            position = request.form.get("position")
            department = request.form.get("department")
            hire_date_str = request.form.get("hire_date")
            hire_date = datetime.strptime(hire_date_str, "%Y-%m-%d").date() if hire_date_str else None

            emp = Employee(
                id=id_value,
                first_name=first_name,
                last_name=last_name,
                position=position,
                department=department,
                hire_date=hire_date
            )
            db.session.add(emp)
            db.session.commit()

            # 📸 Photo upload vers GitHub
            photo = request.files.get("photo")
            if photo and photo.filename != "":
                photos_folder = os.path.join(app.static_folder, "photos")
                os.makedirs(photos_folder, exist_ok=True)
                photo_filename = f"employee_{emp.id}.jpg"
                photo_path = os.path.join(photos_folder, photo_filename)
                photo.save(photo_path)
                # Upload GitHub
                html_url, raw_url = upload_to_github(photo_path, f"media/photos/{photo_filename}")
                emp.photo_path = raw_url
                db.session.commit()
                os.remove(photo_path)

            # 🔳 QR Code upload vers GitHub
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
            audit("add_employee", "Employee", emp.id, {
                    "name": f"{emp.first_name} {emp.last_name}",
                    "position": emp.position,
                    "department": emp.department,
})
            flash(f"❌ Error: {str(e)}", "danger")

    return render_template("add_employee.html")


@app.route("/employee/<int:employee_id>")
@login_required
def employee_detail(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    skills = Skill.query.all()
    return render_template("employee_detail.html", employee=employee, skills=skills)


@app.route("/employee/<int:employee_id>/update_photo", methods=["POST"])
@login_required
def update_employee_photo(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    photo = request.files.get("photo")
    if not photo or photo.filename == "":
        flash(_("⚠️ No file selected."), "warning")
        return redirect(url_for("employee_detail", employee_id=employee_id))

    photos_folder = os.path.join(app.static_folder, "photos")
    os.makedirs(photos_folder, exist_ok=True)
    photo_filename = f"employee_{employee.id}.jpg"
    photo_path = os.path.join(photos_folder, photo_filename)
    photo.save(photo_path)

    html_url, raw_url = upload_to_github(photo_path, f"media/photos/{photo_filename}")
    employee.photo_path = raw_url
    db.session.commit()
    os.remove(photo_path)

    flash(_("✅ Profile photo updated successfully!"), "success")
    return redirect(url_for("employee_detail", employee_id=employee_id))


@app.route("/employee/<int:employee_id>/add_skill", methods=["POST"])
@login_required
def add_skill_to_employee(employee_id):
    skill_id = request.form["skill_id"]
    level = request.form["level"]
    trainer = request.form.get("trainer")
    remarks = request.form.get("remarks")
    last_assessed_str = request.form.get("last_assessed")
    last_assessed = datetime.strptime(last_assessed_str, "%Y-%m-%d").date() if last_assessed_str else datetime.now().date()

    attachment_file = request.files.get("attachment")
    attachment_path = None

    if attachment_file and attachment_file.filename != "":
        upload_folder = os.path.join(app.static_folder, "attachments")
        os.makedirs(upload_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"employee_{employee_id}_{timestamp}_{attachment_file.filename}"
        save_path = os.path.join(upload_folder, filename)
        attachment_file.save(save_path)
        html_url, raw_url = upload_to_github(save_path, f"media/attachments/{filename}")
        attachment_path = raw_url
        os.remove(save_path)

    new_entry = EmployeeSkill(
        employee_id=employee_id,
        skill_id=skill_id,
        level=level,
        last_assessed=last_assessed,
        trainer=trainer,
        remarks=remarks,
        attachment=attachment_path,
    )
    db.session.add(new_entry)
    db.session.commit()
    # 🧾 Audit
       
    audit("assign_skill", "EmployeeSkill", new_entry.id, {
        "employee_id": employee_id,
        "skill_id": skill_id,
        "level": level,
        "trainer": trainer
    })
    flash(_("🧠 Skill added successfully!"), "success")
    return redirect(url_for("employee_detail", employee_id=employee_id))


@app.route("/skills")
@login_required
def skills_list():
    # 🔍 Récupérer le filtre de ligne
    line = request.args.get("line", "").strip()

    # Construire la requête
    query = Skill.query
    if line:
        query = query.filter(Skill.category == line)

    # Exécuter la requête
    skills = query.all()

    # Récupérer toutes les lignes distinctes pour le menu déroulant
    lines = [l[0] for l in db.session.query(Skill.category).distinct().all() if l[0]]

    return render_template("skills.html", skills=skills, lines=lines)

@app.route("/add_skill", methods=["GET", "POST"])
@login_required
def add_skill():
    if request.method == "POST":
        s = Skill(
            skill_name=request.form["skill_name"],
            category=request.form.get("category"),
            description=request.form.get("description"),
        )
        db.session.add(s)
        db.session.commit()
        flash(_("✨ Skill added successfully!"), "success")
        return redirect(url_for("skills_list"))
    return render_template("add_skill.html")

@app.route("/skill/<int:skill_id>/delete", methods=["POST"])
@login_required
def delete_skill(skill_id):
    admin_required()  # 🔒 admin only

    skill = Skill.query.get_or_404(skill_id)

    # Supprimer aussi les relations EmployeeSkill associées
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


@app.route("/employee/<int:employee_id>/delete", methods=["POST"])
@login_required
def delete_employee(employee_id):
    admin_required()  # 🔒 admin only

    employee = Employee.query.get_or_404(employee_id)

    # Supprimer les liaisons skill
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


@app.route("/badge/<int:employee_id>")
def generate_badge(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    # === 📁 Création du dossier local pour les badges ===
    media_qr_folder = os.path.join(app.root_path, "media", "qrcodes")
    os.makedirs(media_qr_folder, exist_ok=True)

    # === 📄 Chemin du fichier PDF généré ===
    badge_path = os.path.join(media_qr_folder, f"badge_{employee.id}.pdf")

    # === 📏 Dimensions du badge ===
    width, height = (5.9 * cm, 8.4 * cm)
    c = canvas.Canvas(badge_path, pagesize=(width, height))

    # === 🔲 Bordure extérieure ===
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(0.1 * cm, 0.1 * cm, width - 0.2 * cm, height - 0.2 * cm)

    # === 🏢 En-tête texte ===
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(width / 2, height - 0.8 * cm, "ASSYMEX MONTERREY, S.A. DE C.V.")
    c.setFont("Helvetica", 6)
    c.drawCentredString(width / 2, height - 1.2 * cm, "San Sebastián No.110 Col. Los Lermas")
    c.drawCentredString(width / 2, height - 1.6 * cm, "67190 Guadalupe, N.L. México")
    c.drawCentredString(width / 2, height - 2.0 * cm, "Tels. +52 81 8127 2833 y +52 81 8127 2835")

    # === Ligne de séparation ===
    c.setStrokeColorRGB(0.75, 0.75, 0.75)
    c.setLineWidth(0.4)
    c.line(0.5 * cm, height - 2.3 * cm, width - 0.5 * cm, height - 2.3 * cm)

    # === Logos locaux ===
    assymex_logo = os.path.join(app.root_path, "static", "img", "logo_assymex.jpg")
    avocarbon_logo = os.path.join(app.root_path, "static", "img", "avocarbon_logo.png")

    if os.path.exists(assymex_logo):
        c.drawImage(assymex_logo, 0.7 * cm, height - 4.0 * cm,
                    width=2.2 * cm, height=0.9 * cm,
                    preserveAspectRatio=True, mask='auto')

    # === 🧾 QR Code (hébergé sur GitHub raw) ===
    if employee.qr_code_path:
        try:
            c.drawImage(employee.qr_code_path, 0.9 * cm, 1.9 * cm,
                        width=2.0 * cm, height=2.0 * cm, mask='auto')
        except Exception as e:
            print(f"⚠️ Impossible d'afficher le QR code : {e}")

    # === 🖼️ Photo Employé (hébergée sur GitHub raw) ===
    if employee.photo_path:
        try:
            c.drawImage(employee.photo_path, 3.3 * cm, 1.9 * cm,
                        width=2.4 * cm, height=3.2 * cm,
                        preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"⚠️ Impossible d'afficher la photo : {e}")
            c.rect(3.3 * cm, 1.9 * cm, 2.4 * cm, 3.2 * cm)
            c.setFont("Helvetica-Oblique", 6)
            c.drawString(3.5 * cm, 3.8 * cm, "No Photo")
    else:
        c.rect(3.3 * cm, 1.9 * cm, 2.4 * cm, 3.2 * cm)
        c.setFont("Helvetica-Oblique", 6)
        c.drawString(3.5 * cm, 3.8 * cm, "No Photo")

    # === Logo AVOCarbon ===
    if os.path.exists(avocarbon_logo):
        c.drawImage(avocarbon_logo, width - 2.2 * cm, 0.25 * cm,
                    width=1.7 * cm, height=0.7 * cm,
                    preserveAspectRatio=True, mask='auto')

    # === Bandeau Nom et Poste ===
    c.setFillColorRGB(0.17, 0.35, 0.69)
    c.rect(0.4 * cm, 0.6 * cm, width - 0.8 * cm, 1.2 * cm, fill=True, stroke=False)
    c.setFillColorRGB(1, 1, 1)

    full_name = f"{employee.first_name.upper()} {employee.last_name.upper()}"
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(width / 2, 1.1 * cm, full_name)
    if employee.position:
        c.setFont("Helvetica", 6)
        c.drawCentredString(width / 2, 0.7 * cm, employee.position.upper())

    # === Encadré ID ===
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(0.4 * cm, 0.2 * cm, 2.2 * cm, 0.35 * cm, fill=True, stroke=True)
    c.setFont("Helvetica", 6)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(0.6 * cm, 0.32 * cm, f"ID: {employee.id}")

    # === Sauvegarde du PDF ===
    c.save()

    # ✅ Retourne le badge en téléchargement
    return send_file(badge_path, as_attachment=True)


@app.route("/employee/<int:employee_id>/public")
def employee_public(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    return render_template("employee_public.html", employee=employee)
def admin_required():
    if not current_user.is_authenticated or current_user.role != "admin":
        abort(403)

@app.route("/admin/users")
@login_required
def admin_users():
    admin_required()
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)

@app.route("/admin/users/<int:user_id>/role", methods=["POST"])
@login_required
def set_user_role(user_id):
    admin_required()
    new_role = request.form["role"]
    if new_role not in ("user","admin"):
        abort(400)
    target = User.query.get_or_404(user_id)
    old = target.role
    target.role = new_role
    audit("promote_user" if new_role=="admin" else "demote_user", "User", user_id, {"old": old, "new": new_role})
    db.session.commit()
    flash(f"Rôle mis à jour: {old} → {new_role}", "success")
    return redirect(url_for("admin_users"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
