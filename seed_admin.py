
from app import app, db, User
from getpass import getpass

with app.app_context():
    username = input("Créer un admin - utilisateur: ").strip()
    email = input("Email (optionnel): ").strip() or None
    password = getpass("Mot de passe: ").strip()
    if User.query.filter_by(username=username).first():
        print("Cet utilisateur existe déjà.")
    else:
        u = User(username=username, email=email, role="admin")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        print("Administrateur créé ✅")
