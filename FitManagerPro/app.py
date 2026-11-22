import os, csv, io
from datetime import date, datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"


def _database_uri():
    """Return the database URL. Render/Heroku still hand out the legacy
    `postgres://` scheme which SQLAlchemy no longer accepts."""
    url = os.getenv("DATABASE_URL", "sqlite:///fitmanager.db")
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or ("dev-only-insecure-secret" if DEBUG else None)
if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "SECRET_KEY environment variable is required. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "1") == "1"
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
# Render terminates TLS at its proxy; trust its forwarded headers.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="admin", nullable=False)

class Plan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    duration_months = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False, default=0)

class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_code = db.Column(db.String(30), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    gender = db.Column(db.String(20))
    age = db.Column(db.Integer)
    address = db.Column(db.String(255))
    joining_date = db.Column(db.Date, nullable=False, default=date.today)
    plan_id = db.Column(db.Integer, db.ForeignKey("plan.id"))
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    expiry_date = db.Column(db.Date, nullable=False)
    fee = db.Column(db.Numeric(10,2), nullable=False, default=0)
    payment_status = db.Column(db.String(20), default="Pending")
    whatsapp_consent = db.Column(db.Boolean, default=False)
    plan = db.relationship("Plan")
    payments = db.relationship("Payment", backref="member", cascade="all, delete-orphan")
    attendance = db.relationship("Attendance", backref="member", cascade="all, delete-orphan")

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default="Paid")
    reference = db.Column(db.String(100))
    paid_at = db.Column(db.DateTime, default=datetime.now)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    checkin_at = db.Column(db.DateTime, default=datetime.now)
    checkout_at = db.Column(db.DateTime)

class Trainer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    specialty = db.Column(db.String(120))

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"))
    channel = db.Column(db.String(30), default="System")
    message = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(30), default="Queued")
    created_at = db.Column(db.DateTime, default=datetime.now)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80))
    action = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def log_action(action):
    db.session.add(ActivityLog(username=session.get("username", "system"), action=action))
    db.session.commit()

def add_months(d, months):
    import calendar
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

@app.context_processor
def inject_globals():
    return {"today": date.today(), "show_demo_credentials": DEBUG}


@app.route("/healthz")
def healthz():
    return jsonify(status="ok")

