from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from models import db, User, TokenBlocklist
from datetime import datetime
import re

auth_bp = Blueprint('auth', __name__)

# ─── Validation Helpers ────────────────────────────────────────────────────────

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PHONE_RE = re.compile(r'^(\+91)?[6-9]\d{9}$')
SPECIAL_RE = re.compile(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~/]')


def validate_phone(phone: str):
    """Normalize and validate Indian phone number. Returns (normalized, error_msg)."""
    phone = phone.strip()
    if not phone:
        return None, "Phone number is required"
    if not PHONE_RE.match(phone):
        return None, "Enter a valid Indian mobile number (e.g. 9876543210 or +919876543210)"
    # Store as 10-digit string without prefix
    normalized = phone[-10:]
    return normalized, None


def validate_password_strength(password: str):
    """Returns list of failing rule names or empty list if strong."""
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("one lowercase letter")
    if not re.search(r'\d', password):
        errors.append("one digit")
    if not SPECIAL_RE.search(password):
        errors.append("one special character (!@#$...)")
    return errors


def validate_name(name: str):
    """Returns error string or None."""
    name = name.strip()
    if not name:
        return "Full name is required"
    if len(name) < 3:
        return "Name must be at least 3 characters"
    if len(name) > 50:
        return "Name must be 50 characters or fewer"
    if name.replace(' ', '').isdigit():
        return "Name cannot be purely numeric"
    return None


# ─── Register ─────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user — requires name, either email or phone_number, and strong password."""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    password = data.get('password') or ''
    phone_raw = (data.get('phone_number') or '').strip()

    # Require at least one contact channel
    if not email and not phone_raw:
        return jsonify({"success": False, "message": "Either email address or phone number is required"}), 400

    # Name validation
    name_err = validate_name(name)
    if name_err:
        return jsonify({"success": False, "message": name_err}), 400

    # Email validation (if provided)
    if email:
        if not EMAIL_RE.match(email):
            return jsonify({"success": False, "message": "Enter a valid email address (e.g. you@example.com)"}), 400
        # Check email uniqueness
        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "message": "This email is already registered. Please log in."}), 409

    # Phone validation (if provided)
    phone = None
    if phone_raw:
        phone, phone_err = validate_phone(phone_raw)
        if phone_err:
            return jsonify({"success": False, "message": phone_err}), 400
        # Check phone uniqueness
        if User.query.filter_by(phone_number=phone).first():
            return jsonify({"success": False, "message": "This phone number is already linked to an account."}), 409

    # If email is not provided, generate a unique placeholder email based on phone number
    if not email:
        # Since not email is True, phone_raw must be present, and phone has been validated/normalized
        email = f"{phone}@buysmart.placeholder"
        if User.query.filter_by(email=email).first():
            return jsonify({"success": False, "message": "This phone number is already linked to an account."}), 409

    # Password strength validation
    pw_errors = validate_password_strength(password)
    if pw_errors:
        return jsonify({
            "success": False,
            "message": f"Password must contain: {', '.join(pw_errors)}"
        }), 400

    # Role assignment (first user becomes admin)
    is_first = User.query.first() is None
    role = 'admin' if is_first else 'user'

    user = User(
        email=email,
        name=name,
        phone_number=phone,
        role=role,
        is_admin=(role == 'admin')
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Auto-login: issue tokens immediately after registration
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "success": True,
        "message": "Account created successfully! Welcome to BuySmart.",
        "data": {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    }), 201


# ─── Login ────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with email or phone number + password. Accepts 'identifier' or legacy 'email' field."""
    data = request.get_json() or {}

    # Support both 'identifier' (new) and 'email' (legacy) field
    identifier = (data.get('identifier') or data.get('email') or '').strip()
    password = data.get('password') or ''

    if not identifier:
        return jsonify({"success": False, "message": "Email or phone number is required"}), 400
    if not password:
        return jsonify({"success": False, "message": "Password is required"}), 400

    # Detect if identifier is email or phone
    if '@' in identifier:
        user = User.query.filter_by(email=identifier.lower()).first()
        if not user:
            return jsonify({"success": False, "message": "No account found with this email address"}), 401
    else:
        # Normalize phone
        phone, phone_err = validate_phone(identifier)
        if phone_err:
            return jsonify({"success": False, "message": "Enter a valid email address or phone number"}), 400
        user = User.query.filter_by(phone_number=phone).first()
        if not user:
            return jsonify({"success": False, "message": "No account found with this phone number"}), 401

    if not user.check_password(password):
        return jsonify({"success": False, "message": "Incorrect password. Please try again."}), 401

    if not user.is_active:
        return jsonify({"success": False, "message": "Your account has been disabled. Please contact support."}), 403

    # Update login timestamps
    now = datetime.utcnow()
    user.last_login = now
    user.last_login_at = now
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "success": True,
        "message": f"Welcome back, {user.name.split()[0]}!",
        "data": {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token
        }
    }), 200


