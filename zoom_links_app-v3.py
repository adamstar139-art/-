import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime
from fpdf import FPDF
from PIL import Image, ImageDraw
import io
import os
import re

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
# 2. إنشاء شعار مدرسة الثغر وتنسيق الخطوط العربية (RTL)
# ---------------------------------------------------------

def create_thaghar_logo_file():
    logo_path = "/workspace/scratch/thaghar_school_logo.png"
    if os.path.exists(logo_path):
        return logo_path
    try:
        w, h = 300, 300
        img = Image.new('RGBA', (w, h), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        green = (0, 108, 53, 255)
        gold = (197, 160, 89, 255)
        cx, cy = 150, 150
        scale = 1.8
        
        b_pts_outer = [
            (cx - int(60*scale), cy - int(10*scale)),
            (cx - int(5*scale), cy + int(25*scale)),
            (cx, cy + int(30*scale)),
            (cx + int(5*scale), cy + int(25*scale)),
            (cx + int(60*scale), cy - int(10*scale)),
            (cx + int(65*scale), cy - int(5*scale)),
            (cx + int(5*scale), cy + int(35*scale)),
            (cx, cy + int(40*scale)),
            (cx - int(5*scale), cy + int(35*scale)),
            (cx - int(65*scale), cy - int(5*scale)),
        ]
        draw.polygon(b_pts_outer, fill=green)
        
        for offset, color in [(-10, green), (-3, gold), (3, green)]:
            draw.line([
                (cx - int(50*scale), cy - int(3*scale) + int(offset*scale)),
                (cx - int(5*scale), cy + int(20*scale) + int(offset*scale))
            ], fill=color, width=int(3*scale))
            draw.line([
                (cx + int(50*scale), cy - int(3*scale) + int(offset*scale)),
                (cx + int(5*scale), cy + int(20*scale) + int(offset*scale))
            ], fill=color, width=int(3*scale))
            
        draw.ellipse([cx - int(20*scale), cy - int(40*scale), cx - int(8*scale), cy - int(28*scale)], fill=green)
        draw.ellipse([cx + int(8*scale), cy - int(40*scale), cx + int(20*scale), cy - int(28*scale)], fill=gold)
        
        img.save(logo_path)
        return logo_path
    except Exception:
        return None

ARABIC_MAP = {
    'ا': ('ﺍ', 'ﺍ', 'ﺎ', 'ﺎ'),
    'أ': ('ﺃ', 'ﺃ', 'ﺄ', 'ﺄ'),
    'إ': ('ﺇ', 'ﺇ', 'ﺈ', 'ﺈ'),
    'آ': ('ﺁ', 'ﺁ', 'ﺂ', 'ﺂ'),
    'ب': ('ﺏ', 'ﺑ', 'ﺒ', 'ﺐ'),
    'ت': ('ﺓ', 'ﺕ', 'ﺖ', 'ﺔ'),
    'ث': ('ﺗ', 'ﺙ', 'ﺚ', 'ﺘ'),
    'ج': ('ﺝ', 'ﺟ', 'ﺠ', 'ﺞ'),
    'ح': ('ﺡ', 'ﺣ', 'ﺤ', 'ﺢ'),
    'خ': ('ﺥ', 'ﺧ', 'ﺨ', 'ﺦ'),
    'د': ('ﺩ', 'ﺩ', 'ﺪ', 'ﺪ'),
    'ذ': ('ﺫ', 'ﺫ', 'ﺬ', 'ﺬ'),
    'ر': ('ﺭ', 'ﺭ', 'ﺮ', 'ﺮ'),
    'ز': ('ﺯ', 'ﺯ', 'ﺰ', 'ﺰ'),
    'س': ('ﺱ', 'ﺳ', 'ﺴ', 'ﺲ'),
    'ش': ('ﺵ', 'ﺷ', 'ﺸ', 'ﺶ'),
    'ص': ('ﺹ', 'ﺻ', 'ﺼ', 'ﺺ'),
    'ض': ('ﺽ', 'ﺿ', 'ﻀ', 'ﺾ'),
    'ط': ('ﻁ', 'ﻃ', 'ﻄ', 'ﻂ'),
    'ظ': ('ﻅ', 'ﻇ', 'ﻈ', 'ﻆ'),
    'ع': ('ﻉ', 'ﻋ', 'ﻌ', 'ﻊ'),
    'غ': ('ﻍ', 'ﻏ', 'ﻐ', 'ﻎ'),
    'ف': ('ﻑ', 'ﻓ', 'ﻔ', 'ﻒ'),
    'ق': ('ﻕ', 'ﻗ', 'ﻘ', 'ﻖ'),
    'ك': ('ﻙ', 'ﻛ', 'ﻜ', 'ﻚ'),
    'ل': ('ﻝ', 'ﻟ', 'ﻠ', 'ﻞ'),
    'م': ('ﻡ', 'ﻣ', 'ﻤ', 'ﻢ'),
    'ن': ('ﻥ', 'ﻧ', 'ﻨ', 'ﻦ'),
    'ه': ('ﻩ', 'ﻫ', 'ﻬ', 'ﻪ'),
    'و': ('ﻭ', 'ﻭ', 'ﻮ', 'ﻮ'),
    'ي': ('ﻯ', 'ﻳ', 'ﻴ', 'ﻰ'),
    'ى': ('ﻱ', 'ﻱ', 'ﻲ', 'ﻲ'),
    'ة': ('ﺓ', 'ﺓ', 'ﺔ', 'ﺔ'),
    'ء': ('ﺀ', 'ﺀ', 'ﺀ', 'ﺀ'),
    'ئ': ('ﺉ', 'ﺋ', 'ﺌ', 'ﺊ'),
    'ؤ': ('ﺅ', 'ﺅ', 'ﺆ', 'ﺆ'),
}
NON_CONNECTING = {'ا', 'أ', 'إ', 'آ', 'د', 'ذ', 'ر', 'ز', 'و', 'ؤ', 'ة', 'ى'}
LAM_ALEF_MAP = {
    ('ل', 'ا'): ('ﻻ', 'ﻼ'),
    ('ل', 'أ'): ('ﻷ', 'ﻸ'),
    ('ل', 'إ'): ('ﻹ', 'ﻺ'),
    ('ل', 'آ'): ('ﻵ', 'ﻶ'),
}

def ar(text):
    if not text: return ""
    text = str(text)
    trans_table = str.maketrans("()[]{}", ")(}{][")
    tokens = re.split(r'(\s+)', text)
    processed_tokens = []
    
    for token in tokens:
        if not token.strip():
            processed_tokens.append(token)
            continue
        has_arabic = any(c in ARABIC_MAP for c in token)
        if not has_arabic:
            processed_tokens.append(token)
            continue
            
        reshaped = []
        n = len(token)
        i = 0
        while i < n:
            if i < n - 1 and token[i] == 'ل' and token[i+1] in ('ا', 'أ', 'إ', 'آ'):
                pair = (token[i], token[i+1])
                prev_conn = (i > 0) and (token[i-1] in ARABIC_MAP) and (token[i-1] not in NON_CONNECTING)
                iso, fin = LAM_ALEF_MAP[pair]
                reshaped.append(fin if prev_conn else iso)
                i += 2
                continue
                
            c = token[i]
            if c not in ARABIC_MAP:
                reshaped.append(c.translate(trans_table))
                i += 1
                continue
                
            prev_conn = (i > 0) and (token[i-1] in ARABIC_MAP) and (token[i-1] not in NON_CONNECTING)
            next_conn = (i < n - 1) and (token[i+1] in ARABIC_MAP)
            iso, ini, med, fin = ARABIC_MAP[c]
            
            if prev_conn and next_conn and (c not in NON_CONNECTING):
                reshaped.append(med)
            elif prev_conn:
                reshaped.append(fin)
            elif next_conn and (c not in NON_CONNECTING):
                reshaped.append(ini)
            else:
                reshaped.append(iso)
            i += 1
            
        processed_tokens.append("".join(reshaped))
        
    full_str = "".join(processed_tokens)
    words = full_str.split(' ')
    reversed_words = []
    for w in reversed(words):
        if any(ord(c) > 127 for c in w):
            reversed_words.append(w[::-1])
        else:
            reversed_words.append(w)
            
    return " ".join(reversed_words)

# ---------------------------------------------------------
# 3. إعدادات وقاعدة بيانات Supabase
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
# 4. دالة إنشاء تقرير PDF احترافي بنسب 100% بدون تداخل خطوط
# ---------------------------------------------------------

class ThagharFPDF(FPDF):
    def header(self):
        font_b = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_r = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        
        if not os.path.exists(font_b):
            font_b = "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"
        if not os.path.exists(font_r):
            font_r = "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"

        self.add_font('MainBold', '', font_b)
        self.add_font('MainReg', '', font_r)
        
        # الشريط العلوي الأخضر والذهبي
        self.set_fill_color(0, 108, 53)
        self.rect(0, 0, 210, 4, 'F')
        self.set_fill_color(197, 160, 89)
        self.rect(0, 4, 210, 1.5, 'F')
        
        # شعار مدرسة الثغر
        logo_img = create_thaghar_logo_file()
        if logo_img and os.path.exists(logo_img):
            self.image(logo_img, x=15, y=9, w=22)
            
        # نص الترويسة الرسمية
        self.set_font('MainBold', size=14)
        self.set_text_color(0, 108, 53)
        self.cell(0, 8, ar("المملكة العربية السعودية - وزارة التعليم"), align='C', new_x='LMARGIN', new_y='NEXT')
        
        self.set_font('MainReg', size=11)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, ar("إدارة التعليم بمحافظة الرياض"), align='C', new_x='LMARGIN', new_y='NEXT')
        
        self.set_font('MainBold', size=13)
        self.set_text_color(0, 108, 53)
        self.cell(0, 8, ar("مدرسة متوسطة الثغر النموذجية الأهلية"), align='C', new_x='LMARGIN', new_y='NEXT')
        
        # خط فاصل ذهبي
        self.set_draw_color(197, 160, 89)
        self.set_line_width(0.8)
        self.line(15, 36, 195, 36)
        self.ln(6)

