from cryptography.fernet import Fernet

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

import sqlite3
import os
import hashlib

# Werkzeug is used for secure password hashing.
# generate_password_hash() creates a salted password hash.
# check_password_hash() verifies a password during login.
from werkzeug.security import generate_password_hash, check_password_hash

# secure_filename() helps make uploaded filenames safer.
from werkzeug.utils import secure_filename

from sqlite3 import IntegrityError


# ============================================================
# FLASK APPLICATION SETUP
# ============================================================

app = Flask(__name__)

# Secret key is used by Flask to protect sessions.
# For a real production application, this should be stored
# securely as an environment variable instead of writing it
# directly in the source code.
app.secret_key = 'secret123'


# ============================================================
# FILE UPLOAD SETTINGS
# ============================================================

UPLOAD_FOLDER = 'uploads'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Maximum file size allowed for upload.
# Here we are allowing files up to 10 MB.
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024


# ============================================================
# FERNET ENCRYPTION
# ============================================================

KEY_FILE = "secret.key"


def load_key():
    """
    Load the Fernet encryption key.

    If secret.key does not exist:
        - Generate a new key.
        - Save it in secret.key.

    If it already exists:
        - Read the existing key.

    The same key must be used to decrypt files that
    were encrypted earlier.
    """

    if not os.path.exists(KEY_FILE):

        # Generate a new Fernet encryption key.
        key = Fernet.generate_key()

        # Save the key in a file.
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)

    else:

        # Read the existing encryption key.
        with open(KEY_FILE, "rb") as key_file:
            key = key_file.read()

    return key


# Load the encryption key.
key = load_key()

# Create the Fernet encryption/decryption object.
fernet = Fernet(key)


# ============================================================
# DATABASE SETUP
# ============================================================

