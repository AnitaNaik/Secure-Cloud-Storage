
from cryptography.fernet import Fernet
from flask import Flask, render_template, request, redirect, url_for,session
import sqlite3
import os

KEY_FILE = "secret.key"

def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
    else:
        with open(KEY_FILE, "rb") as key_file:
            key = key_file.read()
    return key

key = load_key()
fernet = Fernet(key)

app = Flask(__name__)
app.secret_key = 'secret123'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


#database setup(runs code)
def init_db():
    conn = sqlite3.connect('secure_storage.db')
    cursor=conn.cursor()
    conn.execute('CREATE TABLE IF NOT EXISTS users (username TEXT UNIQUE NOT NULL, password TEXT NOT NULL)')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('home.html')
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Connect and store user data
        conn = sqlite3.connect('secure_storage.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))

        return "Signup successful 🎉 Now you can log in!"

    return render_template('signup.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('secure_storage.db')
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM users WHERE username=? AND password=?',
            (username, password)
        )
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = username
            return redirect(url_for('home'))
        else:
            error = "Invalid username or password"

    return render_template('login.html', error=error)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['file']

        if file:
            user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['user'])
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)

            file_data = file.read()                 # read file
            encrypted_data = fernet.encrypt(file_data)  # encrypt

            file_path = os.path.join(user_folder, file.filename)
            with open(file_path, "wb") as f:
                f.write(encrypted_data)             # save encrypted file

            return redirect(url_for('files'))

    return render_template('update.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/files')
def files():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['user'])

    if not os.path.exists(user_folder):
        file_list = []
    else:
        file_list = os.listdir(user_folder)

    return render_template('files.html', files=file_list)

from flask import send_from_directory

@app.route('/download/<filename>')
def download(filename):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['user'])
    file_path = os.path.join(user_folder, filename)

    with open(file_path, "rb") as f:
        encrypted_data = f.read()

    decrypted_data = fernet.decrypt(encrypted_data)

    return decrypted_data, 200, {
        'Content-Disposition': f'attachment; filename={filename}'
    }

@app.route('/delete/<filename>')
def delete(filename):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], session['user'])

    file_path = os.path.join(user_folder, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    return redirect(url_for('files'))


if __name__ == "__main__":
    app.run(debug=True)
