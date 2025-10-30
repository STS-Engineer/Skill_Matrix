
# Auth ajoutée (Flask-Login)

Ce patch ajoute un système de comptes (login) simple avec rôles (`admin`, `user`).
Par défaut, toutes les pages (sauf la page publique de l'employé) sont protégées.

## Installation

1. Installe les dépendances :

```bash
pip install -r requirements.txt
```

2. Applique les migrations pour créer la table `users` (si tu utilises Flask-Migrate déjà présent) :

```bash
flask db migrate -m "add users table"
flask db upgrade
```

> Si tu n'utilises pas encore les migrations, tu peux créer la table automatiquement au premier run via `db.create_all()` en Python, mais **recommandé**: utiliser Flask-Migrate.

3. Crée le premier admin :

```bash
python seed_admin.py
```

4. Lance l'app :

```bash
python app.py
```

## Notes

- La route publique reste: `/employee/<id>/public` (pas de login requis).
- Pour restreindre certaines actions aux seuls admins, tu peux vérifier `current_user.role == "admin"` dans les routes concernées et sinon retourner un `403`.
- Pense à mettre les secrets (BD, SECRET_KEY) dans des variables d'environnement en production.