def init_db():
    """
    Create the required database tables if they do not exist.

    users table:
        Stores usernames and password hashes.

    files table:
        Stores information about uploaded files,
        including their SHA-256 hash.
    """

    conn = sqlite3.connect('secure_storage.db')

    cursor = conn.cursor()

    # --------------------------------------------------------
    # USERS TABLE
    # --------------------------------------------------------
    #
    # Your existing project already has this table:
    #
    # users(username, password)
    #
    # We are keeping the same column name "password" so that
    # your existing database does not need to be recreated.
    #
    # IMPORTANT:
    # The password column will now contain a HASH,
    # not the original password.
    #

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # --------------------------------------------------------
    # FILES TABLE
    # --------------------------------------------------------
    #
    # This table stores the SHA-256 hash of each uploaded file.
    #
    # username  -> owner of the file
    # filename  -> name of the file
    # file_hash -> SHA-256 hash of original file contents
    #

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            UNIQUE(username, filename)
        )
    ''')

    conn.commit()
    conn.close()


# Run database setup when the application starts.
init_db()


# ============================================================
# DELETE ALL FILES OF A USER
# ============================================================

def delete_user_files(username):
    """
    Delete all files belonging to a user.

    This removes:
    1. The user's physical encrypted files from uploads/
    2. The user's file records from the files table
    """

    # --------------------------------------------------------
    # USER-SPECIFIC FOLDER
    # --------------------------------------------------------

    user_folder = os.path.join(
        app.config['UPLOAD_FOLDER'],
        username
    )

    # --------------------------------------------------------
    # DELETE PHYSICAL FILES
    # --------------------------------------------------------

    if os.path.exists(user_folder):

        # Go through every item inside the user's folder.
        for filename in os.listdir(user_folder):

            file_path = os.path.join(
                user_folder,
                filename
            )

            # Delete only files.
            if os.path.isfile(file_path):
                os.remove(file_path)

        # Remove the empty user folder.
        os.rmdir(user_folder)

    # --------------------------------------------------------
    # DELETE FILE RECORDS FROM DATABASE
    # --------------------------------------------------------

    conn = sqlite3.connect('secure_storage.db')
    cursor = conn.cursor()

    cursor.execute(
        '''
        DELETE FROM files
        WHERE username=?
        ''',
        (username,)
    )

    conn.commit()
    conn.close()


# ============================================================
# HOME PAGE
# ============================================================

@app.route('/')
def home():
    return render_template('home.html')


# ============================================================
# SIGNUP
# ============================================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():

    error = None

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        # Basic password length check.
        if len(password) < 8:
            error = "Password must be at least 8 characters long."
            return render_template(
                'signup.html',
                error=error
            )

        conn = sqlite3.connect('secure_storage.db')
        cursor = conn.cursor()

        try:

            # ------------------------------------------------
            # PASSWORD HASHING
            # ------------------------------------------------
            #
            # generate_password_hash():
            #
            # 1. Takes the original password.
            # 2. Generates a random salt automatically.
            # 3. Uses a password-hashing algorithm.
            # 4. Returns a string containing the information
            #    required to verify the password later.
            #
            # The original password is NOT stored.
            #

            password_hash = generate_password_hash(password)

            cursor.execute(
                '''
                INSERT INTO users (username, password)
                VALUES (?, ?)
                ''',
                (username, password_hash)
            )

            conn.commit()
            conn.close()

            # Signup successful → go to login page.
            return redirect(url_for('login'))

        except IntegrityError:

            # This happens when the username already exists.
            error = "Username already exists. Please choose another username."

            conn.close()

    return render_template(
        'signup.html',
        error=error
    )


# ============================================================
# LOGIN
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('secure_storage.db')
        cursor = conn.cursor()

        # Get the stored password hash for this username.
        cursor.execute(
            'SELECT password FROM users WHERE username=?',
            (username,)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            # user[0] contains the stored password hash.
            stored_password_hash = user[0]

            try:

                # ------------------------------------------------
                # PASSWORD VERIFICATION
                # ------------------------------------------------
                #
                # check_password_hash() takes:
                #
                # stored hash + password entered by user
                #
                # It then verifies whether they match.
                #

                password_correct = check_password_hash(
                    stored_password_hash,
                    password
                )

            except ValueError:

                # ------------------------------------------------
                # OLD PASSWORD SUPPORT
                # ------------------------------------------------
                #
                # Your existing database may contain old
                # plaintext passwords because the old version
                # stored passwords directly.
                #
                # If an old password is found, we check it once
                # and immediately convert it into a secure hash.
                #

                password_correct = (
                    stored_password_hash == password
                )

                if password_correct:

                    new_password_hash = generate_password_hash(
                        password
                    )

                    conn = sqlite3.connect(
                        'secure_storage.db'
                    )

                    cursor = conn.cursor()

                    cursor.execute(
                        '''
                        UPDATE users
                        SET password=?
                        WHERE username=?
                        ''',
                        (
                            new_password_hash,
                            username
                        )
                    )

                    conn.commit()
                    conn.close()

            if password_correct:

                # Store username in the Flask session.
                session['user'] = username

                return redirect(url_for('home'))

        # Login failed.
        error = "Invalid username or password"

    return render_template(
        'login.html',
        error=error
    )


# ============================================================
# UPLOAD FILE
# ============================================================

@app.route('/upload', methods=['GET', 'POST'])
def upload():

    # Only logged-in users can upload files.
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        file = request.files.get('file')

        # Make sure a file was actually selected.
        if file and file.filename:

            # ------------------------------------------------
            # SECURE FILENAME
            # ------------------------------------------------
            #
            # Converts an unsafe filename into a safer filename.
            #
            # Example:
            # ../../secret.txt
            #
            # becomes something like:
            # secret.txt
            #

            filename = secure_filename(
                file.filename
            )

            if not filename:
                return "Invalid filename", 400

            # ------------------------------------------------
            # USER-SPECIFIC FOLDER
            # ------------------------------------------------
            #
            # Each user gets their own folder.
            #
            # Example:
            #
            # uploads/
            #     Anita/
            #         file1.pdf
            #
            #     Rahul/
            #         file2.docx
            #

            user_folder = os.path.join(
                app.config['UPLOAD_FOLDER'],
                session['user']
            )

            if not os.path.exists(user_folder):
                os.makedirs(user_folder)

            # Read the original file.
            file_data = file.read()

            # ------------------------------------------------
            # SHA-256 FILE HASH
            # ------------------------------------------------
            #
            # SHA-256 creates a fingerprint of the file
            # contents.
            #
            # We calculate it BEFORE encryption because we
            # want the hash to represent the original file.
            #

            file_hash = hashlib.sha256(
                file_data
            ).hexdigest()

            # ------------------------------------------------
            # FERNET ENCRYPTION
            # ------------------------------------------------
            #
            # Encrypt the original file before saving it.
            #

            encrypted_data = fernet.encrypt(
                file_data
            )

            # Create the path where encrypted data will be saved.
            file_path = os.path.join(
                user_folder,
                filename
            )

            # Save encrypted file to the uploads folder.
            with open(file_path, "wb") as f:
                f.write(encrypted_data)

            # ------------------------------------------------
            # STORE FILE HASH IN SQLITE
            # ------------------------------------------------
            #
            # Store the SHA-256 hash separately in the database.
            #
            # This hash will later be used by the
            # "Verify Integrity" feature.
            #

            conn = sqlite3.connect(
                'secure_storage.db'
            )

            cursor = conn.cursor()

            cursor.execute(
                '''
                INSERT OR REPLACE INTO files
                (username, filename, file_hash)
                VALUES (?, ?, ?)
                ''',
                (
                    session['user'],
                    filename,
                    file_hash
                )
            )

            conn.commit()
            conn.close()

            return redirect(
                url_for('files')
            )

    return render_template(
        'update.html'
    )


# ============================================================
# VIEW MY FILES
# ============================================================

@app.route('/files')
def files():

    # Only logged-in users can see their files.
    if 'user' not in session:
        return redirect(url_for('login'))

    user_folder = os.path.join(
        app.config['UPLOAD_FOLDER'],
        session['user']
    )

    if not os.path.exists(user_folder):

        file_list = []

    else:

        file_list = os.listdir(
            user_folder
        )

    return render_template(
        'files.html',
        files=file_list
    )


# ============================================================
# DOWNLOAD FILE
# ============================================================

@app.route('/download/<filename>')
def download(filename):

    # Only logged-in users can download files.
    if 'user' not in session:
        return redirect(url_for('login'))

    # Make the filename safe before using it.
    filename = secure_filename(filename)

    user_folder = os.path.join(
        app.config['UPLOAD_FOLDER'],
        session['user']
    )

    file_path = os.path.join(
        user_folder,
        filename
    )

    # Check whether the file exists.
    if not os.path.exists(file_path):
        return "File not found", 404

    # Read the encrypted file.
    with open(file_path, "rb") as f:
        encrypted_data = f.read()

    # Decrypt the file using the Fernet key.
    decrypted_data = fernet.decrypt(
        encrypted_data
    )

    # Return the original file to the user.
    return decrypted_data, 200, {
        'Content-Disposition':
            f'attachment; filename="{filename}"'
    }


# ============================================================
# VERIFY FILE INTEGRITY
# ============================================================

@app.route('/verify/<filename>')
def verify(filename):

    # Only logged-in users can verify their files.
    if 'user' not in session:
        return redirect(url_for('login'))

    # Make filename safe.
    filename = secure_filename(filename)

    username = session['user']

    user_folder = os.path.join(
        app.config['UPLOAD_FOLDER'],
        username
    )

    file_path = os.path.join(
        user_folder,
        filename
    )

    # Check whether the encrypted file exists.
    if not os.path.exists(file_path):
        return "File not found", 404

    # --------------------------------------------------------
    # READ ENCRYPTED FILE
    # --------------------------------------------------------

    with open(file_path, "rb") as f:
        encrypted_data = f.read()

    # --------------------------------------------------------
    # DECRYPT FILE
    # --------------------------------------------------------
    #
    # We decrypt it because the original SHA-256 hash was
    # calculated from the original file contents.
    #

    try:

        file_data = fernet.decrypt(
            encrypted_data
        )

    except Exception:

        return "Unable to decrypt file.", 500

    # --------------------------------------------------------
    # CALCULATE SHA-256 AGAIN
    # --------------------------------------------------------
    #
    # This creates the current hash of the file contents.
    #

    current_hash = hashlib.sha256(
        file_data
    ).hexdigest()

    # --------------------------------------------------------
    # GET ORIGINAL HASH FROM DATABASE
    # --------------------------------------------------------

    conn = sqlite3.connect(
        'secure_storage.db'
    )

    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT file_hash
        FROM files
        WHERE username=? AND filename=?
        ''',
        (
            username,
            filename
        )
    )

    result = cursor.fetchone()

    conn.close()

    # If no hash was found in the database.
    if not result:

        return "File hash not found.", 404

    stored_hash = result[0]

    # --------------------------------------------------------
    # COMPARE THE TWO HASHES
    # --------------------------------------------------------
    #
    # Same hash:
    #       File contents are unchanged.
    #
    # Different hash:
    #       File contents are different from the original
    #       version whose hash was stored.
    #

    if current_hash == stored_hash:

        return '''
        <h2>✅ File Integrity Verified</h2>
        <p>The file has not been modified.</p>
        <a href="/files">Back to My Files</a>
        '''

    else:

        return '''
        <h2>❌ Integrity Check Failed</h2>
        <p>The file contents do not match the original hash.</p>
        <a href="/files">Back to My Files</a>
        '''


