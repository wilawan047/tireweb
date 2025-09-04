import mysql.connector
from mysql.connector import pooling
from flask import g, current_app
import os
from dotenv import load_dotenv

load_dotenv()

# ตั้งค่า MySQL Connection Pool
# NOTE: ใช้ port 3307 ห้ามแก้กลับเป็น 3306
DB_CONFIG = dict(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 3307)),  # NOTE: ใช้ port 3307 ห้ามแก้กลับเป็น 3306
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    autocommit=False,
    charset='utf8mb4',
    collation='utf8mb4_unicode_ci',
    use_unicode=True
)

try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="tireweb_pool",
        pool_size=10,
        pool_reset_session=True,
        **DB_CONFIG
    )
except Exception as e:
    print(f"Error initializing DB pool: {e}")
    connection_pool = None

def _get_db_connection():
    if connection_pool is None:
        # สร้าง connection แบบตรงถ้า pool ไม่ได้
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            # ตั้งค่า charset เพิ่มเติมสำหรับการเชื่อมต่อแบบตรง
            cursor = connection.cursor()
            cursor.execute("SET NAMES utf8mb4")
            cursor.execute("SET CHARACTER SET utf8mb4")
            cursor.execute("SET character_set_connection=utf8mb4")
            cursor.close()
            return connection
        except Exception as e:
            print(f"Error creating direct connection: {e}")
            raise RuntimeError("Cannot connect to database")
    return connection_pool.get_connection()

def get_db():
    """ดึงการเชื่อมต่อฐานข้อมูลจาก Flask g object"""
    if 'db_conn' not in g:
        try:
            g.db_conn = _get_db_connection()
            # ตั้งค่า charset สำหรับการเชื่อมต่อใหม่
            cursor = g.db_conn.cursor()
            cursor.execute("SET NAMES utf8mb4")
            cursor.execute("SET CHARACTER SET utf8mb4")
            cursor.execute("SET character_set_connection=utf8mb4")
            cursor.close()
        except Exception as e:
            print(f"Error getting database connection: {e}")
            # ลองรีเซ็ต pool และลองใหม่
            try:
                global connection_pool
                if connection_pool:
                    connection_pool.reset_session()
                g.db_conn = _get_db_connection()
                # ตั้งค่า charset สำหรับการเชื่อมต่อใหม่
                cursor = g.db_conn.cursor()
                cursor.execute("SET NAMES utf8mb4")
                cursor.execute("SET CHARACTER SET utf8mb4")
                cursor.execute("SET character_set_connection=utf8mb4")
                cursor.close()
            except Exception as e2:
                print(f"Error after pool reset: {e2}")
                raise
    else:
        try:
            # ตรวจสอบและรีเชื่อมต่ออัตโนมัติเมื่อหลุด
            if hasattr(g.db_conn, 'is_connected') and not g.db_conn.is_connected():
                try:
                    g.db_conn.reconnect(attempts=2, delay=1)
                    # ตั้งค่า charset หลังจาก reconnect
                    cursor = g.db_conn.cursor()
                    cursor.execute("SET NAMES utf8mb4")
                    cursor.execute("SET CHARACTER SET utf8mb4")
                    cursor.execute("SET character_set_connection=utf8mb4")
                    cursor.close()
                except Exception:
                    # ขอ connection ใหม่จาก pool
                    try:
                        g.db_conn.close()
                    except:
                        pass
                    g.db_conn = _get_db_connection()
                    # ตั้งค่า charset สำหรับการเชื่อมต่อใหม่
                    cursor = g.db_conn.cursor()
                    cursor.execute("SET NAMES utf8mb4")
                    cursor.execute("SET CHARACTER SET utf8mb4")
                    cursor.execute("SET character_set_connection=utf8mb4")
                    cursor.close()
        except Exception:
            try:
                g.db_conn = _get_db_connection()
                # ตั้งค่า charset สำหรับการเชื่อมต่อใหม่
                cursor = g.db_conn.cursor()
                cursor.execute("SET NAMES utf8mb4")
                cursor.execute("SET CHARACTER SET utf8mb4")
                cursor.execute("SET character_set_connection=utf8mb4")
                cursor.close()
            except Exception:
                raise
    return g.db_conn

