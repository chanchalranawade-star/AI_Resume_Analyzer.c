
from flask import Flask, render_template, request, send_file, redirect
from PyPDF2 import PdfReader
from reportlab.pdfgen import canvas
from datetime import datetime
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()
import psycopg2
import psycopg2.extras
app = Flask(__name__)
# Database Create
def get_db_connection():
    return psycopg2.connect(os.environ.get("DATABASE_URL"))


def init_db():

    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT,
        password TEXT
    )
    """)

    # Resume History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resume_history(
        id SERIAL PRIMARY KEY,
        filename TEXT,
        resume_hash TEXT,
        score INTEGER,
        skills TEXT,
        jobs TEXT,
        rating TEXT,
        upload_date TEXT,
        status TEXT DEFAULT 'Pending',
        selected_for TEXT DEFAULT '-'
    )
    """)
    cursor.execute("""
ALTER TABLE resume_history
ADD COLUMN IF NOT EXISTS resume_hash TEXT
""")

    conn.commit()
    cursor.close()
    conn.close()


init_db()
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# Home Page
@app.route('/')
def home():
    return render_template('index.html')


# Login Page
@app.route('/login')
def login():
    return render_template('login.html')


# Register Page
@app.route('/register')
def register():
    return render_template('register.html')
@app.route('/register_user', methods=['POST'])
def register_user():

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if email already exists
    cursor.execute(
        "SELECT id FROM users WHERE email=%s",
        (email,)
    )

    existing_user = cursor.fetchone()

    if existing_user:
        cursor.close()
        conn.close()

        return """
        <h2>Email already registered!</h2>
        <p>Please login using your existing email and password.</p>
        <a href="/login">Go to Login</a>
        """

    # Create new user
    cursor.execute(
        "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
        (name, email, password)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return render_template('login.html')

@app.route('/login_user', methods=['POST'])
def login_user():

    email = request.form['email']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=%s AND password=%s",
        (email, password)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM resume_history")
        total_resumes = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return render_template(
            'dashboard.html',
            username=user[1],
            total_users=total_users,
            total_resumes=total_resumes
        )

    else:
        return """
        <h2>Invalid Email or Password</h2>
        <a href="/login">Try Again</a>
        """
# Dashboard Page
@app.route('/dashboard')
def dashboard():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM resume_history")
    total_resumes = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        username="User",
        total_users=total_users,
        total_resumes=total_resumes
    )
@app.route('/analysis')
def analysis():
    return render_template("analysis.html")
@app.route('/upload', methods=['POST'])
def upload():

    file = request.files['resume']
    filename = file.filename

    file_data = file.read()
    resume_hash = hashlib.sha256(file_data).hexdigest()
    file.seek(0)

    # Check if this resume was already uploaded
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM resume_history WHERE resume_hash=%s",
        (resume_hash,)
    )

    duplicate = cursor.fetchone()

    if duplicate:
        cursor.close()
        conn.close()
        return """
        <h2>Duplicate Resume!</h2>
        <p>This resume has already been uploaded.</p>
        <a href="/dashboard">Go to Dashboard</a>
        """

    communication = int(request.form['communication'])
    personality = int(request.form['personality'])
    logical = int(request.form['logical'])

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    reader = PdfReader(filepath)

    # Check if PDF is password protected
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            return """
            <h2>❌ Password Protected PDF</h2>
            <p>Please upload a PDF that is not password protected.</p>
            <a href="/analysis">Upload Another Resume</a>
            """

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text

    skill_list = [
        "Python",
        "HTML",
        "CSS",
        "Flask",
        "SQL",
        "Java"
    ]

    skills = []

    for skill in skill_list:
        if skill.lower() in text.lower():
            skills.append(skill)

    weaknesses = []

    for skill in skill_list:
        if skill not in skills:
            weaknesses.append(skill)

    suggestions = []

    if "Python" not in skills:
        suggestions.append("Learn Python Programming")

    if "SQL" not in skills:
        suggestions.append("Learn SQL and Database Management")

    if "Flask" not in skills:
        suggestions.append("Learn Flask Framework")

    if "Java" not in skills:
        suggestions.append("Improve Java Skills")

    if len(skills) < 4:
        suggestions.append("Add more technical skills")

    suggestions.append("Add LinkedIn Profile")
    suggestions.append("Add Certifications")

    strengths = [
        "Resume uploaded successfully",
        "Skills detected automatically"
    ]

    jobs = []

    if "Python" in skills:
        jobs.append("Python Developer")

    if "HTML" in skills or "CSS" in skills:
        jobs.append("Frontend Developer")

    if "Flask" in skills:
        jobs.append("Backend Developer")

    if "SQL" in skills:
        jobs.append("Database Developer")

    if "Java" in skills:
        jobs.append("Java Developer")

    if not jobs:
        jobs.append("Software Engineer")

    language_marks = min(len(skills) * 2, 10)
    technical_marks = min(len(skills) * 5, 30)
    job_marks = min(len(jobs) * 6, 30)

    score = (
        language_marks +
        communication +
        personality +
        logical +
        technical_marks +
        job_marks
    )

    if score > 100:
        score = 100

    if score >= 80:
        rating = "Excellent"
    elif score >= 60:
        rating = "Good"
    elif score >= 40:
        rating = "Average"
    else:
        rating = "Needs Improvement"
    print("COMMUNICATION:", communication)
    print("PERSONALITY:", personality)
    print("LOGICAL:", logical)
    print("LANGUAGE:", language_marks)
    print("TECHNICAL:", technical_marks)
    print("JOB:", job_marks)
    status = "Pending"
    selected_for = "-"
    conn = get_db_connection()
    cursor = conn.cursor()

    upload_date = datetime.now().strftime("%d-%m-%Y %I:%M %p")

    cursor.execute(
        """
        INSERT INTO resume_history
        (filename, resume_hash, score, skills, jobs, rating, upload_date, status, selected_for)
        VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            filename,
            resume_hash,
            score,
            ", ".join(skills),
            ", ".join(jobs),
            rating,
            upload_date,
            status,
            selected_for
        )
    )

    conn.commit()
    cursor.close()
    conn.close()

    return render_template(
        "result.html",
        score=score,
        skills=skills,
        strengths=strengths,
        suggestions=suggestions,
        jobs=jobs,
        filename=filename,
        rating=rating,
        weaknesses=weaknesses,
        communication=communication,
        personality=personality,
        logical=logical,
        language_marks=language_marks,
        technical_marks=technical_marks,
        job_marks=job_marks
    )
@app.route('/history')
def history():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id,
           filename,
           score,
           upload_date,
           rating,
           status,
           selected_for
    FROM resume_history
    """)

    records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "history.html",
        records=records
    )
