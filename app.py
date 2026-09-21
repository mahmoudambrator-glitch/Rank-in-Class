from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import os
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    session,
    send_file,
)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# إعداد قاعدة البيانات وتوافقها مع المحلي و Render
db_url = os.environ.get('DATABASE_URL')
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:///library_and_ranking.db'
app.config['SECRET_KEY'] = 'my_super_secret_combined_key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)

# --- نماذج قاعدة البيانات ---

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    files = db.relationship(
        'MaterialFile', backref='subject', lazy=True, cascade='all, delete'
    )

class MaterialFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    file_type = db.Column(db.String(50))
    file_path = db.Column(db.String(500), nullable=False)
    views_count = db.Column(db.Integer, default=0)
    subject_id = db.Column(
        db.Integer, db.ForeignKey('subject.id'), nullable=False
    )

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nat_id = db.Column(db.String(14), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    gpa = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="approved")

class VisitLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_type = db.Column(db.String(50), default="زائر عام") 
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Africa/Cairo")))
    page_visited = db.Column(db.String(200), default='دخول الموقع')

class TrackingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_type = db.Column(db.String(50), default="زائر عام") 
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Africa/Cairo")))
    action_performed = db.Column(db.String(200))

class StudentActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(150), nullable=False)
    nat_id = db.Column(db.String(14), nullable=False)
    action_type = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("Africa/Cairo")))


with app.app_context():
    db.create_all()

import uuid

@app.before_request
def track_visit():
    if not request.path.startswith('/static') and not request.path.startswith('/admin') and 'favicon.ico' not in request.path:
        if 'visitor_uuid' not in session:
            session['visitor_uuid'] = str(uuid.uuid4())
            session['has_visited'] = False

        current_visitor = session.get('student_name') or 'زائر عام'

        # تعديل عداد الزيارات ليحسب مع كل فتح جديد للموقع أو انتهاء الجلسة عند الصفر
        if request.path == '/' and not session.get('counted_this_session'):
            visit = VisitLog(
                visitor_type=current_visitor,
                ip_address=request.remote_addr, 
                page_visited='دخول الموقع'
            )
            db.session.add(visit)
            db.session.commit()
            session['counted_this_session'] = True

        # كود تتبع الخطوات والتنقل الأصلي كما هو تماماً دون أي تغيير
        last_track = TrackingLog.query.filter_by(ip_address=request.remote_addr).order_by(TrackingLog.timestamp.desc()).first()
        
        if not last_track or last_track.action_performed != request.path or last_track.visitor_type != current_visitor:
            track = TrackingLog(
                visitor_type=current_visitor,
                ip_address=request.remote_addr,
                action_performed=request.path
            )
            db.session.add(track)
            db.session.commit()
            
@app.route('/')
def home():
    subjects = Subject.query.order_by(Subject.name.asc()).all()
    return render_template('home.html', subjects=subjects)

