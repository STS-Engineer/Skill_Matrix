from flask import request
from flask_login import current_user
from models import AuditLog, db

def audit(action, entity_type=None, entity_id=None, details=None):
    """Enregistre une action dans la table audit_logs"""
    log = AuditLog(
        user_id = current_user.id if getattr(current_user, "is_authenticated", False) else None,
        action = action,
        entity_type = entity_type,
        entity_id = str(entity_id) if entity_id is not None else None,
        details = details or {},
        ip_address = request.remote_addr,
        user_agent = request.headers.get("User-Agent")
    )
    db.session.add(log)
