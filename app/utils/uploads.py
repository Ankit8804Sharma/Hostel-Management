import os
import uuid
from flask import current_app


def allowed_file(filename: str) -> bool:
    """Return True if the file's extension is in ALLOWED_EXTENSIONS."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('ALLOWED_EXTENSIONS', set())


def save_complaint_attachment(file) -> str | None:
    """
    Validate and save an uploaded complaint attachment.
    Returns the saved filename, or None if no valid file was provided.
    """
    if file is None or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None

    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    file.save(os.path.join(upload_folder, unique_name))
    return unique_name
