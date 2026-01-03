# utils/helpers.py
from functools import wraps
from flask import request, jsonify, g
from config import Config
from models import User


# =====================================================
# TOKEN REQUIRED DECORATOR
# =====================================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            try:
                auth_header = request.headers['Authorization']
                token = auth_header.split(' ')[1]
            except Exception:
                return jsonify({'message': 'Invalid authorization header format!'}), 401

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            user = User.verify_auth_token(token, Config.JWT_SECRET_KEY)
            if not user:
                return jsonify({'message': 'Invalid token!'}), 401
            g.current_user = user
        except Exception as e:
            return jsonify({'message': str(e)}), 401

        return f(*args, **kwargs)

    return decorated


# =====================================================
# ADMIN REQUIRED DECORATOR
# =====================================================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'current_user'):
            return jsonify({'message': 'Authentication required!'}), 401

        if not g.current_user.is_admin:
            return jsonify({'message': 'Admin access required!'}), 403

        return f(*args, **kwargs)

    return decorated
