import os
from datetime import timedelta

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or '4eceea41f6118226ad54747b6cbbfa54ae0be9a35f21369726beb4cb424844cf'
    
    # Database Configuration
    # NOTE: ใช้ port 3307 ห้ามแก้กลับเป็น 3306
    DB_HOST = os.environ.get('DB_HOST') or 'localhost'
    DB_PORT = int(os.environ.get('DB_PORT') or 3307)  # NOTE: ใช้ port 3307 ห้ามแก้กลับเป็น 3306
    DB_USER = os.environ.get('DB_USER') or 'root'
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or ''
    DB_NAME = os.environ.get('DB_NAME') or 'tire_shop'
    
    # File Upload Configuration
    UPLOAD_FOLDER = 'static/uploads'
    PROFILE_UPLOAD_FOLDER = 'static/uploads/profile'
    TIRE_UPLOAD_FOLDER = 'static/uploads/tires'
    PROMOTION_UPLOAD_FOLDER = 'static/uploads/promotions'
    SLIDER_UPLOAD_FOLDER = 'static/uploads/home_slider'
    LOGO_UPLOAD_FOLDER = 'static/uploads/logos'
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Pagination
    DEFAULT_PER_PAGE = 10
    MAX_PER_PAGE = 100