@app.route("/")
def home():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username","").strip()).first()
        if user and check_password_hash(user.password_hash, request.form.get("password","")):
            session.update(user_id=user.id, username=user.username, role=user.role)
            return redirect(url_for("dashboard"))
        flash("Incorrect username or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    members = Member.query.all()
    active = sum(1 for m in members if m.expiry_date >= date.today())
    expired = len(members) - active
    month_start = date.today().replace(day=1)
    monthly_revenue = db.session.query(db.func.coalesce(db.func.sum(Payment.amount),0)).filter(
        Payment.status=="Paid", Payment.paid_at >= datetime.combine(month_start, datetime.min.time())).scalar()
    total_revenue = db.session.query(db.func.coalesce(db.func.sum(Payment.amount),0)).filter_by(status="Paid").scalar()
    pending = Member.query.filter_by(payment_status="Pending").count()
    recent = Member.query.order_by(Member.id.desc()).limit(5).all()
    upcoming = Member.query.filter(Member.expiry_date >= date.today(),
        Member.expiry_date <= date.today()+timedelta(days=7)).order_by(Member.expiry_date).limit(8).all()
    payments = Payment.query.order_by(Payment.paid_at.desc()).limit(6).all()
    plan_counts = {p.name: Member.query.filter_by(plan_id=p.id).count() for p in Plan.query.all()}
    return render_template("dashboard.html", total=len(members), active=active, expired=expired,
        pending=pending, monthly_revenue=monthly_revenue, total_revenue=total_revenue,
        recent=recent, upcoming=upcoming, payments=payments, plan_labels=list(plan_counts.keys()),
        plan_values=list(plan_counts.values()))

@app.route("/members")
@login_required
def members():
    q = request.args.get("q","").strip()
    status = request.args.get("status","")
    query = Member.query
    if q:
        query = query.filter(db.or_(Member.name.ilike(f"%{q}%"), Member.phone.ilike(f"%{q}%"), Member.member_code.ilike(f"%{q}%")))
    if status == "Active": query = query.filter(Member.expiry_date >= date.today())
    if status == "Expired": query = query.filter(Member.expiry_date < date.today())
    rows = query.order_by(Member.id.desc()).all()
    return render_template("members.html", members=rows, q=q, status=status)

@app.route("/members/add", methods=["GET","POST"])
@app.route("/members/<int:member_id>/edit", methods=["GET","POST"])
@login_required
def member_form(member_id=None):
    member = Member.query.get_or_404(member_id) if member_id else None
    plans = Plan.query.order_by(Plan.duration_months).all()
    if request.method == "POST":
        plan = Plan.query.get(int(request.form["plan_id"])) if request.form.get("plan_id") else None
        start = date.fromisoformat(request.form.get("start_date") or date.today().isoformat())
        expiry = date.fromisoformat(request.form["expiry_date"]) if request.form.get("expiry_date") else add_months(start, plan.duration_months if plan else 1)
        if not member:
            member = Member(member_code=f"FMP-{datetime.now():%y%m%d%H%M%S}", joining_date=date.today())
            db.session.add(member)
        member.name=request.form["name"].strip()
        member.phone=request.form["phone"].strip()
        member.email=request.form.get("email","").strip() or None
        member.gender=request.form.get("gender") or None
        member.age=int(request.form["age"]) if request.form.get("age") else None
        member.address=request.form.get("address","").strip() or None
        member.plan_id=plan.id if plan else None
        member.start_date=start
        member.expiry_date=expiry
        member.fee=float(request.form.get("fee") or (plan.price if plan else 0))
        member.payment_status=request.form.get("payment_status","Pending")
        member.whatsapp_consent=bool(request.form.get("whatsapp_consent"))
        db.session.commit()
        log_action(("Updated" if member_id else "Added")+" member "+member.member_code)
        flash("Member saved successfully.", "success")
        return redirect(url_for("members"))
    return render_template("member_form.html", member=member, plans=plans)

@app.route("/members/<int:member_id>/delete", methods=["POST"])
@login_required
def member_delete(member_id):
    m=Member.query.get_or_404(member_id)
    db.session.delete(m); db.session.commit()
    log_action("Deleted member "+m.member_code)
    flash("Member deleted.", "success")
    return redirect(url_for("members"))

@app.route("/members/<int:member_id>")
@login_required
def member_detail(member_id):
    m=Member.query.get_or_404(member_id)
    return render_template("member_detail.html", member=m)

@app.route("/plans", methods=["GET","POST"])
@login_required
def plans():
    if request.method=="POST":
        p=Plan(name=request.form["name"].strip(), duration_months=int(request.form["duration_months"]), price=float(request.form["price"]))
        db.session.add(p)
        try: db.session.commit(); flash("Plan created.","success")
        except: db.session.rollback(); flash("Plan name already exists.","danger")
        return redirect(url_for("plans"))
    return render_template("plans.html", plans=Plan.query.order_by(Plan.duration_months).all())

@app.route("/payments", methods=["GET","POST"])
@login_required
def payments():
    if request.method=="POST":
        member=Member.query.get_or_404(int(request.form["member_id"]))
        amount=float(request.form["amount"])
        p=Payment(member_id=member.id, amount=amount, method=request.form["method"], status="Paid",
                  reference=request.form.get("reference","").strip() or None)
        db.session.add(p); member.payment_status="Paid"
        db.session.commit(); log_action(f"Recorded payment for {member.member_code}")
        flash("Payment recorded. For cash/UPI, staff confirmation is recorded as paid.","success")
        return redirect(url_for("payments"))
    return render_template("payments.html", payments=Payment.query.order_by(Payment.paid_at.desc()).all(),
                           members=Member.query.order_by(Member.name).all())

@app.route("/attendance", methods=["GET","POST"])
@login_required
def attendance():
    if request.method=="POST":
        mid=int(request.form["member_id"])
        open_entry=Attendance.query.filter_by(member_id=mid, checkout_at=None).first()
        if request.form["action"]=="in":
            if open_entry: flash("This member is already checked in.","warning")
            else: db.session.add(Attendance(member_id=mid)); db.session.commit(); flash("Check-in recorded.","success")
        else:
            if open_entry: open_entry.checkout_at=datetime.now(); db.session.commit(); flash("Check-out recorded.","success")
            else: flash("No open check-in found.","warning")
        return redirect(url_for("attendance"))
    return render_template("attendance.html", members=Member.query.order_by(Member.name).all(),
                           entries=Attendance.query.order_by(Attendance.checkin_at.desc()).limit(100).all())

@app.route("/trainers", methods=["GET","POST"])
@login_required
def trainers():
    if request.method=="POST":
        db.session.add(Trainer(name=request.form["name"], phone=request.form.get("phone"), specialty=request.form.get("specialty")))
        db.session.commit(); flash("Trainer added.","success"); return redirect(url_for("trainers"))
    return render_template("trainers.html", trainers=Trainer.query.order_by(Trainer.name).all())

@app.route("/reports")
@login_required
def reports():
    start=request.args.get("start", date.today().replace(day=1).isoformat())
    end=request.args.get("end", date.today().isoformat())
    payments=Payment.query.filter(Payment.paid_at >= datetime.combine(date.fromisoformat(start),datetime.min.time()),
                                  Payment.paid_at < datetime.combine(date.fromisoformat(end)+timedelta(days=1),datetime.min.time()),
                                  Payment.status=="Paid").all()
    return render_template("reports.html", payments=payments, start=start, end=end,
                           revenue=sum(float(p.amount) for p in payments))

@app.route("/reports/export.csv")
@login_required
def export_csv():
    output=io.StringIO(); writer=csv.writer(output)
    writer.writerow(["Payment ID","Member","Amount INR","Method","Status","Date"])
    for p in Payment.query.order_by(Payment.paid_at.desc()).all():
        writer.writerow([p.id,p.member.name,float(p.amount),p.method,p.status,p.paid_at.strftime("%Y-%m-%d %H:%M")])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment; filename=fitmanager-payments.csv"})

@app.route("/activity")
@login_required
def activity():
    return render_template("activity.html", logs=ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(100).all())

@app.cli.command("init-db")
def init_db():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", password_hash=generate_password_hash(os.getenv("ADMIN_PASSWORD","Admin@12345")), role="admin"))
    defaults=[("Monthly",1,1200),("Quarterly",3,3200),("Half-Yearly",6,6000),("Yearly",12,10000)]
    for name,months,price in defaults:
        if not Plan.query.filter_by(name=name).first(): db.session.add(Plan(name=name,duration_months=months,price=price))
    db.session.commit()
    print("Database ready. Login as 'admin' with the ADMIN_PASSWORD you configured.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=DEBUG)
