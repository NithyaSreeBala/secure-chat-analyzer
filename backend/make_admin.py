from app import app
from models import db, User

USERNAME = "nithya_selvam"

with app.app_context():

    user = User.query.filter_by(
        username=USERNAME
    ).first()

    if not user:
        print(f"❌ User '{USERNAME}' not found.")

    else:
        user.role = "admin"
        db.session.commit()

        print("✅ Admin role assigned successfully!")
        print(f"Username: {user.username}")
        print(f"Role: {user.role}")