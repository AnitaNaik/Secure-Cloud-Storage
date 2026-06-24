# Secure Cloud Storage System

## Project Overview

Secure Cloud Storage System is a web application developed using Flask and SQLite that allows users to securely upload, store, and download files. The system provides user authentication, encrypted file storage, and user-specific access control.

## Features

* User Registration (Signup)
* User Login and Logout
* Session Management
* Secure File Upload
* Encrypted File Storage using Fernet Encryption
* File Download Functionality
* User-Specific File Access
* Simple and User-Friendly Interface

## Technologies Used

* Python
* Flask
* SQLite
* HTML
* CSS
* Cryptography (Fernet)

## Project Structure

Secure-Cloud-Storage/

├── app.py

├── requirements.txt

├── README.md

├── secure_storage.db

├── templates/

│   ├── home.html

│   ├── signup.html

│   ├── login.html

│   ├── update.html

│   └── files.html

└── uploads/

## Installation

1. Clone the repository.
2. Install dependencies:

pip install -r requirements.txt

3. Run the application:

python app.py

4. Open the browser and visit:

http://127.0.0.1:5000

## Security Features

* User Authentication
* Session-Based Access Control
* Encrypted File Storage
* User-Specific File Isolation

## Future Enhancements

* Password Hashing
* Cloud Deployment (AWS/Render)
* File Sharing Between Users
* Zero-Knowledge Encryption
* Improved User Interface

## Author

Anita Naik
