from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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

    skills = db.relationship("EmployeeSkill", back_populates="employee", cascade="all, delete-orphan")

class Skill(db.Model):
    __tablename__ = "skills"  # ✅ correspond à ta table
    id = db.Column(db.Integer, primary_key=True)
    skill_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.Text)

    employees = db.relationship("EmployeeSkill", back_populates="skill", cascade="all, delete-orphan")

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
