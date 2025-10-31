from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin

db = SQLAlchemy()

class Employee(db.Model):
    __tablename__ = "employees"  # ✅ correspond à ta table
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    hire_date = db.Column(db.Date)
    photo_path = db.Column(db.String(255))
    qr_code_path = db.Column(db.String(255))
    status = db.Column(db.String(50), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    plant = db.Column(db.String(100), nullable=False)


    skills = db.relationship("EmployeeSkill", back_populates="employee", cascade="all, delete-orphan")

class Skill(db.Model):
    __tablename__ = "skills"  # ✅ correspond à ta table
    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.Text)

    employees = db.relationship("EmployeeSkill", back_populates="skill", cascade="all, delete-orphan")
class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.BigInteger, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.String(64))
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(64))
    user_agent = db.Column(db.Text)
    user = db.relationship("User", backref="audit_logs", lazy=True)
class EmployeeSkill(db.Model):
    __tablename__ = "employeeskills"  # ✅ correspond à ta table
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"))
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id", ondelete="CASCADE"))
    level = db.Column(db.String(1), nullable=False)  # A–E
    last_assessed = db.Column(db.Date)
    trainer = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    attachment = db.Column(db.String(255))

    employee = db.relationship("Employee", back_populates="skills")
    skill = db.relationship("Skill", back_populates="employees")

from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(120))
    role = db.Column(db.String(20), default="user")  # 'admin' or 'user'

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
