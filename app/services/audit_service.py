from ..models import AuditLog
from ..database import db

class AuditService:
    @staticmethod
    def log_action(user_id, action, details=None):
        """
        Logs a user action to the database.
        """
        try:
            log = AuditLog(user_id=user_id, action=action, details=details)
            db.session.add(log)
            db.session.commit()
            return True
        except Exception as e:
            # In a real app, you might want to log this to a file so it's not silent
            print(f"Failed to create audit log: {e}")
            return False
