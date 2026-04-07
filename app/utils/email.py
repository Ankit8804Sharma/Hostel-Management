from flask import current_app
from flask_mail import Message
from app import mail

def send_complaint_received(student_email, student_name, complaint_id, complaint_type):
    try:
        msg = Message(
            subject=f"Complaint #{complaint_id} Received",
            recipients=[student_email],
            body=f"Dear {student_name}, your {complaint_type} complaint (ID: {complaint_id}) has been received and is under review."
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send complaint received email: {e}")

def send_complaint_status_update(student_email, student_name, complaint_id, new_status, staff_name):
    try:
        msg = Message(
            subject=f"Complaint #{complaint_id} Status Updated",
            recipients=[student_email],
            body=f"Dear {student_name}, your complaint (ID: {complaint_id}) status has been updated to {new_status} by {staff_name}."
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send complaint status update email: {e}")

def send_task_assigned(staff_email, staff_name, task_description, assigned_by):
    try:
        msg = Message(
            subject="New Task Assigned",
            recipients=[staff_email],
            body=f"Dear {staff_name}, a new task has been assigned to you by {assigned_by}: {task_description}."
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send task assigned email: {e}")

def send_attendance_marked(student_email, student_name, date, status):
    try:
        msg = Message(
            subject=f"Attendance Marked for {date}",
            recipients=[student_email],
            body=f"Dear {student_name}, your attendance for {date} has been marked as {status}."
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f"Failed to send attendance marked email: {e}")
