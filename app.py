from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_migrate import Migrate
from flask_babel import Babel, _, get_locale
from models import db, Employee, Skill, EmployeeSkill
from config import Config
from datetime import datetime
import qrcode, os
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from github_uploader import upload_to_github
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)

# ======== Configuration multilingue =========
app.config["BABEL_DEFAULT_LOCALE"] = "en"
app.config["BABEL_SUPPORTED_LOCALES"] = ["en", "es_MX"]
app.config["BABEL_DEFAULT_TIMEZONE"] = "UTC"

def select_locale():
    return request.args.get("lang") or "en"

babel = Babel(app, locale_selector=select_locale)

# === Base de données ===
db.init_app(app)
migrate = Migrate(app, db)

# === CONTEXT GLOBAL ===
@app.context_processor
def inject_get_locale():
    return dict(get_locale=get_locale)

# === ROUTES ===
@app.route("/")
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
            flash(f"❌ Error: {str(e)}", "danger")

    return render_template("add_employee.html")


@app.route("/employee/<int:employee_id>")
def employee_detail(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    skills = Skill.query.all()
    return render_template("employee_detail.html", employee=employee, skills=skills)


@app.route("/employee/<int:employee_id>/update_photo", methods=["POST"])
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
    flash(_("🧠 Skill added successfully!"), "success")
    return redirect(url_for("employee_detail", employee_id=employee_id))


@app.route("/skills")
def skills_list():
    skills = Skill.query.all()
    return render_template("skills.html", skills=skills)


@app.route("/add_skill", methods=["GET", "POST"])
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


@app.route("/employee/<int:employee_id>/delete", methods=["POST"])
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    EmployeeSkill.query.filter_by(employee_id=employee.id).delete()
    db.session.delete(employee)
    db.session.commit()
    flash(_("🗑️ Employee deleted successfully!"), "info")
    return redirect(url_for("index"))


@app.route("/badge/<int:employee_id>")
def generate_badge(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    width, height = (5.9 * cm, 8.4 * cm)
    badge_path = os.path.join("/qrcodes", f"badge_{employee.id}.pdf")
    c = canvas.Canvas(badge_path, pagesize=(width, height))

    c.setStrokeColorRGB(0, 0, 0)
    c.rect(0.1 * cm, 0.1 * cm, width - 0.2 * cm, height - 0.2 * cm)

    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(width / 2, height - 0.8 * cm, "ASSYMEX MONTERREY, S.A. DE C.V.")
    c.setFont("Helvetica", 6)
    c.drawCentredString(width / 2, height - 1.2 * cm, "San Sebastián No.110 Col. Los Lermas")
    c.drawCentredString(width / 2, height - 1.6 * cm, "67190 Guadalupe, N.L. México")
    c.drawCentredString(width / 2, height - 2.0 * cm, "Tels. +52 81 8127 2833 y +52 81 8127 2835")

    c.setStrokeColorRGB(0.75, 0.75, 0.75)
    c.setLineWidth(0.4)
    c.line(0.5 * cm, height - 2.3 * cm, width - 0.5 * cm, height - 2.3 * cm)

    assymex_logo = os.path.join(app.root_path, "static", "img", "logo_assymex.jpg")
    avocarbon_logo = os.path.join(app.root_path, "static", "img", "avocarbon_logo.png")

    if os.path.exists(assymex_logo):
        c.drawImage(assymex_logo, 0.7 * cm, height - 4.0 * cm, width=2.2 * cm, height=0.9 * cm, preserveAspectRatio=True, mask='auto')

    if employee.qr_code_path:
        c.drawImage(employee.qr_code_path, 0.9 * cm, 1.9 * cm, width=2.0 * cm, height=2.0 * cm, mask='auto')

    if employee.photo_path:
        c.drawImage(employee.photo_path, 3.3 * cm, 1.9 * cm, width=2.4 * cm, height=3.2 * cm, preserveAspectRatio=True, mask='auto')
    else:
        c.rect(3.3 * cm, 1.9 * cm, 2.4 * cm, 3.2 * cm)
        c.setFont("Helvetica-Oblique", 6)
        c.drawString(3.5 * cm, 3.8 * cm, "No Photo")

    if os.path.exists(avocarbon_logo):
        c.drawImage(avocarbon_logo, width - 2.2 * cm, 0.25 * cm, width=1.7 * cm, height=0.7 * cm, preserveAspectRatio=True, mask='auto')

    c.setFillColorRGB(0.17, 0.35, 0.69)
    c.rect(0.4 * cm, 0.6 * cm, width - 0.8 * cm, 1.2 * cm, fill=True, stroke=False)
    c.setFillColorRGB(1, 1, 1)

    full_name = f"{employee.first_name.upper()} {employee.last_name.upper()}"
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(width / 2, 1.1 * cm, full_name)
    if employee.position:
        c.setFont("Helvetica", 6)
        c.drawCentredString(width / 2, 0.7 * cm, employee.position.upper())

    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setFillColorRGB(0.95, 0.95, 0.95)
    c.rect(0.4 * cm, 0.2 * cm, 2.2 * cm, 0.35 * cm, fill=True, stroke=True)
    c.setFont("Helvetica", 6)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(0.6 * cm, 0.32 * cm, f"ID: {employee.id}")

    c.save()
    return send_file(badge_path, as_attachment=True)


@app.route("/employee/<int:employee_id>/public")
def employee_public(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    return render_template("employee_public.html", employee=employee)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
