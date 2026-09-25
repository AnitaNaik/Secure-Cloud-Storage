
import sqlite3
import os


# ============================================================
# SETTINGS
# ============================================================

DATABASE = "secure_storage.db"
UPLOAD_FOLDER = "uploads"


# ============================================================
# DELETE USER
# ============================================================

def delete_user():

    # Ask which username should be deleted
    username = input("Enter the username you want to delete: ").strip()

    if not username:
        print("Username cannot be empty.")
        return

    # --------------------------------------------------------
    # CONNECT TO DATABASE
    # --------------------------------------------------------

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    # --------------------------------------------------------
    # CHECK WHETHER USER EXISTS
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT username
        FROM users
        WHERE username=?
        """,
        (username,)
    )

    user = cursor.fetchone()

    if user is None:

        print("User not found.")

        conn.close()

        return

    print("User found:", username)

    # --------------------------------------------------------
    # FIND USER'S FILE RECORDS
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT filename
        FROM files
        WHERE username=?
        """,
        (username,)
    )

    files = cursor.fetchall()

    print("Number of file records:", len(files))

    # --------------------------------------------------------
    # DELETE PHYSICAL FILES
    # --------------------------------------------------------

    user_folder = os.path.join(
        UPLOAD_FOLDER,
        username
    )

    if os.path.exists(user_folder):

        print("\nDeleting files...")

        for filename in os.listdir(user_folder):

            file_path = os.path.join(
                user_folder,
                filename
            )

            if os.path.isfile(file_path):

                try:

                    os.remove(file_path)

                    print("Deleted:", filename)

                except PermissionError:

                    print(
                        "Permission denied:",
                        file_path
                    )

                    conn.close()

                    return

        # Delete the empty user folder
        try:

            os.rmdir(user_folder)

            print("User folder deleted.")

        except OSError:

            print("User folder could not be removed.")

    else:

        print("User upload folder does not exist.")

    # --------------------------------------------------------
    # DELETE FILE RECORDS
    # --------------------------------------------------------

    cursor.execute(
        """
        DELETE FROM files
        WHERE username=?
        """,
        (username,)
    )

    deleted_files = cursor.rowcount

    print(
        "Deleted file database records:",
        deleted_files
    )

    # --------------------------------------------------------
    # DELETE USER RECORD
    # --------------------------------------------------------

    cursor.execute(
        """
        DELETE FROM users
        WHERE username=?
        """,
        (username,)
    )

    deleted_user = cursor.rowcount

    # --------------------------------------------------------
    # SAVE CHANGES
    # --------------------------------------------------------

    conn.commit()

    conn.close()

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    if deleted_user == 1:

        print("\n================================")
        print("USER DELETED SUCCESSFULLY")
        print("================================")
        print("Username:", username)
        print("User database record: Deleted")
        print("File database records:", deleted_files)
        print("Physical uploaded files: Deleted")

    else:

        print("\nUser could not be deleted.")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    delete_user()

