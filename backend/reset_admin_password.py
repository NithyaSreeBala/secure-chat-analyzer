from app import app, bcrypt
from models import db, User

USERNAME = "nithya_selvam"

# Change this to your new password
NEW_PASSWORD = "nithu"

with app.app_context():

    user = User.query.filter_by(
        username=USERNAME
    ).first()

    if not user:
        print(f"❌ User '{USERNAME}' not found.")

    else:
        user.password_hash = bcrypt.generate_password_hash(
            NEW_PASSWORD
        ).decode("utf-8")

        user.role = "admin"

        db.session.commit()

        print("✅ Admin password reset successfully!")
        print(f"Username: {user.username}")
        print(f"Role: {user.role}")