def get_cursor(buffered=True, dictionary=True):
    """สร้าง cursor สำหรับฐานข้อมูล"""
    db = get_db()
    if db:
        return db.cursor(buffered=buffered, dictionary=dictionary)
    return None

def close_db_connection(exc):
    """ปิดการเชื่อมต่อฐานข้อมูล"""
    db = g.pop('db_conn', None)
    if db is not None:
        try:
            db.close()
        except Exception as e:
            print(f"Error closing database connection: {e}")

def ensure_page_views_table():
    """สร้างตาราง page_views ถ้ายังไม่มี"""
    try:
        cursor = get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_views (
                id INT AUTO_INCREMENT PRIMARY KEY,
                page_name VARCHAR(255) NOT NULL,
                user_id INT,
                user_role VARCHAR(50),
                ip_address VARCHAR(45),
                user_agent TEXT,
                device_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_page_name (page_name),
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at)
            )
        """)
        get_db().commit()
        print("ตาราง page_views พร้อมใช้งาน")
    except Exception as e:
        print(f"Error creating page_views table: {e}")

def ensure_password_reset_table():
    """สร้างตาราง password_reset_tokens ถ้ายังไม่มี"""
    try:
        cursor = get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                token VARCHAR(255) NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_token (token),
                INDEX idx_expires_at (expires_at)
            )
        """)
        get_db().commit()
        print("ตาราง password_reset_tokens พร้อมใช้งาน")
    except Exception as e:
        print(f"Error creating password_reset_tokens table: {e}")

def ensure_roles_table():
    """ฟังก์ชันนี้ไม่จำเป็นแล้วเพราะใช้ role_name ในตาราง users แทน"""
    pass

def sync_customers_with_users():
    """ซิงค์ข้อมูลระหว่างตาราง customers และ users ที่มีอยู่แล้ว"""
    try:
        cursor = get_cursor()
        
        # หาลูกค้าที่มีข้อมูลในตาราง customers แต่ไม่มี user_id
        cursor.execute("""
            SELECT c.customer_id, c.first_name, c.last_name, c.email, c.phone, c.gender, c.birthdate
            FROM customers c 
            WHERE c.user_id IS NULL
        """)
        customers_without_user = cursor.fetchall()
        
        for customer in customers_without_user:
            # สร้าง username จาก email หรือชื่อ
            username = customer['email'].split('@')[0] if customer['email'] else f"{customer['first_name']}{customer['customer_id']}"
            
            # ตรวจสอบว่า username ซ้ำหรือไม่
            cursor.execute("SELECT username FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                # ถ้า username ซ้ำ ให้เพิ่มตัวเลขต่อท้าย
                counter = 1
                while True:
                    new_username = f"{username}{counter}"
                    cursor.execute("SELECT username FROM users WHERE username = %s", (new_username,))
                    if not cursor.fetchone():
                        username = new_username
                        break
                    counter += 1
            
            # สร้าง password เริ่มต้น (รหัสผ่านชั่วคราว)
            from werkzeug.security import generate_password_hash
            temp_password = "123456"  # รหัสผ่านเริ่มต้น
            password_hash = generate_password_hash(temp_password, method='scrypt')
            
            # สร้างชื่อเต็ม
            full_name = f"{customer['first_name']} {customer['last_name']}"
            
            # เพิ่มข้อมูลลงตาราง users
            cursor.execute("""
                INSERT INTO users (username, password_hash, name, role_name) 
                VALUES (%s, %s, %s, 'customer')
            """, (username, password_hash, full_name))
            
            user_id = cursor.lastrowid
            
            # อัพเดต user_id ในตาราง customers
            cursor.execute("UPDATE customers SET user_id = %s WHERE customer_id = %s", 
                         (user_id, customer['customer_id']))
            
            print(f"สร้าง user สำหรับลูกค้า: {full_name} (username: {username}, password: {temp_password})")
        
        if customers_without_user:
            get_db().commit()
            print(f"ซิงค์ข้อมูลสำเร็จสำหรับลูกค้า {len(customers_without_user)} คน")
        else:
            print("ไม่มีลูกค้าที่ต้องซิงค์ข้อมูล")
            
        return True
    except Exception as e:
        print(f"Error syncing customers with users: {e}")
        return False

