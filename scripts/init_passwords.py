"""Legacy helper: hash any existing plaintext passwords in the students table."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash
from app import app, mysql


def main():
    with app.app_context():
        cur = mysql.connection.cursor()
        cur.execute("SELECT student_id, password FROM students")
        rows = cur.fetchall()
        updated = 0
        for student_id, password in rows:
            if password and not password.startswith(('pbkdf2:', 'scrypt:')):
                cur.execute(
                    "UPDATE students SET password=%s WHERE student_id=%s",
                    (generate_password_hash(password), student_id),
                )
                updated += 1
        mysql.connection.commit()
        cur.close()
        print(f"Updated {updated} password(s).")


if __name__ == '__main__':
    main()