@app.route('/subject/<int:subject_id>')
def subject_detail(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    return render_template('subject_detail.html', subject=subject)

@app.route('/open_file/<int:file_id>')
def open_file(file_id):
    file_item = MaterialFile.query.get_or_404(file_id)
    if file_item.file_path:
        file_item.views_count = (file_item.views_count or 0) + 1
        db.session.commit()
        return redirect(file_item.file_path)
    
    flash('❌ الرابط المطلوب غير موجود!', 'danger')
    return redirect(url_for('home'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    total_visits = VisitLog.query.count()
    subjects = Subject.query.order_by(Subject.name.asc()).all()
    all_files = MaterialFile.query.join(Subject).order_by(Subject.name.asc(), MaterialFile.title.asc()).all()
    recent_visits = VisitLog.query.order_by(VisitLog.timestamp.desc()).all()
    recent_trackings = TrackingLog.query.order_by(TrackingLog.timestamp.desc()).all()
    students = Student.query.order_by(Student.gpa.desc()).all()
    student_activities = StudentActivityLog.query.order_by(StudentActivityLog.timestamp.desc()).all()

    return render_template(
        'admin.html',
        total_visits=total_visits,
        subjects=subjects,
        all_files=all_files,
        recent_visits=recent_visits,
        recent_trackings=recent_trackings,
        students=students,
        student_activities=student_activities
    )

@app.route('/admin/clear_visits', methods=['POST'])
def clear_visits():
    try:
        db.session.query(VisitLog).delete()
        db.session.commit()
        flash('🗑️ تم تصفير سجلات الزيارات بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('❌ حدث خطأ أثناء التصفير', 'danger')
    return redirect(url_for('admin'))

@app.route('/admin/clear_tracking', methods=['POST'])
def clear_tracking():
    try:
        db.session.query(TrackingLog).delete()
        db.session.commit()
        flash('🗑️ تم تصفير سجلات التتبع بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('❌ حدث خطأ أثناء التصفير', 'danger')
    return redirect(url_for('admin'))

@app.route('/admin/add_subject', methods=['POST'])
def add_subject():
    name = request.form.get('name')
    description = request.form.get('description')
    if name:
        db.session.add(Subject(name=name, description=description))
        db.session.commit()
        flash('تم إضافة المادة بنجاح', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/edit_subject/<int:subject_id>', methods=['POST'])
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    new_name = request.form.get('name')
    description = request.form.get('description')
    if new_name:
        subject.name = new_name
        if description is not None:
            subject.description = description
        db.session.commit()
        flash('تم تعديل المادة بنجاح!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/add_file', methods=['POST'])
def add_file():
    title = request.form.get('title')
    file_type = request.form.get('file_type')
    drive_url = request.form.get('drive_url')
    subject_id_raw = request.form.get('subject_id')
    
    if not subject_id_raw or not title or not drive_url:
        flash('❌ يرجى ملء جميع الحقول المطلوبة!', 'danger')
        return redirect(url_for('admin'))

    try:
        subject_id = int(subject_id_raw)
    except ValueError:
        flash('❌ خطأ في معرف المادة!', 'danger')
        return redirect(url_for('admin'))

    new_file = MaterialFile(
        title=title,
        file_type=file_type,
        file_path=drive_url,
        subject_id=subject_id,
    )
    db.session.add(new_file)
    db.session.commit()
    flash('تم إضافة رابط الملف بنجاح!', 'success')

    return redirect(url_for('admin'))

@app.route('/admin/edit_file/<int:file_id>', methods=['POST'])
def edit_file(file_id):
    file_item = MaterialFile.query.get_or_404(file_id)
    file_item.subject_id = request.form.get('subject_id')
    file_item.title = request.form.get('title')
    file_item.file_type = request.form.get('file_type')
    file_item.file_path = request.form.get('drive_url')
    
    db.session.commit()
    flash('تم تعديل الملف بنجاح!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_subject/<int:subject_id>', methods=['POST'])
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    db.session.delete(subject)
    db.session.commit()
    flash('تم حذف المادة بنجاح', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_file/<int:file_id>', methods=['POST'])
def delete_file(file_id):
    file_item = MaterialFile.query.get_or_404(file_id)
    db.session.delete(file_item)
    db.session.commit()
    flash('تم حذف الملف بنجاح', 'success')
    return redirect(url_for('admin'))

@app.route("/ranking", methods=["GET", "POST"])
def student_ranking():
    result = None

    if request.method == "POST":
        action = request.form.get("action_type")
        
        if action == "query":
            nat_id = request.form.get("query_nat_id", "").strip()
            student = Student.query.filter_by(nat_id=nat_id).first()
            if student:
                session.permanent = True
                session['student_name'] = student.name
                rank = Student.query.filter(Student.gpa > student.gpa).count() + 1
                total = Student.query.count()
                result = {"name": student.name, "rank": rank, "total": total}
                
                log = StudentActivityLog(
                    student_name=student.name,
                    nat_id=nat_id,
                    action_type="استعلام عن الترتيب"
                )
                db.session.add(log)
                db.session.commit()
            else:
                flash("❌ الرقم القومي غير مسجل في النظام!", "danger")
                
        elif action == "register":
            name = request.form.get("name", "").strip()
            nat_id = request.form.get("nat_id", "").strip()
            gpa_raw = request.form.get("gpa", "").strip()

            if len(name.split()) < 3:
                flash("❌ يجب كتابة الاسم ثلاثياً على الأقل!", "danger")
                return redirect("/ranking")

            if not (nat_id.isdigit() and len(nat_id) == 14):
                flash("❌ الرقم القومي يجب أن يتكون من 14 رقماً!", "danger")
                return redirect("/ranking")

            if Student.query.filter_by(nat_id=nat_id).first():
                flash("⚠️ هذا الرقم القومي مسجل بالفعل!", "warning")
                return redirect("/ranking")

            try:
                gpa = float(gpa_raw)
                if not (0.0 <= gpa <= 4.0):
                    raise ValueError
            except ValueError:
                flash("❌ يرجى إدخال GPA صحيح بين 0.00 و 4.00", "danger")
                return redirect("/ranking")

            new_student = Student(nat_id=nat_id, name=name, gpa=gpa, status="approved")
            db.session.add(new_student)
            
            log = StudentActivityLog(
                student_name=name,
                nat_id=nat_id,
                action_type="تسجيل جديد في الدفعة"
            )
            db.session.add(log)
            db.session.commit()
            
            session.permanent, session['student_name'] = True, name
            
            rank = Student.query.filter(Student.gpa > gpa).count() + 1
            total = Student.query.count()
            result = {"name": name, "rank": rank, "total": total}
            flash("✅ تم حفظ البيانات بنجاح!", "success")

    return render_template("ranking.html", result=result)

@app.route("/admin/delete_student/<int:id>", methods=["POST"])
def delete_student(id):
    student = Student.query.get_or_404(id)
    db.session.delete(student)
    db.session.commit()
    flash("🗑️ تم حذف الطالب بنجاح!", "success")
    return redirect("/admin")

@app.route("/admin/update_student/<int:id>", methods=["POST"])
def update_student_gpa(id):
    student = Student.query.get_or_404(id)
    try:
        gpa = float(request.form.get("gpa"))
        if 0.0 <= gpa <= 4.0:
            student.gpa = gpa
            db.session.commit()
            flash("✅ تم تحديث الـ GPA بنجاح!", "success")
        else:
            flash("❌ القيمة يجب أن تكون بين 0.00 و 4.00", "danger")
    except ValueError:
        flash("❌ يرجى إدخال رقم صحيح للـ GPA", "danger")
    return redirect("/admin")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
