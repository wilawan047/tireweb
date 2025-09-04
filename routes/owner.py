from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, current_app, jsonify, send_file
from database import get_cursor, get_db
from decorators import owner_login_required
import os
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime

owner = Blueprint('owner', __name__, url_prefix='/owner')

@owner.route('/')
@owner.route('/dashboard')
@owner_login_required
def dashboard():
    """หน้าแดชบอร์ดเจ้าของกิจการ"""
    try:
        cursor = get_cursor()
        
        # สถิติสรุป
        cursor.execute('SELECT COUNT(*) as total FROM customers')
        total_customers = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as total FROM bookings')
        total_bookings = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as total FROM tires')
        total_tires = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as total FROM page_views')
        total_page_views = cursor.fetchone()['total']
        
        # ดึงข้อมูลสถานะการจองสำหรับ chart
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM bookings
            GROUP BY status
            ORDER BY count DESC
        ''')
        booking_status = cursor.fetchall()
        
        return render_template('owner/dashboard.html',
                             total_customers=total_customers,
                             total_bookings=total_bookings,
                             total_tires=total_tires,
                             total_revenue=0,  # ไม่มีข้อมูล revenue ในขณะนี้
                             total_page_views=total_page_views,
                             booking_status=booking_status)
    except Exception as e:
        print(f"Error in owner_dashboard: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('auth.login'))

@owner.route('/bookings_report')
@owner_login_required
def bookings_report():
    """หน้ารายงานการจองสำหรับเจ้าของกิจการ"""
    try:
        cursor = get_cursor()
        
        # สถิติสรุป
        cursor.execute('SELECT COUNT(*) as total FROM bookings')
        total_bookings = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(*) as pending FROM bookings WHERE status = "รอดำเนินการ"')
        pending_bookings = cursor.fetchone()['pending']
        
        cursor.execute('SELECT COUNT(*) as completed FROM bookings WHERE status = "สำเร็จ"')
        completed_bookings = cursor.fetchone()['completed']
        
        cursor.execute('SELECT COUNT(*) as cancelled FROM bookings WHERE status = "ยกเลิก"')
        cancelled_bookings = cursor.fetchone()['cancelled']
        
        # ดึงข้อมูลการจองรายเดือน (6 เดือนล่าสุด)
        cursor.execute('''
            SELECT DATE_FORMAT(booking_date, '%Y-%m') as month, COUNT(*) as count
            FROM bookings
            WHERE booking_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(booking_date, '%Y-%m')
            ORDER BY month DESC
        ''')
        monthly_bookings = cursor.fetchall()
        
        # ดึงข้อมูลการจองทั้งหมด
        cursor.execute('''
            SELECT b.*, 
                   c.first_name, c.last_name, c.phone,
                   v.brand_name, v.model_name, v.license_plate
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
            ORDER BY b.booking_date DESC
        ''')
        bookings = cursor.fetchall()
        
        return render_template('owner/bookings_report.html', 
                             bookings=bookings,
                             total_bookings=total_bookings,
                             pending_bookings=pending_bookings,
                             completed_bookings=completed_bookings,
                             cancelled_bookings=cancelled_bookings,
                             monthly_bookings=monthly_bookings)
        
    except Exception as e:
        print(f"Error in bookings_report: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดรายงาน', 'error')
        return redirect(url_for('owner.dashboard'))


@owner.route('/bookings_report_pdf')
@owner_login_required
def bookings_report_pdf():
    """หน้ารายงานการจอง PDF สำหรับเจ้าของกิจการ"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        cursor = get_cursor()
        
        # ดึงข้อมูลการจองตามช่วงวันที่
        query = '''
            SELECT b.*, 
                   c.first_name, c.last_name, c.phone,
                   v.brand_name, v.model_name, v.license_plate
            FROM bookings b
            JOIN customers c ON b.customer_id = c.customer_id
            JOIN vehicles v ON b.vehicle_id = v.vehicle_id
        '''
        params = []
        
        if start_date and end_date:
            query += ' WHERE DATE(b.booking_date) BETWEEN %s AND %s'
            params.extend([start_date, end_date])
        
        query += ' ORDER BY b.booking_date DESC'
        cursor.execute(query, params)
        bookings = cursor.fetchall()
        
        # แปลงข้อมูลให้เป็น JSON serializable
        bookings_data = []
        for booking in bookings:
            booking_dict = {
                'booking_id': booking['booking_id'],
                'booking_date': booking['booking_date'].strftime('%Y-%m-%d') if booking['booking_date'] else None,
                'service_date': booking['service_date'].strftime('%Y-%m-%d') if booking['service_date'] else None,
                'service_time': str(booking['service_time']) if booking['service_time'] else None,
                'status': booking['status'],
                'first_name': booking['first_name'],
                'last_name': booking['last_name'],
                'phone': booking['phone'],
                'brand_name': booking['brand_name'],
                'model_name': booking['model_name'],
                'license_plate': booking['license_plate']
            }
            bookings_data.append(booking_dict)
        
        # สร้าง PDF ด้วย ReportLab
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import io
        import os
        
        # สร้าง buffer สำหรับ PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0, topMargin=0, rightMargin=0, bottomMargin=0)
        elements = []
        
        # ลงทะเบียนฟอนต์ภาษาไทย
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'Noto_Sans_Thai', 'static', 'NotoSansThai-Regular.ttf')
        pdfmetrics.registerFont(TTFont('NotoSansThai', font_path))
        
        # สร้างสไตล์
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='NotoSansThai',
            fontSize=18,
            spaceAfter=30,
            alignment=1  # center
        )
        
        # สร้างสไตล์สำหรับข้อความปกติ
        normal_style = ParagraphStyle(
            'ThaiNormal',
            parent=styles['Normal'],
            fontName='NotoSansThai',
            fontSize=12
        )
        
        # เพิ่มโลโก้และชื่อร้านที่มุมซ้ายบนสุด
        from reportlab.platypus import Image
        from reportlab.platypus import Table, TableStyle
        
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'logos', 'saengjaroen.jpg')
        if os.path.exists(logo_path):
            # สร้างโลโก้และชื่อร้านในตารางเดียวกัน
            logo = Image(logo_path, width=0.5*inch, height=0.5*inch)
            logo.hAlign = 'LEFT'
            logo.vAlign = 'MIDDLE'
            
            # สร้างสไตล์สำหรับชื่อร้าน
            shop_name_style = ParagraphStyle(
                'ShopName',
                parent=styles['Normal'],
                fontName='NotoSansThai',
                fontSize=10,
                alignment=0,  # left
                leftIndent=0,
                rightIndent=0,
                firstLineIndent=0,
                spaceBefore=0,
                spaceAfter=0
            )
            shop_name = Paragraph("TYREPLUS BSG", shop_name_style)
            
            # สร้างตารางที่มีโลโก้และชื่อร้าน
            header_table = Table([[logo, shop_name]], colWidths=[0.5*inch, 2*inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # โลโก้ชิดซ้าย
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),  # ชื่อร้านชิดซ้าย
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # จัดกึ่งกลางแนวตั้ง
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            header_table.hAlign = 'LEFT'  # จัดตารางให้ชิดซ้าย
            
            elements.append(header_table)
            elements.append(Spacer(1, 8))
        
        # หัวข้อรายงาน
        title = Paragraph("รายงานการจองบริการ", title_style)
        title.leftIndent = 20
        elements.append(title)
        
        # ข้อมูลช่วงวันที่
        if start_date and end_date:
            date_info = Paragraph(f"ช่วงวันที่: {start_date} ถึง {end_date}", normal_style)
            date_info.leftIndent = 20
            elements.append(date_info)
            elements.append(Spacer(1, 32))
        
        # สร้างตารางข้อมูล
        if bookings_data:
            # หัวตาราง
            table_data = [
                ['ลำดับ', 'ลูกค้า', 'รถยนต์', 'วันที่จอง', 'สถานะ']
            ]
            
            # ข้อมูลในตาราง
            for i, booking in enumerate(bookings_data, 1):
                customer_name = f"{booking['first_name']} {booking['last_name']}"
                vehicle_info = f"{booking['brand_name']} {booking['model_name']}"
                booking_date = booking['booking_date'] or '-'
                status = booking['status']
                
                table_data.append([
                    str(i),
                    customer_name,
                    vehicle_info,
                    booking_date,
                    status
                ])
            
            # สร้างตาราง
            table = Table(table_data, colWidths=[0.5*inch, 1.5*inch, 1.5*inch, 1*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 1), (-1, -1), 'NotoSansThai'),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),  # เพิ่ม padding ซ้าย
            ]))
            
            elements.append(table)
        else:
            no_data = Paragraph("ไม่พบข้อมูลการจองในช่วงวันที่ที่เลือก", normal_style)
            no_data.leftIndent = 20
            elements.append(no_data)
        
        # สร้าง PDF
        doc.build(elements)
        buffer.seek(0)
        
        # ส่งกลับไฟล์ PDF
        from flask import send_file
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'booking_report_{start_date}_to_{end_date}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error in bookings_report_pdf: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@owner.route('/page_views_report_pdf')
@owner_login_required
def page_views_report_pdf():
    """หน้ารายงานสถิติการเข้าชม PDF สำหรับเจ้าของกิจการ"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        cursor = get_cursor()
        
        # ดึงข้อมูลสถิติการเข้าชมตามช่วงวันที่
        query = '''
            SELECT page_id, COUNT(*) as total_visits
            FROM page_view_logs
        '''
        params = []
        
        if start_date and end_date:
            query += ' WHERE DATE(viewed_at) BETWEEN %s AND %s'
            params.extend([start_date, end_date])
        
        query += ' GROUP BY page_id ORDER BY total_visits DESC'
        cursor.execute(query, params)
        page_views = cursor.fetchall()
        
        # ดึงข้อมูลสถิติตามอุปกรณ์
        device_query = '''
            SELECT 
                CASE 
                    WHEN device_type IS NULL OR device_type = '' THEN 'unknown'
                    ELSE device_type 
                END as device_type, 
                COUNT(*) as count
            FROM page_view_logs
        '''
        device_params = []
        
        if start_date and end_date:
            device_query += ' WHERE DATE(viewed_at) BETWEEN %s AND %s'
            device_params.extend([start_date, end_date])
        
        device_query += ' GROUP BY CASE WHEN device_type IS NULL OR device_type = "" THEN "unknown" ELSE device_type END ORDER BY count DESC'
        cursor.execute(device_query, device_params)
        device_stats = cursor.fetchall()
        
        # ดึงข้อมูลการเข้าชมรายวัน
        daily_query = '''
            SELECT DATE(viewed_at) as date, COUNT(*) as count
            FROM page_view_logs
        '''
        daily_params = []
        
        if start_date and end_date:
            daily_query += ' WHERE DATE(viewed_at) BETWEEN %s AND %s'
            daily_params.extend([start_date, end_date])
        else:
            daily_query += ' WHERE viewed_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)'
        
        daily_query += ' GROUP BY DATE(viewed_at) ORDER BY date ASC'
        cursor.execute(daily_query, daily_params)
        daily_visits = cursor.fetchall()
        
        # สร้างไฟล์ PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0, topMargin=0, rightMargin=0, bottomMargin=0)
        elements = []
        
        # ลงทะเบียน font ภาษาไทย
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fonts', 'Noto_Sans_Thai', 'NotoSansThai-VariableFont_wdth,wght.ttf')
        pdfmetrics.registerFont(TTFont('NotoSansThai', font_path))
        
        # สร้าง styles ด้วย font ภาษาไทย
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='NotoSansThai',
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # center
            leading=22
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName='NotoSansThai',
            fontSize=14,
            spaceAfter=12,
            leading=16
        )
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='NotoSansThai',
            fontSize=12,
            leading=14
        )
        
        # เพิ่มโลโก้และชื่อร้านที่มุมซ้ายบนสุด
        from reportlab.platypus import Image
        from reportlab.platypus import Table, TableStyle
        
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads', 'logos', 'saengjaroen.jpg')
        if os.path.exists(logo_path):
            # สร้างโลโก้และชื่อร้านในตารางเดียวกัน
            logo = Image(logo_path, width=0.5*inch, height=0.5*inch)
            logo.hAlign = 'LEFT'
            logo.vAlign = 'MIDDLE'
            
            # สร้างสไตล์สำหรับชื่อร้าน
            shop_name_style = ParagraphStyle(
                'ShopName',
                parent=styles['Normal'],
                fontName='NotoSansThai',
                fontSize=10,
                alignment=0,  # left
                leftIndent=0,
                rightIndent=0,
                firstLineIndent=0,
                spaceBefore=0,
                spaceAfter=0
            )
            shop_name = Paragraph("TYREPLUS BSG", shop_name_style)
            
            # สร้างตารางที่มีโลโก้และชื่อร้าน
            header_table = Table([[logo, shop_name]], colWidths=[0.5*inch, 2*inch])
            header_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # โลโก้ชิดซ้าย
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),  # ชื่อร้านชิดซ้าย
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # จัดกึ่งกลางแนวตั้ง
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            header_table.hAlign = 'LEFT'  # จัดตารางให้ชิดซ้าย
            
            elements.append(header_table)
            elements.append(Spacer(1, 8))
        
        # หัวเรื่อง
        title = Paragraph("รายงานสถิติการเข้าชมหน้าเว็บ", title_style)
        title.leftIndent = 20
        elements.append(title)
        
        # ข้อมูลช่วงวันที่
        if start_date and end_date:
            date_info = Paragraph(f"ช่วงวันที่: {start_date} ถึง {end_date}", normal_style)
            date_info.leftIndent = 20
            elements.append(date_info)
            elements.append(Spacer(1, 20))
        
        # สร้างตารางข้อมูลหน้าเว็บ
        if page_views:
            # หัวเรื่อง
            page_views_title = Paragraph("หน้าที่เข้าชมมากที่สุด", heading_style)
            elements.append(page_views_title)
            elements.append(Spacer(1, 12))
            
            # หัวตาราง
            table_data = [['หน้าเว็บ', 'จำนวนการเข้าชม']]
            
            # ข้อมูลในตาราง
            for page in page_views:
                page_name = page['page_id']
                # แปลงชื่อหน้าให้อ่านง่าย
                if page_name == 'customer/home.html':
                    page_name = 'หน้าหลัก'
                elif page_name == 'customer/contact.html':
                    page_name = 'หน้าติดต่อ'
                elif page_name == 'customer/guide.html':
                    page_name = 'หน้าคู่มือ'
                elif page_name == 'customer/promotions.html':
                    page_name = 'หน้าโปรโมชั่น'
                elif page_name == 'customer/tires_michelin.html':
                    page_name = 'หน้ายาง Michelin'
                elif page_name == 'customer/tires_maxxis.html':
                    page_name = 'หน้ายาง Maxxis'
                elif page_name == 'customer/tires_bfgoodrich.html':
                    page_name = 'หน้ายาง BFGoodrich'
                elif page_name == 'customer/recommend.html':
                    page_name = 'หน้าแนะนำยาง'
                elif page_name == 'customer/compare.html':
                    page_name = 'หน้าเปรียบเทียบยาง'
                elif page_name == 'customer/profile.html':
                    page_name = 'หน้าโปรไฟล์ลูกค้า'
                elif page_name == 'customer/bookings.html':
                    page_name = 'หน้าการจอง'
                elif page_name == 'customer/booking-history.html':
                    page_name = 'หน้าประวัติการจอง'
                elif page_name == 'login.html':
                    page_name = 'หน้าเข้าสู่ระบบ'
                elif page_name == 'register.html':
                    page_name = 'หน้าลงทะเบียน'
                
                table_data.append([page_name, str(page['total_visits'])])
            
            # สร้างตาราง
            table = Table(table_data, colWidths=[4*inch, 2*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),  # ตัวเลขชิดขวา
                ('FONTNAME', (0, 1), (-1, -1), 'NotoSansThai'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),  # เพิ่ม padding ซ้าย
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        else:
            # ถ้าไม่มีข้อมูล
            no_data = Paragraph("ไม่พบข้อมูลการเข้าชมในช่วงวันที่ที่เลือก", normal_style)
            no_data.leftIndent = 20
            elements.append(no_data)
        
        # สร้างตารางข้อมูลอุปกรณ์
        if device_stats:
            device_title = Paragraph("อุปกรณ์ที่ใช้เข้าชม", heading_style)
            elements.append(device_title)
            elements.append(Spacer(1, 12))
            
            device_table_data = [['อุปกรณ์', 'จำนวนการเข้าชม']]
            
            for device in device_stats:
                device_name = device['device_type']
                if device_name == 'mobile':
                    device_name = 'มือถือ'
                elif device_name == 'desktop':
                    device_name = 'เดสก์ท็อป'
                elif device_name == 'tablet':
                    device_name = 'แท็บเล็ต'
                elif device_name == 'unknown':
                    device_name = 'อื่นๆ'
                
                device_table_data.append([device_name, str(device['count'])])
            
            device_table = Table(device_table_data, colWidths=[3*inch, 3*inch])
            device_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'NotoSansThai'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            
            elements.append(device_table)
            elements.append(Spacer(1, 20))
        
        # สร้างตารางข้อมูลการเข้าชมรายวัน
        if daily_visits:
            daily_title = Paragraph("การเข้าชมรายวัน", heading_style)
            elements.append(daily_title)
            elements.append(Spacer(1, 12))
            
            daily_table_data = [['วันที่', 'จำนวนการเข้าชม']]
            
            for daily in daily_visits:
                date_str = daily['date'].strftime('%d/%m/%Y') if hasattr(daily['date'], 'strftime') else str(daily['date'])
                daily_table_data.append([date_str, str(daily['count'])])
            
            daily_table = Table(daily_table_data, colWidths=[3*inch, 3*inch])
            daily_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'NotoSansThai'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'NotoSansThai'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
            ]))
            
            elements.append(daily_table)
            elements.append(Spacer(1, 20))
        
        elements.append(Spacer(1, 20))
        
        # ข้อมูลเพิ่มเติม
        info_text = Paragraph(f"รายงานนี้ถูกสร้างเมื่อ: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_style)
        elements.append(info_text)
        
        # สร้าง PDF
        doc.build(elements)
        buffer.seek(0)
        
        # ส่งไฟล์ PDF กลับไป
        filename = f"page_views_report_{start_date}_to_{end_date}.pdf" if start_date and end_date else "page_views_report.pdf"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"Error in page_views_report_pdf: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@owner.route('/page_views_report')
@owner_login_required
def page_views_report():
    """หน้ารายงานสถิติการเข้าชมสำหรับเจ้าของกิจการ"""
    try:
        cursor = get_cursor()
        
        # สถิติสรุป
        cursor.execute('SELECT COUNT(*) as total FROM page_views')
        total_page_views = cursor.fetchone()['total']
        
        cursor.execute('SELECT SUM(views) as total FROM page_views')
        total_visits = cursor.fetchone()['total'] or 0
        
        # ดึงข้อมูลสถิติการเข้าชมจากตาราง page_views (top pages)
        cursor.execute('''
            SELECT page_id, views, last_viewed_at
            FROM page_views 
            ORDER BY views DESC
            LIMIT 10
        ''')
        top_pages = cursor.fetchall()
        
        # ดึงข้อมูลสถิติตามอุปกรณ์จากตาราง page_view_logs
        cursor.execute('''
            SELECT device_type, COUNT(*) as count
            FROM page_view_logs
            GROUP BY device_type
            ORDER BY count DESC
        ''')
        device_stats = cursor.fetchall()
        
        # ดึงข้อมูลการเข้าชมรายวัน (7 วันล่าสุด)
        cursor.execute('''
            SELECT DATE(viewed_at) as date, COUNT(*) as count
            FROM page_view_logs
            WHERE viewed_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(viewed_at)
            ORDER BY date DESC
        ''')
        daily_visits = cursor.fetchall()
        
        return render_template('owner/page_views_report.html', 
                             total_page_views=total_page_views,
                             total_visits=total_visits,
                             top_pages=top_pages,
                             device_stats=device_stats,
                             daily_visits=daily_visits)
        
    except Exception as e:
        print(f"Error in page_views_report: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดรายงาน', 'error')
        return redirect(url_for('owner.dashboard'))


@owner.route('/profile', methods=['GET', 'POST'])
@owner_login_required
def profile():
    """หน้าแก้ไขข้อมูลผู้ใช้เจ้าของกิจการ"""
    try:
        cursor = get_cursor()
        
        # ดึงข้อมูลผู้ใช้ปัจจุบัน
        owner_user_id = session.get('owner_user_id')
        cursor.execute('''
            SELECT u.user_id, u.username, u.name, u.avatar_filename, u.role_name
            FROM users u
            WHERE u.user_id = %s
        ''', (owner_user_id,))
        user = cursor.fetchone()
        
        if request.method == 'POST':
            # อัปเดตข้อมูลผู้ใช้
            name = request.form.get('name')
            
            # อัปเดตชื่อ
            cursor.execute('''
                UPDATE users 
                SET name = %s
                WHERE user_id = %s
            ''', (name, owner_user_id))
            
            flash('อัปเดตข้อมูลเรียบร้อยแล้ว', 'success')
            return redirect(url_for('owner.profile'))
        
        return render_template('owner/profile.html', user=user)
        
    except Exception as e:
        print(f"Error in owner profile: {e}")
        flash('เกิดข้อผิดพลาดในการโหลดข้อมูล', 'error')
        return redirect(url_for('owner.dashboard'))


@owner.route('/logout', methods=['POST', 'GET'])
@owner_login_required
def logout():
    """ออกจากระบบเจ้าของกิจการ"""
    session.clear()
    session.permanent = False
    flash('ออกจากระบบเจ้าของกิจการเรียบร้อย', 'success')
    return redirect(url_for('auth.login'))