# ─── Refresh ──────────────────────────────────────────────────────────────────

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Generate a new access token using a valid refresh token."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    if not user.is_active:
        return jsonify({"success": False, "message": "Account disabled. Please contact support."}), 403

    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        "success": True,
        "message": "Token refreshed successfully",
        "data": {"access_token": access_token}
    }), 200


# ─── Logout ───────────────────────────────────────────────────────────────────

@auth_bp.route('/logout', methods=['POST'])
@jwt_required(optional=True)
def logout():
    """Logout user and revoke both access token and optional refresh token."""
    jwt_data = get_jwt()
    if jwt_data:
        jti = jwt_data["jti"]
        if not TokenBlocklist.query.filter_by(jti=jti).first():
            db.session.add(TokenBlocklist(jti=jti))

    data = request.get_json() or {}
    refresh_token = data.get('refresh_token')
    if refresh_token:
        try:
            from flask_jwt_extended import decode_token
            decoded = decode_token(refresh_token)
            refresh_jti = decoded["jti"]
            if not TokenBlocklist.query.filter_by(jti=refresh_jti).first():
                db.session.add(TokenBlocklist(jti=refresh_jti))
        except Exception:
            pass

    db.session.commit()
    return jsonify({"success": True, "message": "Logged out successfully"}), 200


# ─── Get Current User ─────────────────────────────────────────────────────────

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    """Fetch current user details."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    if not user.is_active:
        return jsonify({"success": False, "message": "Account disabled. Please contact support."}), 403

    return jsonify({
        "success": True,
        "message": "Profile fetched successfully",
        "data": {"user": user.to_dict()}
    }), 200


# ─── Update Profile ───────────────────────────────────────────────────────────

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update name and/or phone_number for the current user."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    data = request.get_json() or {}
    new_name = (data.get('name') or '').strip()
    new_phone_raw = (data.get('phone_number') or '').strip()

    # Validate and update name if provided
    if new_name:
        name_err = validate_name(new_name)
        if name_err:
            return jsonify({"success": False, "message": name_err}), 400
        user.name = new_name

    # Validate and update phone if provided
    if new_phone_raw:
        phone, phone_err = validate_phone(new_phone_raw)
        if phone_err:
            return jsonify({"success": False, "message": phone_err}), 400
        # Check uniqueness (exclude self)
        existing = User.query.filter_by(phone_number=phone).first()
        if existing and existing.id != user.id:
            return jsonify({"success": False, "message": "This phone number is already linked to another account."}), 409
        user.phone_number = phone

    db.session.commit()
    return jsonify({
        "success": True,
        "message": "Profile updated successfully.",
        "data": {"user": user.to_dict()}
    }), 200


# ─── Change Password ──────────────────────────────────────────────────────────

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change password — requires current password verification and strong new password."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    data = request.get_json() or {}
    current_password = data.get('current_password') or ''
    new_password = data.get('new_password') or ''

    if not current_password:
        return jsonify({"success": False, "message": "Current password is required"}), 400
    if not new_password:
        return jsonify({"success": False, "message": "New password is required"}), 400

    if not user.check_password(current_password):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 401

    if current_password == new_password:
        return jsonify({"success": False, "message": "New password must be different from your current password"}), 400

    pw_errors = validate_password_strength(new_password)
    if pw_errors:
        return jsonify({
            "success": False,
            "message": f"New password must contain: {', '.join(pw_errors)}"
        }), 400

    user.set_password(new_password)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Password changed successfully."
    }), 200
