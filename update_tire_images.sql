-- อัปเดตชื่อไฟล์รูปภาพในฐานข้อมูล (ใช้ชื่อเดิม)
UPDATE tires 
SET tire_image_url = 'Michelin_AGILIS_3.png' 
WHERE tire_image_url = 'Michelin AGILIS 3.png';

-- อัปเดตชื่อไฟล์รูปภาพเก่าอื่นๆ ที่ไม่ถูกต้อง (ใช้ชื่อเดิม)
UPDATE tires 
SET tire_image_url = 'Michelin_ENERGY_XM2__EXM2.png' 
WHERE tire_image_url = 'Michelin ENERGY XM2 +_EXM2+.png';

-- ตรวจสอบผลลัพธ์
SELECT tire_id, tire_image_url 
FROM tires 
WHERE tire_image_url LIKE '%Michelin%';

-- ตรวจสอบไฟล์รูปภาพทั้งหมดที่มีปัญหา
SELECT tire_id, tire_image_url 
FROM tires 
WHERE tire_image_url LIKE '%_%' 
   OR tire_image_url LIKE '%__%';
