#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
สคริปต์สำหรับแก้ไขชื่อไฟล์รูปภาพยางในฐานข้อมูล
"""

import mysql.connector
from mysql.connector import Error

def fix_tire_image_names():
    """แก้ไขชื่อไฟล์รูปภาพยางในฐานข้อมูล"""
    
    try:
        # เชื่อมต่อฐานข้อมูล
        connection = mysql.connector.connect(
            host='localhost',
            port=3307,  # ใช้ port 3307 ตามที่กำหนด
            user='root',
            password='',
            database='tire_shop'
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            print("เชื่อมต่อฐานข้อมูลสำเร็จ")
            
            # แก้ไขชื่อไฟล์รูปภาพเก่าที่ไม่ถูกต้อง (ใช้ชื่อเดิม)
            updates = [
                # Michelin AGILIS 3
                ("UPDATE tires SET tire_image_url = 'Michelin_AGILIS_3.png' WHERE tire_image_url = 'Michelin AGILIS 3.png'", 
                 "Michelin AGILIS 3.png -> Michelin_AGILIS_3.png"),
                
                # Michelin ENERGY XM2
                ("UPDATE tires SET tire_image_url = 'Michelin_ENERGY_XM2__EXM2.png' WHERE tire_image_url = 'Michelin ENERGY XM2 +_EXM2+.png'", 
                 "Michelin ENERGY XM2 +_EXM2+.png -> Michelin_ENERGY_XM2__EXM2.png"),
            ]
            
            # ดำเนินการอัปเดต
            for sql, description in updates:
                cursor.execute(sql)
                affected_rows = cursor.rowcount
                print(f"อัปเดต {description}: {affected_rows} แถว")
            
            # Commit การเปลี่ยนแปลง
            connection.commit()
            print("อัปเดตฐานข้อมูลสำเร็จ")
            
            # ตรวจสอบผลลัพธ์
            print("\n=== ตรวจสอบผลลัพธ์ ===")
            
            # ตรวจสอบไฟล์รูปภาพทั้งหมดที่มีปัญหา
            cursor.execute("""
                SELECT tire_id, tire_image_url 
                FROM tires 
                WHERE tire_image_url LIKE '%_%' 
                   OR tire_image_url LIKE '%__%'
                ORDER BY tire_image_url
            """)
            
            problematic_files = cursor.fetchall()
            if problematic_files:
                print(f"พบไฟล์ที่มีปัญหาทั้งหมด {len(problematic_files)} รายการ:")
                for tire_id, filename in problematic_files:
                    print(f"  tire_id: {tire_id}, filename: {filename}")
            else:
                print("ไม่พบไฟล์ที่มีปัญหา")
            
            # ตรวจสอบไฟล์รูปภาพ Michelin ทั้งหมด
            cursor.execute("""
                SELECT tire_id, tire_image_url 
                FROM tires 
                WHERE tire_image_url LIKE '%Michelin%'
                ORDER BY tire_image_url
            """)
            
            michelin_files = cursor.fetchall()
            print(f"\nไฟล์รูปภาพ Michelin ทั้งหมด {len(michelin_files)} รายการ:")
            for tire_id, filename in michelin_files:
                print(f"  tire_id: {tire_id}, filename: {filename}")
            
    except Error as e:
        print(f"เกิดข้อผิดพลาด: {e}")
    
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("\nปิดการเชื่อมต่อฐานข้อมูล")

if __name__ == "__main__":
    print("เริ่มต้นการแก้ไขชื่อไฟล์รูปภาพยาง...")
    fix_tire_image_names()
    print("เสร็จสิ้น")
