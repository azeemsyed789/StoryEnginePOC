from database import SessionLocal, Base, engine
from models import User
from auth_utils import hash_password

db = SessionLocal()

# ADMIN user
admin = User(
    email="admin@test.com",
    password_hash="admin123",  # store plain password temporarily
    role="admin"
)

# NORMAL user
user = User(
    email="user@test.com",
    password_hash="user123",  # store plain password temporarily
    role="user"
)

db.add(admin)
db.add(user)
db.commit()
db.close()

print("Test users created successfully")
