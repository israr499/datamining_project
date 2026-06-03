

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from database import (
    create_user,
    authenticate_user,
    update_last_login,
    get_user_by_id,
    email_exists,
    username_exists
)
from email_utils import generate_otp, send_otp_email, is_valid_email
import secrets
from datetime import datetime, timedelta


auth_bp = Blueprint("auth", __name__)



def generate_session_token():
    return secrets.token_urlsafe(32)


def is_logged_in():
    return "user_id" in session


def get_current_user():
    if is_logged_in():
        return get_user_by_id(session["user_id"])
    return None


def login_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for("auth.login_page"))
        return view_func(*args, **kwargs)

    return wrapper


def is_otp_expired(created_at_string, minutes=5):
    try:
        created_at = datetime.fromisoformat(created_at_string)
        return datetime.now() > created_at + timedelta(minutes=minutes)
    except Exception:
        return True


# ============================================
# LOGIN ROUTES
# ============================================

@auth_bp.route("/login")
def login_page():
    if is_logged_in():
        return redirect(url_for("index"))
    return render_template("login.html")


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    try:
        data = request.get_json()

        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return jsonify({
                "success": False,
                "message": "Username and password required"
            }), 400

        result = authenticate_user(username, password)

        if result["success"]:
            session.clear()

            session["user_id"] = result["user_id"]
            session["username"] = result["username"]
            session["full_name"] = result.get("full_name", result["username"])

            update_last_login(result["user_id"])

            return jsonify({
                "success": True,
                "message": "Login successful",
                "redirect": url_for("index"),
                "user": {
                    "username": result["username"],
                    "email": result["email"],
                    "full_name": result.get("full_name")
                }
            })

        return jsonify({
            "success": False,
            "message": result.get("message", "Login failed")
        }), 401

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500



@auth_bp.route("/signup")
def signup_page():
    if is_logged_in():
        return redirect(url_for("index"))
    return render_template("signup.html")


@auth_bp.route("/api/signup", methods=["POST"])
def api_signup():
    try:
        data = request.get_json()

        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        full_name = data.get("full_name", "").strip()

        if not username or not email or not password:
            return jsonify({
                "success": False,
                "message": "Username, email, and password are required."
            }), 400

        if len(username) < 3:
            return jsonify({
                "success": False,
                "message": "Username must be at least 3 characters."
            }), 400

        if not is_valid_email(email):
            return jsonify({
                "success": False,
                "message": "Please enter a valid email address."
            }), 400

        if len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Password must be at least 6 characters."
            }), 400

        if username_exists(username):
            return jsonify({
                "success": False,
                "message": "Username already exists."
            }), 400

        if email_exists(email):
            return jsonify({
                "success": False,
                "message": "Email already exists."
            }), 400

        otp_code = generate_otp()
        email_result = send_otp_email(email, otp_code)

        if not email_result["success"]:
            return jsonify({
                "success": False,
                "message": email_result["message"]
            }), 500

        session["pending_signup"] = {
            "username": username,
            "email": email,
            "password": password,
            "full_name": full_name,
            "otp": otp_code,
            "otp_created_at": datetime.now().isoformat()
        }

        return jsonify({
            "success": True,
            "message": "OTP sent successfully. Please verify your email.",
            "redirect": url_for("auth.verify_otp_page")
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================
# OTP VERIFICATION ROUTES
# ============================================

@auth_bp.route("/verify-otp")
def verify_otp_page():
    if is_logged_in():
        return redirect(url_for("index"))

    pending_signup = session.get("pending_signup")

    if not pending_signup:
        return redirect(url_for("auth.signup_page"))

    return render_template(
        "verify_otp.html",
        email=pending_signup.get("email", "")
    )


@auth_bp.route("/api/verify-otp", methods=["POST"])
def api_verify_otp():
    try:
        pending_signup = session.get("pending_signup")

        if not pending_signup:
            return jsonify({
                "success": False,
                "message": "No pending signup found. Please sign up again.",
                "redirect": url_for("auth.signup_page")
            }), 400

        data = request.get_json()
        entered_otp = data.get("otp", "").strip()

        if not entered_otp:
            return jsonify({
                "success": False,
                "message": "Please enter OTP."
            }), 400

        if is_otp_expired(pending_signup.get("otp_created_at")):
            return jsonify({
                "success": False,
                "message": "OTP expired. Please resend OTP."
            }), 400

        if entered_otp != pending_signup.get("otp"):
            return jsonify({
                "success": False,
                "message": "Invalid OTP. Please try again."
            }), 400

        username = pending_signup["username"]
        email = pending_signup["email"]
        password = pending_signup["password"]
        full_name = pending_signup.get("full_name")

        if username_exists(username):
            session.pop("pending_signup", None)
            return jsonify({
                "success": False,
                "message": "Username already exists. Please sign up again.",
                "redirect": url_for("auth.signup_page")
            }), 400

        if email_exists(email):
            session.pop("pending_signup", None)
            return jsonify({
                "success": False,
                "message": "Email already exists. Please sign up again.",
                "redirect": url_for("auth.signup_page")
            }), 400

        result = create_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            email_verified=1
        )

        if not result["success"]:
            return jsonify({
                "success": False,
                "message": result["message"]
            }), 400

        auth_result = authenticate_user(username, password)

        if auth_result["success"]:
            session.clear()

            session["user_id"] = auth_result["user_id"]
            session["username"] = auth_result["username"]
            session["full_name"] = auth_result.get("full_name", auth_result["username"])

            update_last_login(auth_result["user_id"])

            return jsonify({
                "success": True,
                "message": "Email verified successfully. Account created.",
                "redirect": url_for("index")
            })

        return jsonify({
            "success": True,
            "message": "Email verified successfully. Please login.",
            "redirect": url_for("auth.login_page")
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@auth_bp.route("/api/resend-otp", methods=["POST"])
def api_resend_otp():
    try:
        pending_signup = session.get("pending_signup")

        if not pending_signup:
            return jsonify({
                "success": False,
                "message": "No pending signup found. Please sign up again.",
                "redirect": url_for("auth.signup_page")
            }), 400

        email = pending_signup.get("email")

        otp_code = generate_otp()
        email_result = send_otp_email(email, otp_code)

        if not email_result["success"]:
            return jsonify({
                "success": False,
                "message": email_result["message"]
            }), 500

        pending_signup["otp"] = otp_code
        pending_signup["otp_created_at"] = datetime.now().isoformat()
        session["pending_signup"] = pending_signup

        return jsonify({
            "success": True,
            "message": "New OTP sent successfully."
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ============================================
# LOGOUT
# ============================================

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))


# ============================================
# PROFILE ROUTES
# ============================================

@auth_bp.route("/profile")
@login_required
def profile_page():
    user = get_current_user()
    return render_template("profile.html", user=user)


@auth_bp.route("/api/profile", methods=["GET"])
@login_required
def api_get_profile():
    user = get_current_user()

    if user:
        return jsonify({
            "success": True,
            "user": {
                "username": user["username"],
                "email": user["email"],
                "full_name": user.get("full_name"),
                "email_verified": user.get("email_verified"),
                "member_since": user.get("created_at"),
                "last_login": user.get("last_login")
            }
        })

    return jsonify({
        "success": False,
        "message": "User not found"
    }), 404