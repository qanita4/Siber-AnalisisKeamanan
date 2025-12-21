# from flask import Flask, render_template, request, redirect, url_for
# from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy import text
# import sqlite3

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os

# app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        return f'<Student {self.name}>'

def login_required(f): 
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Middleware to prevent caching for all pages
@app.after_request
def add_header(response):           #(menambahkan) fungsi add_header
    # Mencegah caching pada semua halaman untuk menghindari masalah tombol kembali
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/registrasi', methods=['GET', 'POST'])
def register():     # (menambahkan) fungsi register
    # Jika sudah login, arahkan ke index
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

    # Periksa apakah pengguna sudah terdaftar
        existing_user = db.session.execute(
            text("SELECT * FROM user WHERE username = :username"),
            {'username': username}
        ).fetchone()
        
        if existing_user:
            flash('Username sudah terdaftar!', 'danger')
            return redirect(url_for('register'))
        
    # Hash password dan buat pengguna
        hashed_password = generate_password_hash(password)
        db.session.execute(
            text("INSERT INTO user (username, password) VALUES (:username, :password)"),
            {'username': username, 'password': hashed_password}
        )
        db.session.commit()
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('registrasi.html')

@app.route('/login', methods=['GET', 'POST'])
def login():   # (menambahkan) fungsi login
    # Jika sudah login, arahkan ke index
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
    # Periksa kredensial pengguna
        user = db.session.execute(
            text("SELECT * FROM user WHERE username = :username"),
            {'username': username}
        ).fetchone()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login berhasil!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Username atau password salah!', 'danger')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()  # Hapus semua data sesi
    flash('Anda telah logout.', 'info')
    response = redirect(url_for('login'))
    response.set_cookie('session', '', expires=0)  # Hapus cookie sesi
    return response

@app.route('/')
def index():
    # Kuery RAW (tetap digunakan untuk membaca daftar; pastikan data ditampilkan dengan escaping di template)
    students = db.session.execute(text('SELECT * FROM student')).fetchall()
    return render_template('index.html', students=students)

@app.route('/add', methods=['POST'])
@login_required         # (menambahkan) memastikan hanya pengguna yang sudah login yang dapat menambahkan siswa
def add_student():
    # Ambil data langsung dari form (validasi client-side diasumsikan ada di HTML)
    name = request.form.get('name')
    age = request.form.get('age')
    grade = request.form.get('grade')

    # Gunakan query parameterized untuk penyimpanan (tetap aman terhadap SQL injection)
    db.session.execute(
        text("INSERT INTO student (name, age, grade) VALUES (:name, :age, :grade)"),
        {'name': name, 'age': age, 'grade': grade}
    )
    db.session.commit()
    flash('Siswa berhasil ditambahkan!', 'success')
    return redirect(url_for('index'))

@app.route('/delete/<string:id>') 
@login_required
def delete_student(id):

    # db.session.execute(text(f"DELETE FROM student WHERE id={id}"))
    # db.session.commit()
    # return redirect(url_for('index'))

    db.session.execute(
        text("DELETE FROM student WHERE id = :id"), 
        {"id": id}                      #(memodifikasi) menggunakan query parameterized
    )
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        grade = request.form['grade']
        
        # db.session.execute(text(f"UPDATE student SET name='{name}', age={age}, grade='{grade}' WHERE id={id}"))
        # db.session.commit()
        # return redirect(url_for('index'))

        db.session.execute(
            text("UPDATE student SET name = :name, age = :age, grade = :grade WHERE id = :id"), # (memodifikasi) menggunakan query parameterized
            {'name': name, 'age': age, 'grade': grade, 'id': id}
        )
        db.session.commit()
        return redirect(url_for('index'))
    
    else:
        # student = db.session.execute(text(f"SELECT * FROM student WHERE id={id}")).fetchone()
        student = db.session.execute(text("SELECT * FROM student WHERE id = :id"), {'id': id}).fetchone() #(memodifikasi) menggunakan query parameterized
        return render_template('edit.html', student=student)


# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()
#     app.run(debug=True)
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    #app.run(host='0.0.0.0', port=5005, debug=True)
    app.run(host='127.0.0.1', port=5005, debug=False)   # (memodifikasi) menonaktifkan debug dan mengubah host menjadi localhost

