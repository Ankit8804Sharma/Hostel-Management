from functools import wraps
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, get_jwt_identity, jwt_required, get_jwt
)
from app import db
from app.models import Student, StaffMember, Complaint

api_bp = Blueprint('api', __name__)

def require_warden():
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            claims = get_jwt()
            if claims.get('role') not in ('warden', 'chief_warden'):
                return jsonify({"error": "Warden access required"}), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

@api_bp.route('/auth/login/student', methods=['POST'])
def login_student():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
        
    student = Student.query.filter_by(email=email).first()
    if not student or not student.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
        
    access_token = create_access_token(
        identity=f"student_{student.student_id}",
        additional_claims={"role": "student"}
    )
    return jsonify({
        "access_token": access_token,
        "student_id": student.student_id,
        "name": student.name
    }), 200

@api_bp.route('/auth/login/staff', methods=['POST'])
def login_staff():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400
        
    staff = StaffMember.query.filter_by(email=email).first()
    if not staff or not staff.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401
        
    access_token = create_access_token(
        identity=f"staff_{staff.staff_id}",
        additional_claims={"role": staff.role}
    )
    return jsonify({
        "access_token": access_token,
        "staff_id": staff.staff_id,
        "name": staff.name,
        "role": staff.role
    }), 200

@api_bp.route('/student/complaints', methods=['GET', 'POST'])
@jwt_required()
def student_complaints():
    identity = get_jwt_identity()
    if not identity.startswith('student_'):
        return jsonify({"error": "Student access required"}), 403
    student_id = int(identity.split('_')[1])
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    if request.method == 'GET':
        complaints = Complaint.query.filter_by(student_id=student.student_id).all()
        return jsonify([
            {
                "id": c.complaint_id,
                "type": c.type,
                "status": c.status,
                "created_at": c.issue_date.isoformat(),
                "description": c.description
            } for c in complaints
        ]), 200

    if request.method == 'POST':
        data = request.get_json() or {}
        c_type = data.get('complaint_type', '').strip()
        desc = data.get('description', '').strip()
        if not c_type or not desc:
            return jsonify({"error": "complaint_type and description required"}), 400
        
        from datetime import date
        row = Complaint(
            type=c_type,
            description=desc,
            status='Open',
            issue_date=date.today(),
            student_id=student.student_id
        )
        db.session.add(row)
        db.session.commit()
        return jsonify({"id": row.complaint_id, "message": "Complaint submitted"}), 201

@api_bp.route('/student/profile', methods=['GET'])
@jwt_required()
def student_profile():
    identity = get_jwt_identity()
    if not identity.startswith('student_'):
        return jsonify({"error": "Student access required"}), 403
    student_id = int(identity.split('_')[1])
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"error": "Student not found"}), 404

    from app.models import RoomAllocation
    alloc = RoomAllocation.query.filter_by(student_id=student.student_id, vacate_date=None).first()
    
    return jsonify({
        "name": student.name,
        "email": student.email,
        "roll_no": student.roll_number or "",
        "room": alloc.room.room_number if alloc else "",
        "hostel": alloc.room.hostel.name if alloc else ""
    }), 200

@api_bp.route('/warden/complaints', methods=['GET'])
@require_warden()
def warden_complaints():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '').strip()
    
    query = Complaint.query
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    pagination = query.order_by(Complaint.issue_date.desc()).paginate(page=page, per_page=20, error_out=False)
    
    return jsonify({
        "complaints": [
            {
                "id": c.complaint_id,
                "type": c.type,
                "status": c.status,
                "created_at": c.issue_date.isoformat(),
                "description": c.description,
                "student_id": c.student_id
            } for c in pagination.items
        ],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    }), 200

@api_bp.route('/warden/complaints/<int:id>/status', methods=['PATCH'])
@require_warden()
def update_complaint_status(id):
    complaint = db.session.get(Complaint, id)
    if not complaint:
        return jsonify({"error": "Complaint not found"}), 404
        
    data = request.get_json() or {}
    new_status = data.get('status', '').strip()
    if not new_status:
        return jsonify({"error": "status required"}), 400
        
    complaint.status = new_status
    db.session.commit()
    return jsonify({"message": "Updated"}), 200
