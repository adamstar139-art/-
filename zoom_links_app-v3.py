import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime
import io
import os
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------
# 1. إعدادات الصفحة والهوية البصرية (Saudi Theme & RTL)
# ---------------------------------------------------------
st.set_page_config(
    page_title="نظام جمع روابط الحصص | متوسطة الثغر النموذجية الأهلية",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    
    html, body, [class*="css"], div, span, h1, h2, h3, h4, p, label, input, button {
        font-family: 'Cairo', sans-serif !important;
        direction: rtl;
        text-align: right;
    }
    
    .saudi-header {
        background: linear-gradient(135deg, #006C35 0%, #004D25 100%);
        color: #FFFFFF;
        padding: 22px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-bottom: 5px solid #C5A059;
    }
    
    .saudi-header h1 {
        font-size: 24px;
        font-weight: 800;
        margin: 0;
        color: #FFFFFF !important;
    }
    
    .saudi-header h2 {
        font-size: 19px;
        font-weight: 700;
        margin-top: 5px;
        color: #D3E7D3 !important;
    }
    
    .saudi-header h3 {
        font-size: 16px;
        font-weight: 600;
        margin-top: 5px;
        color: #C5A059 !important;
    }
    
    .stButton>button {
        background-color: #006C35 !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 8px 24px !important;
        border: none !important;
        width: 100%;
    }
    
    .stButton>button:hover {
        background-color: #004D25 !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. إعدادات وقاعدة بيانات Supabase
# ---------------------------------------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

try:
    if "supabase" in st.secrets:
        SUPABASE_URL = st.secrets["supabase"].get("url", SUPABASE_URL)
        SUPABASE_KEY = st.secrets["supabase"].get("key", SUPABASE_KEY)
    elif "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
        SUPABASE_URL = st.secrets["SUPABASE_URL"]
        SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    pass

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

TABLE_NAME = "zoom_records"

def insert_record(teacher, day, date_val, grade, section, period, link, subject):
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    payload = {
        "teacher_name": teacher,
        "day_name": day,
        "lesson_date": date_val,
        "grade": grade,
        "section": section,
        "period": period,
        "zoom_link": link,
        "subject": subject
    }
    try:
        response = requests.post(endpoint, json=payload, headers=HEADERS, timeout=10)
        if response.status_code in [200, 201]:
            return True, "تم الحفظ بنجاح في Supabase"
        else:
            return False, f"خطأ من الخادم ({response.status_code}): {response.text}"
    except Exception as e:
        return False, f"تعذر الاتصال بالمشروع: {str(e)}"

def fetch_records(filter_date=None, filter_grade=None, filter_section=None):
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    params = {
        "select": "id,teacher_name,day_name,lesson_date,grade,section,period,zoom_link,subject",
        "order": "lesson_date.desc,period.asc"
    }
    if filter_date:
        params["lesson_date"] = f"eq.{filter_date}"
    if filter_grade and filter_grade != "الكل":
        params["grade"] = f"eq.{filter_grade}"
    if filter_section and filter_section != "الكل":
        params["section"] = f"eq.{filter_section}"
        
    try:
        response = requests.get(endpoint, headers=HEADERS, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return pd.DataFrame(data)
        else:
            return pd.DataFrame(columns=['id', 'teacher_name', 'day_name', 'lesson_date', 'grade', 'section', 'period', 'zoom_link', 'subject'])
    except Exception:
        return pd.DataFrame(columns=['id', 'teacher_name', 'day_name', 'lesson_date', 'grade', 'section', 'period', 'zoom_link', 'subject'])

def delete_record(record_id):
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    params = {"id": f"eq.{record_id}"}
    try:
        response = requests.delete(endpoint, headers=HEADERS, params=params, timeout=10)
        return response.status_code in [200, 204]
    except Exception:
        return False

# ---------------------------------------------------------
# 3. دالة إنشاء تقرير PDF عالي الجودة ومطابق لخط التقرير الشامل
# ---------------------------------------------------------

def draw_thagher_logo(draw, cx, cy, scale=1.2):
    navy = (26, 46, 90)
    gold = (197, 160, 89)
    
    b_pts_outer = [
        (cx - int(100*scale), cy - int(20*scale)),
        (cx - int(10*scale), cy + int(40*scale)),
        (cx, cy + int(50*scale)),
        (cx + int(10*scale), cy + int(40*scale)),
        (cx + int(100*scale), cy - int(20*scale)),
        (cx + int(110*scale), cy - int(10*scale)),
        (cx + int(10*scale), cy + int(55*scale)),
        (cx, cy + int(65*scale)),
        (cx - int(10*scale), cy + int(55*scale)),
        (cx - int(110*scale), cy - int(10*scale)),
    ]
    draw.polygon(b_pts_outer, fill=navy)
    
    for offset, color in [(-15, navy), (-5, gold), (5, navy)]:
        draw.line([
            (cx - int(80*scale), cy - int(5*scale) + int(offset*scale)),
            (cx - int(10*scale), cy + int(35*scale) + int(offset*scale))
        ], fill=color, width=int(4*scale))
        draw.line([
            (cx + int(80*scale), cy - int(5*scale) + int(offset*scale)),
            (cx + int(10*scale), cy + int(35*scale) + int(offset*scale))
        ], fill=color, width=int(4*scale))
        
    draw.ellipse([cx - int(35*scale), cy - int(65*scale), cx - int(15*scale), cy - int(45*scale)], fill=navy)
    draw.polygon([
        (cx - int(25*scale), cy - int(42*scale)),
        (cx - int(50*scale), cy - int(10*scale)),
        (cx - int(5*scale), cy + int(10*scale)),
    ], fill=navy)
    
    draw.ellipse([cx + int(15*scale), cy - int(65*scale), cx + int(35*scale), cy - int(45*scale)], fill=gold)
    draw.polygon([
        (cx + int(25*scale), cy - int(42*scale)),
        (cx + int(50*scale), cy - int(10*scale)),
        (cx + int(5*scale), cy + int(10*scale)),
    ], fill=gold)

def generate_perfect_pdf_report(df_records, selected_date, day_str, section_title=""):
    W, H = 2480, 3508 # A4 at 300 DPI
    img = Image.new('RGB', (W, H), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # البحث عن الخط الكوفي/النسخي المعتمد
    kufi_bold = "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"
    kufi_reg = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"
    
    if not os.path.exists(kufi_bold):
        kufi_bold = "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"
    if not os.path.exists(kufi_reg):
        kufi_reg = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"

    font_header_bold = ImageFont.truetype(kufi_bold, 52)
    font_title_bold = ImageFont.truetype(kufi_bold, 44)
    font_tbl_head = ImageFont.truetype(kufi_bold, 36)
    font_tbl_body = ImageFont.truetype(kufi_reg, 34)
    font_sub = ImageFont.truetype(kufi_reg, 38)
    font_footer_b = ImageFont.truetype(kufi_bold, 34)
    font_footer_r = ImageFont.truetype(kufi_reg, 32)

    # شريط الهوية العلوية
    draw.rectangle([0, 0, W, 45], fill=(0, 108, 53))
    draw.rectangle([0, 45, W, 60], fill=(197, 160, 89))

    # ترويسة التقرير
    y = 140
    draw.text((W // 2, y), "المملكة العربية السعودية - وزارة التعليم", fill=(0, 108, 53), font=font_header_bold, anchor="mm")
    y += 85
    draw.text((W // 2, y), "إدارة التعليم بمحافظة الرياض", fill=(70, 70, 70), font=font_sub, anchor="mm")
    y += 75
    draw.text((W // 2, y), "مدرسة متوسطة الثغر النموذجية الأهلية", fill=(0, 108, 53), font=font_header_bold, anchor="mm")

    y += 80
    draw.line([120, y, W - 120, y], fill=(197, 160, 89), width=5)

    # عنوان التقرير
    y += 85
    title_text = f"تقرير روابط حصص الزوم اليومية - يوم {day_str} ({selected_date})"
    if section_title:
        title_text += f" - ({section_title})"
    
    draw.rounded_rectangle([150, y, W - 150, y + 110], radius=18, fill=(240, 248, 242), outline=(0, 108, 53), width=4)
    draw.text((W // 2, y + 55), title_text, fill=(0, 108, 53), font=font_title_bold, anchor="mm")

    # إعداد جدول الحصص
    y_table = y + 170
    col_widths = [480, 320, 280, 260, 260, 520]
    x_start = (W - sum(col_widths)) // 2

    headers = ["المعلم", "المادة", "الصف", "الفصل", "الحصة", "رابط الحصة"]
    row_height = 95

    x_curr = x_start
    for i, h_text in enumerate(headers):
        w_col = col_widths[i]
        draw.rectangle([x_curr, y_table, x_curr + w_col, y_table + row_height], fill=(0, 108, 53), outline=(0, 80, 40), width=2)
        draw.text((x_curr + w_col // 2, y_table + row_height // 2), h_text, fill=(255, 255, 255), font=font_tbl_head, anchor="mm")
        x_curr += w_col

    y_curr = y_table + row_height

    if df_records.empty:
        total_w = sum(col_widths)
        draw.rectangle([x_start, y_curr, x_start + total_w, y_curr + 120], fill=(255, 255, 255), outline=(200, 200, 200), width=2)
        draw.text((W // 2, y_curr + 60), "لا توجد حصص مسجلة لهذا اليوم / الفصل", fill=(100, 100, 100), font=font_tbl_body, anchor="mm")
        y_curr += 120
    else:
        for idx, row in df_records.iterrows():
            bg_color = (245, 250, 246) if idx % 2 == 1 else (255, 255, 255)
            vals = [
                str(row.get('teacher_name', '-')),
                str(row.get('subject') or '-'),
                str(row.get('grade', '-')),
                str(row.get('section', '-')),
                str(row.get('period', '-')),
                "رابط الحصة المباشر"
            ]
            x_curr = x_start
            for i, val in enumerate(vals):
                w_col = col_widths[i]
                draw.rectangle([x_curr, y_curr, x_curr + w_col, y_curr + row_height], fill=bg_color, outline=(210, 220, 212), width=2)
                text_color = (0, 102, 204) if i == 5 else (30, 30, 30)
                draw.text((x_curr + w_col // 2, y_curr + row_height // 2), val, fill=text_color, font=font_tbl_body, anchor="mm")
                x_curr += w_col
            y_curr += row_height

    # قسم التوقيعات والاعتمادات الرسمية
    y_footer = max(y_curr + 120, H - 550)
    draw.line([120, y_footer - 40, W - 120, y_footer - 40], fill=(200, 200, 200), width=3)

    w_sec = (W - 240) // 3
    x1 = 120 + w_sec // 2
    x2 = 120 + w_sec + w_sec // 2
    x3 = 120 + 2 * w_sec + w_sec // 2

    draw.text((x1, y_footer), "وكيل الشؤون الطلاب", fill=(0, 108, 53), font=font_footer_b, anchor="mm")
    draw.text((x2, y_footer), "وكيل الشؤون التعليمية", fill=(0, 108, 53), font=font_footer_b, anchor="mm")
    draw.text((x3, y_footer), "مدير المدرسة", fill=(0, 108, 53), font=font_footer_b, anchor="mm")

    draw.text((x1, y_footer + 65), "صالح بن عبدالله الدعجاني", fill=(40, 40, 40), font=font_footer_r, anchor="mm")
    draw.text((x2, y_footer + 65), "محمد مبروك السيد", fill=(40, 40, 40), font=font_footer_r, anchor="mm")
    draw.text((x3, y_footer + 65), "إبراهيم بن موسى التميمي", fill=(40, 40, 40), font=font_footer_r, anchor="mm")

    y_footer_2 = y_footer + 160
    draw.text((W // 2, y_footer_2), "المسؤول التقني والمنصة: محمد سامي السعيد", fill=(0, 108, 53), font=font_footer_b, anchor="mm")

    pdf_bytes_io = io.BytesIO()
    img.save(pdf_bytes_io, format='PDF', resolution=300.0)
    return pdf_bytes_io.getvalue()

# ---------------------------------------------------------
# 4. الواجهة الرئيسية والتنقل في التطبيق
# ---------------------------------------------------------

st.markdown("""
<div class="saudi-header">
    <h1>المملكة العربية السعودية - وزارة التعليم</h1>
    <h2>إدارة التعليم بمحافظة الرياض</h2>
    <h3>مدرسة متوسطة الثغر النموذجية الأهلية</h3>
    <hr style="border: 0; height: 1px; background: #C5A059; margin: 10px 0;">
    <p style="margin: 0; font-size: 18px; font-weight: 700;">منصة تسجيل ورصد روابط حصص الزوم (Supabase Cloud Sync)</p>
</div>
""", unsafe_allow_html=True)

if SUPABASE_URL and SUPABASE_KEY:
    st.sidebar.success("⚡ النظام متصل بقاعدة بيانات Supabase")
else:
    st.sidebar.warning("⚠️ يرجى إضافة مفاتيح Supabase في Secrets")

# التحقق من حالة تسجيل الدخول للإدارة
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

menu = st.sidebar.radio(
    "📌 القائمة الرئيسية",
    ["📝 تسجيل رابط حصة (المعلم)", "📊 التقرير اليومي ولوحة التحكم (الإدارة)", "⚙️ إدارة وتعديل السجلات"]
)

if st.session_state["authenticated"]:
    st.sidebar.success("🔑 تم تسجيل الدخول كإداري")
    if st.sidebar.button("🔒 تسجيل الخروج"):
        st.session_state["authenticated"] = False
        st.rerun()

DAYS_LIST = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]
GRADES_LIST = ["الأول متوسط", "الثاني متوسط", "الثالث متوسط"]
PERIODS_LIST = ["الحصة الأولى", "الحصة الثانية", "الحصة الثالثة", "الحصة الرابعة", "الحصة الخامسة", "الحصة السادسة", "الحصة السابعة"]

ALL_SECTIONS = [
    "أول أول", "أول ثاني",
    "ثاني أول", "ثاني ثاني", "ثاني ثالث",
    "ثالث أول", "ثالث ثاني", "ثالث ثالث"
]

TEACHERS_LIST = [
    "محمد سامي السعيد",
    "علي محمد معوض",
    "أحمد عبد الحميد سعيد",
    "محمد عبد المنعم أبو كيلة",
    "هيثم رضا عطية",
    "عماد الدين نصر كرم",
    "السيد الغريب بدوي",
    "محمد إبراهيم عبد الرحمن",
    "أسامة أحمد سالم",
    "عماد بكر عارف",
    "إبراهيم علي العتيبي",
    "عيسى خالد العويس",
    "زيد بن علي التميمي",
    "أحمد سلامة",
    "معلم آخر (أدخل الاسم)"
]

# ---------------------------------------------------------
# الصفحة 1: تسجيل رابط حصة (المعلم) - مفتوحة بدون كلمة مرور
# ---------------------------------------------------------
if menu == "📝 تسجيل رابط حصة (المعلم)":
    st.subheader("📝 نموذج إضافة رابط حصة افتراضية جديد")
    st.info("💡 اختر البيانات واضغط حفظ لإرسال الرابط مباشرة.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        teacher_select = st.selectbox("اسم المعلم:", TEACHERS_LIST)
        if teacher_select == "معلم آخر (أدخل الاسم)":
            teacher_name = st.text_input("أدخل اسم المعلم الثلاثي:")
        else:
            teacher_name = teacher_select
            
        day_name = st.selectbox("اليوم:", DAYS_LIST)
        lesson_date = st.date_input("تاريخ الحصة:", value=date.today())
        subject = st.text_input("المادة الدراسية (مثال: المهارات الرقمية):")
        
    with col2:
        grade = st.selectbox("الصف الدراسي:", GRADES_LIST, key="grade_selectbox")
        
        if grade == "الأول متوسط":
            section_options = ["أول أول", "أول ثاني"]
        elif grade == "الثاني متوسط":
            section_options = ["ثاني أول", "ثاني ثاني", "ثاني ثالث"]
        elif grade == "الثالث متوسط":
            section_options = ["ثالث أول", "ثالث ثاني", "ثالث ثالث"]
        else:
            section_options = ["1", "2", "3"]
            
        section = st.selectbox("الفصل / الشعبة:", section_options, key="section_selectbox")
        period = st.selectbox("رقم الحصة:", PERIODS_LIST)
        zoom_link = st.text_input("رابط الزوم (Zoom Link):", placeholder="ألصق رابط الحصة هنا")
        
    submit_button = st.button("💾 حفظ وإرسال الرابط إلى Supabase", use_container_width=True)
    
    if submit_button:
        if not teacher_name or not zoom_link:
            st.error("⚠️ يرجى التأكد من اختيار/كتابة اسم المعلم ولصق رابط الزوم كاملاً!")
        elif not zoom_link.startswith("http"):
            st.warning("⚠️ يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://")
        else:
            success, msg = insert_record(teacher_name, day_name, lesson_date.strftime("%Y-%m-%d"), grade, section, period, zoom_link, subject)
            if success:
                st.success(f"✅ تم حفظ رابط الحصة بنجاح في Supabase للمعلم ({teacher_name}) - {grade} ({section}) - {period}!")
            else:
                st.error(f"⚠️ {msg}")

# ---------------------------------------------------------
# الصفحات المحمية بكلمة مرور (666666): التقرير والإدارة
# ---------------------------------------------------------
else:
    if not st.session_state["authenticated"]:
        st.subheader("🔒 منطقة محمية (خاصة بالإدارة والكنترول)")
        st.info("يرجى إدخال كلمة المرور للوصول إلى التقرير اليومي ولوحة تحكم النظام.")
        
        col_p1, col_p2 = st.columns([3, 1])
        with col_p1:
            pwd_input = st.text_input("كلمة المرور:", type="password", key="admin_password_field")
        with col_p2:
            st.write("")
            st.write("")
            btn_login = st.button("🔓 دخول للإدارة")
            
        if btn_login or pwd_input:
            if pwd_input == "666666":
                st.session_state["authenticated"] = True
                st.success("✅ تم تسجيل الدخول بنجاح!")
                st.rerun()
            elif pwd_input:
                st.error("❌ كلمة المرور غير صحيحة!")
    else:
        if menu == "📊 التقرير اليومي ولوحة التحكم (الإدارة)":
            st.subheader("📊 جدول ورصد روابط الحصص اليومية والطباعة والتصدير")
            
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                selected_date = st.date_input("اختر تاريخ التقرير:", value=date.today())
            with col_f2:
                selected_grade = st.selectbox("تصفية العرض حسب الصف:", ["الكل"] + GRADES_LIST)
            with col_f3:
                selected_section_filter = st.selectbox("تصفية العرض حسب الفصل:", ["الكل"] + ALL_SECTIONS)
                
            date_str = selected_date.strftime("%Y-%m-%d")
            df = fetch_records(
                filter_date=date_str, 
                filter_grade=selected_grade,
                filter_section=selected_section_filter
            )
            
            day_name_str = DAYS_LIST[selected_date.weekday() % 5] if selected_date.weekday() < 5 else "اليوم"
            
            st.markdown(f"### 📋 حصص يوم {day_name_str} الموافق ({date_str})")
            
            if df.empty:
                st.warning("ℹ️ لا توجد روابط حصص مسجلة لهذا التاريخ أو المصفى المختار.")
            else:
                c1, c2, c3 = st.columns(3)
                c1.metric("إجمالي الحصص المسجلة", len(df))
                c2.metric("عدد المعلمين المشاركين", df['teacher_name'].nunique() if 'teacher_name' in df.columns else 0)
                c3.metric("الصفوف المكتملة", df['grade'].nunique() if 'grade' in df.columns else 0)
                
                st.divider()
                
                cols_to_show = [c for c in ['teacher_name', 'subject', 'grade', 'section', 'period', 'zoom_link'] if c in df.columns]
                display_df = df[cols_to_show].copy()
                display_df.columns = ['المعلم', 'المادة', 'الصف', 'الفصل', 'الحصة', 'رابط الزوم'][:len(cols_to_show)]
                
                st.dataframe(display_df, use_container_width=True)
                
                st.divider()
                
                st.markdown("### 🖨️ خيارات الطباعة والتصدير عالية الجودة (PDF / Excel)")
                
                tab1, tab2, tab3 = st.tabs(["📄 طباعة التقرير العام الشامل", "🎯 طباعة تقرير فصل منفصل (PDF)", "📊 تصدير Excel"])
                
                with tab1:
                    st.write("طباعة تقرير كلي لجميع الحصص والصفوف المسجلة لهذا اليوم بنفس خط التقرير الشامل:")
                    pdf_bytes_all = generate_perfect_pdf_report(df, date_str, day_name_str, section_title="جميع الفصول")
                    st.download_button(
                        label="🖨️ تحميل التقرير الشامل لجميع الفصول (PDF)",
                        data=pdf_bytes_all,
                        file_name=f"تقرير_جميع_الفصول_{date_str}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                with tab2:
                    st.write("اختر فصلاً محدداً لطباعة تقرير منفصل به فقط:")
                    target_sec = st.selectbox("اختر الفصل المراد طباعته:", ALL_SECTIONS, key="print_single_section")
                    
                    if 'section' in df.columns:
                        df_sec = df[df['section'] == target_sec]
                    else:
                        df_sec = pd.DataFrame()
                        
                    if df_sec.empty:
                        st.info(f"لا توجد حصص مسجلة لفصل ({target_sec}) في تاريخ {date_str}.")
                    else:
                        st.success(f"تم العثور على {len(df_sec)} حصة مسجلة لفصل ({target_sec}).")
                        
                    pdf_bytes_sec = generate_perfect_pdf_report(df_sec, date_str, day_name_str, section_title=f"فصل {target_sec}")
                    st.download_button(
                        label=f"📄 تحميل تقرير (فصل {target_sec}) منفصل (PDF)",
                        data=pdf_bytes_sec,
                        file_name=f"تقرير_فصل_{target_sec}_{date_str}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                with tab3:
                    st.write("تصدير الجدول إلى ملف Excel للتعديل أو الأرشفة:")
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        display_df.to_excel(writer, index=False, sheet_name="الحصص")
                    excel_bytes = excel_buffer.getvalue()
                    
                    st.download_button(
                        label="📊 تصدير البيانات إلى ملف Excel (.xlsx)",
                        data=excel_bytes,
                        file_name=f"جدول_الحصص_{date_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

        elif menu == "⚙️ إدارة وتعديل السجلات":
            st.subheader("⚙️ إدارة وتعديل روابط الحصص المسجلة")
            
            selected_date_mgt = st.date_input("اختر تاريخ اليوم للتحكم بالسجلات:", value=date.today())
            date_str_mgt = selected_date_mgt.strftime("%Y-%m-%d")
            
            df_mgt = fetch_records(filter_date=date_str_mgt)
            
            if df_mgt.empty:
                st.info("لا توجد سجلات متاحة للتعديل أو الحذف في هذا التاريخ.")
            else:
                st.write("اختر السجل الذي ترغب في حذفه أو تعديله:")
                for idx, row in df_mgt.iterrows():
                    with st.expander(f"📌 {row.get('teacher_name', 'معلم')} | {row.get('grade', '-')} - {row.get('section', '-')} | {row.get('period', '-')}"):
                        st.write(f"**المادة:** {row.get('subject') or 'غير محددة'}")
                        st.write(f"**الرابط:** [{row.get('zoom_link')}]({row.get('zoom_link')})")
                        if st.button(f"❌ حذف هذا السجل (رقم {row.get('id')})", key=f"del_{row.get('id')}"):
                            if delete_record(row.get('id')):
                                st.success("تم حذف السجل بنجاح من Supabase!")
                                st.rerun()
                            else:
                                st.error("تعذر حذف السجل من Supabase.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #777; font-size: 13px;'>تطوير نظام إدارة التعليم | متوسطة الثغر النموذجية الأهلية - بالرياض © 1448 هـ</p>", unsafe_allow_html=True)
