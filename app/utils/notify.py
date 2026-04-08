from app import db
from app.models import Notification


def notify_student(student_id: int, message: str) -> None:
    """Create and commit a notification for a student."""
    try:
        notif = Notification(user_type='student', user_id=student_id, message=message)
        db.session.add(notif)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # In a real app we'd use current_app.logger.error(e). We just suppress it here.
        pass


def notify_staff(staff_id: int, message: str) -> None:
    """Create and commit a notification for a staff member."""
    try:
        notif = Notification(user_type='staff', user_id=staff_id, message=message)
        db.session.add(notif)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        pass
