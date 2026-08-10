import os
from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "super_secret_key"  # لحفظ التنبيهات والسيشن

# 1. إعداد رابط قاعدة البيانات من Vercel / Environment
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 2. تعريف جدول الطلاب في قاعدة البيانات
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nat_id = db.Column(db.String(14), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    gpa = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="approved")

# إنشاء الجداول تلقائيًا عند التشغيل
with app.app_context():
    db.create_all()

ADMIN_PASSWORD = "admin"

@app.route("/")
def index():
    # تعديل الاستعلام هنا ليعمل بشكل صحيح بدون أخطاء
    approved_students = Student.query.filter_by(status="approved").order_by(Student.gpa.desc()).all()
    return render_template("index.html", students=approved_students)

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name", "").strip()
    nat_id = request.form.get("nat_id", "").strip()
    gpa_raw = request.form.get("gpa", "").strip()

    # 1. التحقق من الاسم الثلاثي
    if len(name.split()) < 3:
        flash("❌ يجب كتابة الاسم ثلاثياً على الأقل!", "danger")
        return redirect("/")

    # 2. التحقق من الرقم القومي (14 رقم)
    if not (nat_id.isdigit() and len(nat_id) == 14):
        flash("❌ الرقم القومي يجب أن يتكون من 14 رقماً صحيحاً!", "danger")
        return redirect("/")

    # التحقق من أن الرقم القومي غير مسجل مسبقاً
    existing_student = Student.query.filter_by(nat_id=nat_id).first()
    if existing_student:
        flash("⚠️ هذا الرقم القومي مسجل بالفعل! تواصل مع المسؤول للتعديل.", "warning")
        return redirect("/")

    # 3. التحقق من GPA
    try:
        gpa = float(gpa_raw)
        if not (0.0 <= gpa <= 4.0):
            raise ValueError
    except ValueError:
        flash("❌ يرجى إدخال GPA صحيح بين 0.00 و 4.00", "danger")
        return redirect("/")

    # حفظ الطالب في قاعدة البيانات
    new_student = Student(nat_id=nat_id, name=name, gpa=gpa, status="approved")
    db.session.add(new_student)
    db.session.commit()

    flash("✅ تم حفظ البيانات بنجاح في قاعدة البيانات!", "success")
    return redirect("/")
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        password = request.form.get("password")
        if password == ADMIN_PASSWORD:
            return redirect("/admin/users")
        else:
            flash("❌ كلمة المرور غير صحيحة!", "danger")
    return render_template("admin_login.html")

@app.route("/admin/users")
def admin_users():
    students = Student.query.order_by(Student.gpa.desc()).all()
    return render_template("admin_users.html", students=students)
if __name__ == "__main__":
    app.run(debug=True)