@app.route("/view/<int:id>")
def view_resume(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, filename, score, upload_date, status, selected_for
        FROM resume_history
        WHERE id = %s
    """, (id,))

    record = cursor.fetchone()

    cursor.close()
    conn.close()

    from_hr = request.args.get("from") == "hr"

    return render_template(
        "view.html",
        record=record,
        from_hr=from_hr
    )
@app.route('/hrlogin', methods=['GET', 'POST'])
def hrlogin():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == "Sudarshan" and password == os.environ.get("HR_PASSWORD"):
            return redirect('/hrdashboard')

        else:
            return "<h2>Invalid HR Username or Password</h2>"

    return render_template("hrlogin.html")
@app.route('/hrdashboard')
def hrdashboard():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id,
           filename,
           score,
           rating,
           status,
           selected_for
    FROM resume_history
    """)

    records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'hrdashboard.html',
        records=records
    )


@app.route('/registered_users')
def registered_users():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, email
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'registered_users.html',
        users=users
    )

@app.route('/select/<int:id>')
def select(id):

    return render_template(
        "select_candidate.html",
        id=id
    )
@app.route('/selected')
def selected():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM resume_history
    WHERE status = 'Selected'
    """)

    records = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "selected.html",
        records=records
    )
@app.route('/save_selection/<int:id>', methods=['POST'])
def save_selection(id):

    job = request.form['job']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
    """
    UPDATE resume_history
    SET status='Selected',
        selected_for=%s
    WHERE id=%s
    """,
    (job, id)
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/hrdashboard')
@app.route('/reject/<int:id>')
def reject(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE resume_history
        SET status='Rejected',
            selected_for='-'
        WHERE id=%s
    """, (id,))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect('/hrdashboard')
@app.route('/logout')
def logout():
    return render_template('login.html')
from flask import send_from_directory

@app.route("/resume/<filename>")
def view_resume_pdf(filename):
    return send_from_directory("uploads", filename)
@app.route('/download_report')
def download_report():

    pdf_file = "resume_report.pdf"

    c = canvas.Canvas(pdf_file)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, 800, "AI Resume Analysis Report")

    c.setFont("Helvetica", 12)
    c.drawString(50, 750, "Resume Score : 85%")
    c.drawString(50, 720, "Rating : Good")

    c.drawString(50, 680, "Detected Skills:")
    c.drawString(70, 660, "- Python")
    c.drawString(70, 640, "- HTML")
    c.drawString(70, 620, "- CSS")
    c.drawString(70, 600, "- Flask")
    c.drawString(70, 580, "- SQL")

    c.save()

    return send_file(
        pdf_file,
        as_attachment=True
    )

    return render_template("view.html", record=record)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)