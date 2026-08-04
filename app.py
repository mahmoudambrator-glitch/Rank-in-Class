import os
from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "super_secret_key"

db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nat_id = db.Column(db.String(14), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    gpa = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="approved")

with app.app_context():
    db.create_all()

@app.route("/")
def index():
    approved_students = Student.query.filter_by(status="approved").order_by(Student.gpa.desc()).all()
    return render_template("index.html", students=approved_students)

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    nat_id = request.form.get("nat_id", "").strip()
    gpa_raw = request.form.get("gpa", "").strip()

    if len(name.split()) < 3:
        flash("❌ يجب كتابة الاسم ثلاثياً على الأقل!", "danger")
        return redirect("/")

    if not (nat_id.isdigit() and len(nat_id) == 14):
        flash("❌ الرقم القومي يجب أن يتكون من 14 رقماً صحيحاً!", "danger")
        return redirect("/")

    existing_student = Student.query.filter_by(nat_id=nat_id).first()
    if existing_student:
        flash("⚠️ هذا الرقم القومي مسجل بالفعل! تواصل مع المسؤول للتعديل.", "warning")
        return redirect("/")

    try:
        gpa = float(gpa_raw)
        if not (0.0 <= gpa <= 4.0):
            raise ValueError
    except ValueError:
        flash("❌ يرجى إدخال GPA صحيح بين 0.00 و 4.00", "danger")
        return redirect("/")

    new_student = Student(nat_id=nat_id, name=name, gpa=gpa, status="approved")
    db.session.add(new_student)
    db.session.commit()

    flash("✅ تم حفظ البيانات بنجاح في قاعدة البيانات!", "success")
    return redirect("/")

@app.route("/admin/users")
def admin_users():
    all_students = Student.query.all()
    return render_template("admin_users.html", students=all_students)

@app.route("/admin/update_gpa/<int:student_id>", methods=["POST"])
def update_gpa(student_id):
    student = Student.query.get_or_404(student_id)
    new_gpa_raw = request.form.get("new_gpa", "").strip()
    try:
        new_gpa = float(new_gpa_raw)
        if not (0.0 <= new_gpa <= 4.0):
            raise ValueError
        student.gpa = new_gpa
        db.session.commit()
        flash("✅ تم تعديل الـ GPA بنجاح!", "success")
    except ValueError:
        flash("❌ يرجى إدخال GPA صحيح بين 0.00 و 4.00", "danger")
    return redirect("/admin/users")

@app.route("/admin/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    flash("🗑️ تم حذف الطالب بنجاح!", "success")
    return redirect("/admin/users")