def generate_perfect_pdf_report(df, selected_date, day_str, section_title=""):
    pdf = ThagharFPDF()
    pdf.add_page()
    
    # عنوان التقرير الرئاسي
    pdf.set_font('MainBold', size=12)
    pdf.set_fill_color(240, 248, 242)
    pdf.set_draw_color(0, 108, 53)
    pdf.set_text_color(0, 108, 53)
    
    title_str = f"تقرير روابط حصص الزوم اليومية - يوم {day_str} ({selected_date})"
    if section_title:
        title_str += f" - ({section_title})"
        
    pdf.cell(0, 10, ar(title_str), border=1, align='C', fill=True, new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)
    
    # ترتيب أعمدة الجدول من اليمين إلى اليسار (RTL Table)
    col_widths = [38, 25, 25, 30, 32, 40]
    headers_rtl = ['رابط الحصة', 'الحصة', 'الفصل', 'الصف', 'المادة', 'المعلم']
    
    pdf.set_fill_color(0, 108, 53)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('MainBold', size=10)
    
    for i, h in enumerate(headers_rtl):
        pdf.cell(col_widths[i], 9, ar(h), border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('MainReg', size=9.5)
    
    if df.empty:
        pdf.cell(sum(col_widths), 10, ar("لا توجد حصص مسجلة لهذا اليوم / الفصل"), border=1, align='C')
        pdf.ln()
    else:
        fill = False
        for _, row in df.iterrows():
            pdf.set_fill_color(245, 248, 245) if fill else pdf.set_fill_color(255, 255, 255)
            
            # Col 0: Zoom Link (Leftmost)
            zoom_url = str(row.get('zoom_link', ''))
            pdf.set_text_color(0, 102, 204)
            pdf.cell(col_widths[0], 8, ar("رابط الحصة"), border=1, align='C', fill=fill, link=zoom_url if zoom_url.startswith("http") else "")
            pdf.set_text_color(0, 0, 0)
            
            # Cols 1 to 5
            pdf.cell(col_widths[1], 8, ar(str(row.get('period', '-'))), border=1, align='C', fill=fill)
            pdf.cell(col_widths[2], 8, ar(str(row.get('section', '-'))), border=1, align='C', fill=fill)
            pdf.cell(col_widths[3], 8, ar(str(row.get('grade', '-'))), border=1, align='C', fill=fill)
            pdf.cell(col_widths[4], 8, ar(str(row.get('subject') or '-')), border=1, align='C', fill=fill)
            pdf.cell(col_widths[5], 8, ar(str(row.get('teacher_name', '-'))), border=1, align='C', fill=fill)
            
            pdf.ln()
            fill = not fill
            
    pdf.ln(12)
    
    # التوقيعات والاعتمادات الرسمية أسفل التقرير
    pdf.set_font('MainBold', size=9.5)
    w_col = 60
    pdf.cell(w_col, 6, ar("وكيل الشؤون الطلاب"), align='C')
    pdf.cell(w_col, 6, ar("وكيل الشؤون التعليمية"), align='C')
    pdf.cell(w_col, 6, ar("مدير المدرسة"), align='C', new_x='LMARGIN', new_y='NEXT')
    
    pdf.set_font('MainReg', size=9)
    pdf.cell(w_col, 6, ar("صالح بن عبدالله الدعجاني"), align='C')
    pdf.cell(w_col, 6, ar("محمد مبروك السيد"), align='C')
    pdf.cell(w_col, 6, ar("إبراهيم بن موسى التميمي"), align='C', new_x='LMARGIN', new_y='NEXT')
    
    pdf.ln(4)
    pdf.set_font('MainBold', size=9.5)
    pdf.cell(0, 6, ar("المسؤول التقني والمنصة: محمد سامي السعيد"), align='C', new_x='LMARGIN', new_y='NEXT')
    
    return bytes(pdf.output())

# ---------------------------------------------------------
# 5. الواجهة الرئيسية والتنقل بين الصفحات
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

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

menu = st.sidebar.radio(
    "📌 القائمة الرئيسية",
    ["📝 تسجيل رابط حصة (المعلم)", "📊 التقرير اليومي ولوحة التحكم (الإدارة)", "⚙️ إدارة وتعديل السجلات"]
)

if st.session_state["authenticated"]:
    st.sidebar.divider()
    if st.sidebar.button("🔒 تسجيل خروج الإدارة"):
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
                st.success(f"✅ تم حفظ رابط الحصة بنجاح للمعلم ({teacher_name}) - {grade} ({section}) - {period}!")
            else:
                st.error(f"⚠️ {msg}")

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
                
                st.markdown("### 🖨️ خيارات الطباعة والتصدير (PDF / Excel)")
                
                tab1, tab2, tab3 = st.tabs(["📄 طباعة التقرير العام الشامل", "🎯 طباعة تقرير فصل منفصل (PDF)", "📊 تصدير Excel"])
                
                with tab1:
                    st.write("طباعة تقرير كلي لجميع الحصص والصفوف المسجلة لهذا اليوم:")
                    pdf_bytes_all = generate_perfect_pdf_report(df, date_str, day_name_str, section_title="جميع الفصول")
                    st.download_button(
                        label="🖨️ تحميل التقرير الشامل لجميع الفصول (PDF)",
                        data=pdf_bytes_all,
                        file_name=f"تقرير_جميع_الفصول_{date_str}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                with tab2:
                    st.write("اختر فصلاً محداً لطباعة تقرير منفصل به فقط:")
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