# ============================================================
# DELETE FILE
# ============================================================

@app.route('/delete/<filename>')
def delete(filename):

    # Only logged-in users can delete files.
    if 'user' not in session:
        return redirect(url_for('login'))

    # Make filename safe.
    filename = secure_filename(filename)

    username = session['user']

    user_folder = os.path.join(
        app.config['UPLOAD_FOLDER'],
        username
    )

    file_path = os.path.join(
        user_folder,
        filename
    )

    # Delete the encrypted file.
    if os.path.exists(file_path):
        os.remove(file_path)

    # --------------------------------------------------------
    # DELETE THE FILE'S HASH FROM DATABASE
    # --------------------------------------------------------
    #
    # We should also remove the corresponding hash because
    # the file itself no longer exists.
    #

    conn = sqlite3.connect(
        'secure_storage.db'
    )

    cursor = conn.cursor()

    cursor.execute(
        '''
        DELETE FROM files
        WHERE username=? AND filename=?
        ''',
        (
            username,
            filename
        )
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for('files')
    )


# ============================================================
# DELETE USER ACCOUNT
# ============================================================

@app.route('/delete_user', methods=['POST'])
def delete_user():

    # Only logged-in users can delete their own account.
    if 'user' not in session:
        return redirect(url_for('login'))

    # Get the currently logged-in username.
    username = session['user']

    # --------------------------------------------------------
    # DELETE ALL USER FILES
    # --------------------------------------------------------
    #
    # This deletes:
    # 1. Encrypted files from uploads/username/
    # 2. File records from the files table
    #

    delete_user_files(username)

    # --------------------------------------------------------
    # DELETE USER FROM USERS TABLE
    # --------------------------------------------------------

    conn = sqlite3.connect(
        'secure_storage.db'
    )

    cursor = conn.cursor()

    cursor.execute(
        '''
        DELETE FROM users
        WHERE username=?
        ''',
        (username,)
    )

    conn.commit()
    conn.close()

    # --------------------------------------------------------
    # LOG USER OUT
    # --------------------------------------------------------

    session.pop('user', None)

    # Redirect to signup page after account deletion.
    return redirect(
        url_for('signup')
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route('/logout')
def logout():

    # Remove the user from the session.
    session.pop('user', None)

    return redirect(
        url_for('login')
    )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    # host="0.0.0.0" allows the application to run on Render
    # as well as locally.
    #
    # debug=False is safer for the deployed version.

    app.run(
        host="0.0.0.0",
        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        ),
        debug=False
    )