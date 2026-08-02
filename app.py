from flask import Flask, render_template, request, redirect, flash

app = Flask(__name__)
app.secret_key = "super_secret_key"  # لحفظ التنبيهات والسيشن

# قاعدة بيانات مؤقتة في الذاكرة
students_db = {}
ADMIN_PASSWORD = "admin"

@app.route("/")
def index():
    # ترتيب الطلاب المقبولين حسب الـ GPA من الأعلى للأقل
    approved_students = [s for s in students_db.values() if s['status'] == 'approved']
    approved_students.sort(key=lambda x: x['gpa'], reverse=True)
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

    if nat_id in students_db:
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

    # حفظ الطالب
    students_db[nat_id] = {
        "nat_id": nat_id,
        "name": name,
        "gpa": gpa,
        "status": "approved"  # تقدر تخليها pending لو عاوز تراجع الأول
    }

    flash("✅ تم حفظ البيانات بنجاح! لا يمكن تعديل GPA إلا بواسطة المسؤول.", "success")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)