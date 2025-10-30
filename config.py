import os

class Config:
    # Informations de connexion
    DB_HOST = "avo-adb-002.postgres.database.azure.com"
    DB_PORT = 5432
    DB_LOGIN = "administrationSTS"  # ✅ Important : inclure le suffixe
    DB_PASSWORD = "St$%400987"
    DB_DATABASE = "Personnel_skill_matrix"
    SSL_MODE = "require"

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{DB_LOGIN}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}?sslmode={SSL_MODE}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY") or "votre_cle_secrete_tres_tres_securisee"
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "static/qrcodes")
    ALLOW_SELF_SIGNUP = True # RH uniquement crée les comptes
    SECRET_KEY = "change-moi-en-variable-d-environnement"