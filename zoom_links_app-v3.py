import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime
from fpdf import FPDF
from PIL import Image, ImageDraw
import io
import os
import re
import base64
import tempfile
import html as _html

# شعار المدرسة مضمّن Base64 (مع احتياطي حتى لا ينكسر مهما كان موقع التشغيل)
try:
    from logo_data import load_logo_b64
    _LOGO_B64 = load_logo_b64()
except Exception:
    _LOGO_B64 = ""

# مجلد الخطوط العربية الاحترافية المرفقة بجانب التطبيق
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_DIR = os.path.join(_APP_DIR, "fonts")

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

_LOGO_CACHE_PATH = None

def create_thaghar_logo_file():
    """يفكّ شعار المدرسة المضمّن (Base64) إلى ملف مؤقت ليستخدمه مولّد PDF.
    يعتمد على الشعار الرسمي المرفوع، وليس رسمًا مؤقتًا."""
    global _LOGO_CACHE_PATH
    if _LOGO_CACHE_PATH and os.path.exists(_LOGO_CACHE_PATH):
        return _LOGO_CACHE_PATH

    # 1) الشعار الرسمي المضمّن Base64
    if _LOGO_B64:
        try:
            raw = base64.b64decode(_LOGO_B64)
            tmp = tempfile.NamedTemporaryFile(prefix="thaghr_logo_", suffix=".png", delete=False)
            tmp.write(raw)
            tmp.flush()
            tmp.close()
            _LOGO_CACHE_PATH = tmp.name
            return _LOGO_CACHE_PATH
        except Exception:
            pass

    # 2) شعار مرفق بجانب التطبيق (احتياطي)
    for cand in ("school_logo.png", "logo.png", "thaghr_logo.png"):
        p = os.path.join(_APP_DIR, cand)
        if os.path.exists(p):
            _LOGO_CACHE_PATH = p
            return p
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
    'ي': ('ﻱ', 'ﻳ', 'ﻴ', 'ﻰ'),
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

def update_record(record_id, teacher, day, date_val, grade, section, period, link, subject):
    """يحدّث حصة مسجّلة قائمة في Supabase (حسب رقم السجل id)."""
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    params = {"id": f"eq.{record_id}"}
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
        response = requests.patch(endpoint, json=payload, headers=HEADERS, params=params, timeout=10)
        if response.status_code in [200, 204]:
            return True, "تم تحديث الحصة بنجاح"
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
# أوقات الحصص الرسمية (مستخرجة من الجدول الزمني للمدرسة)
# تُشتق تلقائيًا من اسم الحصة وتظهر في التقارير (PDF / HTML / الشاشة / Excel)
# ---------------------------------------------------------
PERIOD_TIMES = {
    "الحصة الأولى": "6:30 - 7:15",
    "الحصة الثانية": "7:15 - 8:00",
    "الحصة الثالثة": "8:00 - 8:45",
    "الحصة الرابعة": "9:05 - 9:50",
    "الحصة الخامسة": "9:50 - 10:35",
    "الحصة السادسة": "10:35 - 11:20",
    "الحصة السابعة": "11:20 - 12:05",
}

def get_period_time(period):
    """يعيد وقت الحصة (بداية - نهاية) المطابق لاسم الحصة، أو '-' إن لم يوجد."""
    return PERIOD_TIMES.get(str(period).strip(), "-")

# ---------------------------------------------------------
# 4. دالة إنشاء تقرير PDF احترافي بنسب 100% بدون تداخل خطوط
# ---------------------------------------------------------

# ------- خطوط عربية احترافية: نسخ (للمتن) وكوفي (للعناوين) -------
def _resolve_font(bundled_names, system_paths):
    """يبحث أولاً عن الخط المرفق بجانب التطبيق ثم في خطوط النظام."""
    for name in bundled_names:
        p = os.path.join(_FONT_DIR, name)
        if os.path.exists(p):
            return p
    for p in system_paths:
        if os.path.exists(p):
            return p
    return None

FONT_BODY = _resolve_font(
    ["NotoNaskhArabic-Regular.ttf"],
    ["/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
     "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"],
)
FONT_BODY_BOLD = _resolve_font(
    ["NotoNaskhArabic-Bold.ttf"],
    ["/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
     "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"],
)
FONT_TITLE = _resolve_font(
    ["NotoNaskhArabic-Bold.ttf"],
    ["/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
     "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"],
)
# خط لاتيني احتياطي للرموز وعلامات الترقيم والأقواس التي لا تتوفر في خط النسخ
FONT_FALLBACK = _resolve_font(
    ["DejaVuSans.ttf"],
    ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
)

# ألوان الهوية البصرية
CLR_GREEN = (0, 108, 53)
CLR_GREEN_DARK = (0, 77, 37)
CLR_GOLD = (197, 160, 89)
CLR_GREY = (90, 90, 90)
CLR_ROW = (244, 249, 245)

class ThagharFPDF(FPDF):
    def header(self):
        # تسجيل الخطوط العربية الاحترافية (مرة واحدة)
        if not getattr(self, "_fonts_ready", False):
            self.add_font('MainReg', '', FONT_BODY)
            self.add_font('MainBold', '', FONT_BODY_BOLD)
            self.add_font('MainTitle', '', FONT_TITLE)
            # خط احتياطي للرموز اللاتينية وعلامات الترقيم
            if FONT_FALLBACK:
                try:
                    self.add_font('Fallback', '', FONT_FALLBACK)
                    self.set_fallback_fonts(['Fallback'])
                except Exception:
                    pass
            self._fonts_ready = True

        # الشريط العلوي الأخضر والذهبي
        self.set_fill_color(*CLR_GREEN)
        self.rect(0, 0, 210, 5, 'F')
        self.set_fill_color(*CLR_GOLD)
        self.rect(0, 5, 210, 1.6, 'F')

        # شعار المدرسة الرسمي (يسار الترويسة)
        logo_img = create_thaghar_logo_file()
        if logo_img and os.path.exists(logo_img):
            try:
                self.image(logo_img, x=14, y=10, h=26)
            except Exception:
                pass

        # نص الترويسة الرسمية
        self.set_y(10)
        self.set_font('MainTitle', size=14)
        self.set_text_color(*CLR_GREEN)
        self.cell(0, 8, ar("المملكة العربية السعودية - وزارة التعليم"), align='C', new_x='LMARGIN', new_y='NEXT')

        self.set_font('MainReg', size=10.5)
        self.set_text_color(*CLR_GREY)
        self.cell(0, 6, ar("إدارة التعليم بمحافظة الرياض"), align='C', new_x='LMARGIN', new_y='NEXT')

        self.set_font('MainTitle', size=13)
        self.set_text_color(*CLR_GREEN_DARK)
        self.cell(0, 8, ar("مدرسة متوسطة الثغر النموذجية الأهلية"), align='C', new_x='LMARGIN', new_y='NEXT')

        # خط فاصل ذهبي مزدوج
        self.set_draw_color(*CLR_GOLD)
        self.set_line_width(0.9)
        self.line(14, 38, 196, 38)
        self.set_draw_color(*CLR_GREEN)
        self.set_line_width(0.3)
        self.line(14, 39.2, 196, 39.2)
        self.ln(10)

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(*CLR_GOLD)
        self.set_line_width(0.5)
        self.line(14, self.get_y(), 196, self.get_y())
        self.ln(1.5)
        self.set_font('MainReg', size=8)
        self.set_text_color(130, 130, 130)
        gen = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cell(0, 5, ar("متوسطة الثغر النموذجية الأهلية — الرياض") + "   |   " + ar("تاريخ الإصدار: ") + gen + "   |   " + ar("صفحة ") + str(self.page_no()), align='C')

def generate_perfect_pdf_report(df, selected_date, day_str, section_title=""):
    pdf = ThagharFPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # شريط عنوان التقرير الرئيسي
    pdf.set_font('MainTitle', size=12)
    pdf.set_fill_color(*CLR_GREEN)
    pdf.set_text_color(255, 255, 255)
    title_str = f"تقرير روابط حصص الزوم اليومية — يوم {day_str} ({selected_date})"
    pdf.cell(0, 11, ar(title_str), border=0, align='C', fill=True, new_x='LMARGIN', new_y='NEXT')

    if section_title:
        pdf.set_font('MainBold', size=10.5)
        pdf.set_fill_color(*CLR_GOLD)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, ar(section_title), border=0, align='C', fill=True, new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)

    # صندوق ملخّص سريع (عدد الحصص / المعلمين / الصفوف)
    n_lessons = 0 if df is None or df.empty else len(df)
    n_teachers = 0 if df is None or df.empty or 'teacher_name' not in df.columns else df['teacher_name'].nunique()
    n_grades = 0 if df is None or df.empty or 'grade' not in df.columns else df['grade'].nunique()
    pdf.set_font('MainReg', size=9.5)
    pdf.set_text_color(*CLR_GREEN_DARK)
    pdf.set_fill_color(240, 248, 242)
    pdf.set_draw_color(*CLR_GOLD)
    pdf.set_line_width(0.3)
    summary = (f"إجمالي الحصص: {n_lessons}      •      عدد المعلمين: {n_teachers}"
               f"      •      الصفوف: {n_grades}")
    pdf.cell(0, 9, ar(summary), border=1, align='C', fill=True, new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)

    # جدول من اليمين إلى اليسار (RTL) — يُقرأ: المعلم ← المادة ← الصف ← الفصل ← الحصة ← وقت الحصة ← الرابط
    # (إضافة عمود "وقت الحصة" بجانب رقم الحصة)
    col_widths = [34, 24, 20, 22, 26, 30, 36]
    headers_rtl = ['رابط الحصة', 'وقت الحصة', 'الحصة', 'الفصل', 'الصف', 'المادة', 'المعلم']
    table_w = sum(col_widths)
    x_start = (210 - table_w) / 2

    pdf.set_x(x_start)
    pdf.set_fill_color(*CLR_GREEN)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('MainBold', size=10)
    pdf.set_draw_color(*CLR_GREEN_DARK)
    pdf.set_line_width(0.2)
    for i, h in enumerate(headers_rtl):
        pdf.cell(col_widths[i], 10, ar(h), border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_text_color(40, 40, 40)
    pdf.set_font('MainReg', size=9.5)
    pdf.set_draw_color(210, 215, 210)

    if df is None or df.empty:
        pdf.set_x(x_start)
        pdf.set_fill_color(252, 245, 245)
        pdf.set_text_color(150, 60, 60)
        pdf.cell(table_w, 11, ar("لا توجد حصص مسجلة لهذا اليوم / الفصل"), border=1, align='C', fill=True)
        pdf.ln()
    else:
        fill = False
        for _, row in df.iterrows():
            pdf.set_x(x_start)
            if fill:
                pdf.set_fill_color(*CLR_ROW)
            else:
                pdf.set_fill_color(255, 255, 255)

            # العمود 0: رابط الزوم (قابل للنقر)
            zoom_url = str(row.get('zoom_link', ''))
            pdf.set_text_color(0, 90, 180)
            pdf.set_font('MainBold', size=9.5)
            pdf.cell(col_widths[0], 8.5, ar("فتح الرابط"), border=1, align='C', fill=True,
                     link=zoom_url if zoom_url.startswith("http") else "")
            pdf.set_text_color(40, 40, 40)
            pdf.set_font('MainReg', size=9.5)

            period_val = str(row.get('period', '-'))
            # العمود 1: وقت الحصة (أرقام لاتينية تُعرض كما هي دون عكس)
            pdf.cell(col_widths[1], 8.5, get_period_time(period_val), border=1, align='C', fill=True)
            pdf.cell(col_widths[2], 8.5, ar(period_val), border=1, align='C', fill=True)
            pdf.cell(col_widths[3], 8.5, ar(str(row.get('section', '-'))), border=1, align='C', fill=True)
            pdf.cell(col_widths[4], 8.5, ar(str(row.get('grade', '-'))), border=1, align='C', fill=True)
            pdf.cell(col_widths[5], 8.5, ar(str(row.get('subject') or '-')), border=1, align='C', fill=True)
            pdf.cell(col_widths[6], 8.5, ar(str(row.get('teacher_name', '-'))), border=1, align='C', fill=True)
            pdf.ln()
            fill = not fill

    pdf.ln(14)

    # التوقيعات والاعتمادات الرسمية
    pdf.set_font('MainBold', size=9.5)
    pdf.set_text_color(*CLR_GREEN_DARK)
    w_col = 60
    pdf.cell(w_col, 6, ar("وكيل شؤون الطلاب"), align='C')
    pdf.cell(w_col, 6, ar("وكيل الشؤون التعليمية"), align='C')
    pdf.cell(w_col, 6, ar("مدير المدرسة"), align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(2)
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.2)
    y_line = pdf.get_y()
    for k in range(3):
        cx = 15 + k * w_col
        pdf.line(cx + 10, y_line, cx + w_col - 10, y_line)
    pdf.ln(2)
    pdf.set_font('MainReg', size=9)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(w_col, 6, ar("صالح بن عبدالله الدعجاني"), align='C')
    pdf.cell(w_col, 6, ar("محمد مبروك السيد"), align='C')
    pdf.cell(w_col, 6, ar("إبراهيم بن موسى التميمي"), align='C', new_x='LMARGIN', new_y='NEXT')

    pdf.ln(6)
    pdf.set_font('MainBold', size=9)
    pdf.set_text_color(*CLR_GOLD)
    pdf.cell(0, 6, ar("المسؤول التقني والمنصة: محمد سامي السعيد"), align='C', new_x='LMARGIN', new_y='NEXT')

    return bytes(pdf.output())

def generate_html_report(df, selected_date, day_str, section_title=""):
    """ينشئ تقرير HTML مستقل بالكامل (RTL) مع الشعار المضمّن وتنسيق احترافي قابل للطباعة."""
    logo_uri = ("data:image/png;base64," + _LOGO_B64) if _LOGO_B64 else ""
    logo_tag = (f'<img class="logo" src="{logo_uri}" alt="شعار المدرسة">' if logo_uri else "")

    n_lessons = 0 if df is None or df.empty else len(df)
    n_teachers = 0 if df is None or df.empty or 'teacher_name' not in df.columns else int(df['teacher_name'].nunique())
    n_grades = 0 if df is None or df.empty or 'grade' not in df.columns else int(df['grade'].nunique())

    # بناء صفوف الجدول (ترتيب الأعمدة من اليمين إلى اليسار: المعلم ثم ... ثم الرابط)
    rows_html = ""
    if df is None or df.empty:
        rows_html = ('<tr><td colspan="7" class="empty">لا توجد حصص مسجلة لهذا اليوم / الفصل</td></tr>')
    else:
        for _, row in df.iterrows():
            zoom_url = str(row.get('zoom_link', '') or '')
            if zoom_url.startswith("http"):
                safe_url = _html.escape(zoom_url, quote=True)
                link_cell = f'<a class="zoom" href="{safe_url}" target="_blank" rel="noopener noreferrer">فتح الرابط</a>'
            else:
                link_cell = '<span class="nolink">—</span>'
            teacher = _html.escape(str(row.get('teacher_name', '-')))
            subject = _html.escape(str(row.get('subject') or '-'))
            grade = _html.escape(str(row.get('grade', '-')))
            section = _html.escape(str(row.get('section', '-')))
            period = _html.escape(str(row.get('period', '-')))
            period_time = _html.escape(get_period_time(row.get('period', '')))
            rows_html += (
                "<tr>"
                f"<td class='c-teacher'>{teacher}</td>"
                f"<td>{subject}</td>"
                f"<td>{grade}</td>"
                f"<td>{section}</td>"
                f"<td>{period}</td>"
                f"<td class='c-time'>{period_time}</td>"
                f"<td class='c-link'>{link_cell}</td>"
                "</tr>"
            )

    sec_bar = (f'<div class="subbar">{_html.escape(section_title)}</div>' if section_title else "")
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    title_txt = _html.escape(f"تقرير روابط حصص الزوم اليومية — يوم {day_str} ({selected_date})")

    html_doc = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_txt}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
  * {{ box-sizing: border-box; }}
  body {{ font-family:'Cairo',sans-serif; direction:rtl; text-align:right; background:#eef1ee; color:#222; margin:0; padding:24px; }}
  .sheet {{ max-width:1000px; margin:0 auto; background:#fff; padding:28px 34px 40px; border-radius:10px; box-shadow:0 6px 24px rgba(0,0,0,.12); border-top:6px solid #006C35; }}
  .topbar {{ height:6px; background:linear-gradient(90deg,#006C35,#C5A059); border-radius:4px; margin-bottom:16px; }}
  .head {{ display:flex; align-items:center; gap:18px; border-bottom:2px solid #C5A059; padding-bottom:14px; margin-bottom:4px; }}
  .head .logo {{ height:90px; width:auto; filter:drop-shadow(0 2px 4px rgba(0,0,0,.2)); }}
  .head .titles {{ flex:1; text-align:center; }}
  .head h1 {{ color:#006C35; font-size:20px; font-weight:800; margin:0; }}
  .head h2 {{ color:#555; font-size:14px; font-weight:600; margin:4px 0 0; }}
  .head h3 {{ color:#004D25; font-size:16px; font-weight:700; margin:4px 0 0; }}
  .rpt-title {{ background:#006C35; color:#fff; text-align:center; font-weight:700; font-size:16px; padding:11px; border-radius:6px; margin-top:18px; }}
  .subbar {{ background:#C5A059; color:#fff; text-align:center; font-weight:700; font-size:13px; padding:7px; border-radius:5px; margin-top:6px; }}
  .summary {{ display:flex; justify-content:center; gap:28px; flex-wrap:wrap; background:#f0f8f2; border:1px solid #C5A059; border-radius:6px; padding:12px; margin:16px 0; color:#004D25; font-weight:700; font-size:14px; }}
  .summary span b {{ color:#006C35; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:14px; direction:rtl; }}
  thead th {{ background:#006C35; color:#fff; padding:11px 8px; border:1px solid #004D25; font-weight:700; }}
  tbody td {{ padding:9px 8px; border:1px solid #d6dcd6; text-align:center; }}
  tbody tr:nth-child(even) {{ background:#f4f9f5; }}
  .c-teacher {{ font-weight:600; }}
  .c-time {{ font-weight:700; color:#004D25; direction:ltr; }}
  a.zoom {{ display:inline-block; background:#006C35; color:#fff; text-decoration:none; padding:5px 14px; border-radius:5px; font-weight:700; font-size:13px; }}
  a.zoom:hover {{ background:#004D25; }}
  .nolink {{ color:#aaa; }}
  td.empty {{ text-align:center; color:#9a3c3c; background:#fcf5f5; padding:16px; font-weight:700; }}
  .signs {{ display:flex; justify-content:space-between; margin-top:46px; gap:16px; }}
  .signs .box {{ flex:1; text-align:center; }}
  .signs .role {{ font-weight:700; color:#004D25; font-size:14px; }}
  .signs .line {{ border-top:1px dashed #999; margin:34px 16px 6px; }}
  .signs .name {{ color:#555; font-size:13px; }}
  .tech {{ text-align:center; margin-top:26px; color:#C5A059; font-weight:700; font-size:13px; }}
  .foot {{ margin-top:24px; border-top:1px solid #C5A059; padding-top:8px; text-align:center; color:#999; font-size:12px; }}
  @media print {{ body {{ background:#fff; padding:0; }} .sheet {{ box-shadow:none; border-radius:0; max-width:100%; }} a.zoom {{ color:#006C35; background:none; padding:0; }} }}
</style>
</head>
<body>
  <div class="sheet">
    <div class="topbar"></div>
    <div class="head">
      {logo_tag}
      <div class="titles">
        <h1>المملكة العربية السعودية - وزارة التعليم</h1>
        <h2>إدارة التعليم بمحافظة الرياض</h2>
        <h3>مدرسة متوسطة الثغر النموذجية الأهلية</h3>
      </div>
    </div>
    <div class="rpt-title">{title_txt}</div>
    {sec_bar}
    <div class="summary">
      <span>إجمالي الحصص: <b>{n_lessons}</b></span>
      <span>عدد المعلمين: <b>{n_teachers}</b></span>
      <span>الصفوف: <b>{n_grades}</b></span>
    </div>
    <table>
      <thead>
        <tr>
          <th>المعلم</th><th>المادة</th><th>الصف</th><th>الفصل</th>
          <th>الحصة</th><th>وقت الحصة</th><th>رابط الحصة</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    <div class="signs">
      <div class="box"><div class="role">وكيل شؤون الطلاب</div><div class="line"></div><div class="name">صالح بن عبدالله الدعجاني</div></div>
      <div class="box"><div class="role">وكيل الشؤون التعليمية</div><div class="line"></div><div class="name">محمد مبروك السيد</div></div>
      <div class="box"><div class="role">مدير المدرسة</div><div class="line"></div><div class="name">إبراهيم بن موسى التميمي</div></div>
    </div>
    <div class="tech">المسؤول التقني والمنصة: محمد سامي السعيد</div>
    <div class="foot">متوسطة الثغر النموذجية الأهلية — الرياض&nbsp;&nbsp;|&nbsp;&nbsp;تاريخ الإصدار: {gen_time}</div>
  </div>
</body>
</html>"""
    return html_doc.encode("utf-8")

# ---------------------------------------------------------
# 5. الواجهة الرئيسية والتنقل بين الصفحات
# ---------------------------------------------------------

_LOGO_DATA_URI = ("data:image/png;base64," + _LOGO_B64) if _LOGO_B64 else ""
_logo_html = (f'<img src="{_LOGO_DATA_URI}" alt="شعار المدرسة" '
              f'style="height:84px;margin-bottom:10px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.25));">'
              if _LOGO_DATA_URI else '')

st.markdown(f"""
<div class="saudi-header">
    {_logo_html}
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
# تطابق صحيح بين تاريخ بايثون (Monday=0 ... Sunday=6) واسم اليوم العربي
AR_WEEKDAYS = {
    0: "الإثنين",
    1: "الثلاثاء",
    2: "الأربعاء",
    3: "الخميس",
    4: "الجمعة",
    5: "السبت",
    6: "الأحد",
}

def arabic_day_name(d):
    """يعيد اسم اليوم العربي الصحيح المطابق للتاريخ."""
    return AR_WEEKDAYS.get(d.weekday(), "اليوم")
GRADES_LIST = ["الأول متوسط", "الثاني متوسط", "الثالث متوسط"]
PERIODS_LIST = ["الحصة الأولى", "الحصة الثانية", "الحصة الثالثة", "الحصة الرابعة", "الحصة الخامسة", "الحصة السادسة", "الحصة السابعة"]

# ترتيب رقم الحصة حسب تسلسلها المنطقي (الأولى ← السابعة) وليس أبجديًا
_PERIOD_ORDER = {name: i for i, name in enumerate(PERIODS_LIST)}

def sort_by_period(df):
    """يرتّب حصص الجدول بحسب تسلسل الحصص (الأولى ثم الثانية ...)."""
    if df is None or df.empty or 'period' not in df.columns:
        return df
    out = df.copy()
    # أي قيمة غير معروفة توضع في النهاية
    out['_porder'] = out['period'].map(lambda p: _PERIOD_ORDER.get(str(p), 999))
    sort_cols = ['_porder']
    if 'grade' in out.columns:
        sort_cols.append('grade')
    if 'section' in out.columns:
        sort_cols.append('section')
    out = out.sort_values(by=sort_cols, kind='stable').drop(columns=['_porder']).reset_index(drop=True)
    return out

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
    # تبويبات: تسجيل حصة جديدة — تعديل حصة مسجلة — عرض حصص المعلم
    reg_tab, edit_tab, view_tab = st.tabs(["➕ تسجيل حصة جديدة", "✏️ تعديل حصة مسجلة", "👁️ عرض حصصي وتصديرها PDF"])

    # ============ تبويب تسجيل حصة جديدة ============
    with reg_tab:
        st.subheader("📝 نموذج إضافة رابط حصة افتراضية جديد")
        st.info("💡 اختر البيانات واضغط حفظ لإرسال الرابط مباشرة. الحقول المعلّمة بـ (*) إجبارية.")

        col1, col2 = st.columns(2)

        with col1:
            teacher_select = st.selectbox("اسم المعلم:", TEACHERS_LIST, key="reg_teacher")
            if teacher_select == "معلم آخر (أدخل الاسم)":
                teacher_name = st.text_input("أدخل اسم المعلم الثلاثي:", key="reg_teacher_other")
            else:
                teacher_name = teacher_select

            lesson_date = st.date_input("تاريخ الحصة:", value=date.today(), key="reg_date")
            # يُشتق اسم اليوم تلقائيًا من التاريخ لضمان التطابق
            day_name = arabic_day_name(lesson_date)
            st.text_input("اليوم (تلقائي حسب التاريخ):", value=day_name, disabled=True, key="reg_day")
            subject = st.text_input("المادة الدراسية (*) (مثال: المهارات الرقمية):", key="reg_subject")

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
            period = st.selectbox("رقم الحصة:", PERIODS_LIST, key="reg_period")
            # عرض وقت الحصة تلقائيًا حسب الجدول الزمني للمدرسة
            st.text_input("وقت الحصة (تلقائي حسب الجدول):", value=get_period_time(period), disabled=True, key="reg_time")
            zoom_link = st.text_input("رابط الزوم (Zoom Link):", placeholder="ألصق رابط الحصة هنا", key="reg_link")

        submit_button = st.button("💾 حفظ وإرسال الرابط إلى Supabase", use_container_width=True, key="reg_submit")

        if submit_button:
            if not teacher_name or not zoom_link:
                st.error("⚠️ يرجى التأكد من اختيار/كتابة اسم المعلم ولصق رابط الزوم كاملاً!")
            elif not subject or not subject.strip():
                st.error("⚠️ حقل المادة الدراسية إجباري — يرجى كتابة اسم المادة قبل الحفظ!")
            elif not zoom_link.startswith("http"):
                st.warning("⚠️ يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://")
            else:
                success, msg = insert_record(teacher_name, day_name, lesson_date.strftime("%Y-%m-%d"), grade, section, period, zoom_link, subject.strip())
                if success:
                    st.success(f"✅ تم حفظ رابط الحصة بنجاح للمعلم ({teacher_name}) - {grade} ({section}) - {period}!")
                else:
                    st.error(f"⚠️ {msg}")

    # ============ تبويب تعديل حصة مسجلة ============
    with edit_tab:
        st.subheader("✏️ تعديل بيانات حصة مسجلة")
        st.info("💡 اختر تاريخ الحصة ثم الحصة المراد تعديلها، عدّل الحقول ثم اضغط حفظ التعديلات.")

        edit_date = st.date_input("تاريخ الحصة المراد تعديلها:", value=date.today(), key="edit_date_pick")
        df_edit = fetch_records(filter_date=edit_date.strftime("%Y-%m-%d"))
        df_edit = sort_by_period(df_edit)

        if df_edit is None or df_edit.empty:
            st.warning("ℹ️ لا توجد حصص مسجلة في هذا التاريخ لتعديلها.")
        else:
            rec_options = {}
            for _, r in df_edit.iterrows():
                lbl = f"① {r.get('period','-')} — {r.get('teacher_name','-')} — {r.get('subject') or 'بدون مادة'} — ({r.get('grade','-')} / {r.get('section','-')})"
                rec_options[lbl] = r
            chosen = st.selectbox("اختر الحصة المراد تعديلها:", list(rec_options.keys()), key="edit_rec_sel")
            rec = rec_options[chosen]
            rec_id = rec.get('id')

            e1, e2 = st.columns(2)
            with e1:
                _t = str(rec.get('teacher_name', '') or '')
                _tidx = TEACHERS_LIST.index(_t) if _t in TEACHERS_LIST else len(TEACHERS_LIST) - 1
                e_teacher_sel = st.selectbox("اسم المعلم:", TEACHERS_LIST, index=_tidx, key="edit_teacher")
                if e_teacher_sel == "معلم آخر (أدخل الاسم)":
                    e_teacher = st.text_input("أدخل اسم المعلم الثلاثي:", value=(_t if _t not in TEACHERS_LIST else ""), key="edit_teacher_other")
                else:
                    e_teacher = e_teacher_sel

                try:
                    _d = datetime.strptime(str(rec.get('lesson_date')), "%Y-%m-%d").date()
                except Exception:
                    _d = edit_date
                e_date = st.date_input("تاريخ الحصة:", value=_d, key="edit_lesson_date")
                e_day = arabic_day_name(e_date)
                st.text_input("اليوم (تلقائي):", value=e_day, disabled=True, key="edit_day")
                e_subject = st.text_input("المادة الدراسية (*):", value=str(rec.get('subject') or ''), key="edit_subject")

            with e2:
                _g = str(rec.get('grade', '') or '')
                _gidx = GRADES_LIST.index(_g) if _g in GRADES_LIST else 0
                e_grade = st.selectbox("الصف الدراسي:", GRADES_LIST, index=_gidx, key="edit_grade")

                if e_grade == "الأول متوسط":
                    e_sec_opts = ["أول أول", "أول ثاني"]
                elif e_grade == "الثاني متوسط":
                    e_sec_opts = ["ثاني أول", "ثاني ثاني", "ثاني ثالث"]
                elif e_grade == "الثالث متوسط":
                    e_sec_opts = ["ثالث أول", "ثالث ثاني", "ثالث ثالث"]
                else:
                    e_sec_opts = ["1", "2", "3"]
                _s = str(rec.get('section', '') or '')
                _sidx = e_sec_opts.index(_s) if _s in e_sec_opts else 0
                e_section = st.selectbox("الفصل / الشعبة:", e_sec_opts, index=_sidx, key="edit_section")

                _p = str(rec.get('period', '') or '')
                _pidx = PERIODS_LIST.index(_p) if _p in PERIODS_LIST else 0
                e_period = st.selectbox("رقم الحصة:", PERIODS_LIST, index=_pidx, key="edit_period")
                st.text_input("وقت الحصة (تلقائي):", value=get_period_time(e_period), disabled=True, key="edit_time")
                e_link = st.text_input("رابط الزوم (Zoom Link):", value=str(rec.get('zoom_link') or ''), key="edit_link")

            if st.button("💾 حفظ التعديلات", use_container_width=True, key="edit_submit"):
                if not e_teacher or not e_link:
                    st.error("⚠️ يرجى التأكد من اسم المعلم ورابط الزوم!")
                elif not e_subject or not e_subject.strip():
                    st.error("⚠️ حقل المادة الدراسية إجباري — يرجى كتابة اسم المادة!")
                elif not e_link.startswith("http"):
                    st.warning("⚠️ يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://")
                else:
                    ok, msg = update_record(rec_id, e_teacher, e_day, e_date.strftime("%Y-%m-%d"), e_grade, e_section, e_period, e_link, e_subject.strip())
                    if ok:
                        st.success("✅ تم حفظ تعديلات الحصة بنجاح!")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {msg}")

    # ============ تبويب عرض حصص المعلم وتصديرها PDF ============
    with view_tab:
        st.subheader("👁️ عرض حصص المعلم وتصديرها PDF")
        st.info("💡 اختر اسمك وتاريخ اليوم لعرض جدول الحصص التي أضفتها، ثم حمّلها كملف PDF رسمي.")

        v1, v2 = st.columns(2)
        with v1:
            v_teacher_sel = st.selectbox("اسم المعلم:", TEACHERS_LIST, key="view_teacher")
            if v_teacher_sel == "معلم آخر (أدخل الاسم)":
                v_teacher = st.text_input("أدخل اسم المعلم الثلاثي:", key="view_teacher_other")
            else:
                v_teacher = v_teacher_sel
        with v2:
            v_date = st.date_input("تاريخ اليوم:", value=date.today(), key="view_date")

        v_date_str = v_date.strftime("%Y-%m-%d")
        v_day_str = arabic_day_name(v_date)

        if not v_teacher or not str(v_teacher).strip():
            st.warning("ℹ️ يرجى اختيار/كتابة اسم المعلم أولاً.")
        else:
            v_df = fetch_records(filter_date=v_date_str)
            # تصفية حسب اسم المعلم المختار
            if v_df is not None and not v_df.empty and 'teacher_name' in v_df.columns:
                v_df = v_df[v_df['teacher_name'] == v_teacher]
            v_df = sort_by_period(v_df)

            st.markdown(f"### 📋 حصص المعلم ({v_teacher}) — يوم {v_day_str} ({v_date_str})")

            if v_df is None or v_df.empty:
                st.warning("ℹ️ لا توجد حصص مسجلة لهذا المعلم في هذا التاريخ.")
            else:
                st.success(f"✅ تم العثور على {len(v_df)} حصة مسجلة.")
                _v_cols = [c for c in ['subject', 'grade', 'section', 'period', 'zoom_link'] if c in v_df.columns]
                v_tbl = v_df[_v_cols].copy()
                _v_rename = {'subject': 'المادة', 'grade': 'الصف', 'section': 'الفصل', 'period': 'الحصة', 'zoom_link': 'رابط الزوم'}
                v_tbl = v_tbl.rename(columns=_v_rename)
                if 'المادة' in v_tbl.columns:
                    v_tbl['المادة'] = v_tbl['المادة'].map(lambda s: s if (s and str(s).strip()) else 'بدون مادة')
                if 'الحصة' in v_tbl.columns:
                    _vp = v_tbl.columns.get_loc('الحصة') + 1
                    v_tbl.insert(_vp, 'وقت الحصة', v_df['period'].map(get_period_time).values)
                st.dataframe(v_tbl, use_container_width=True, hide_index=True)

                st.divider()
                v_pdf = generate_perfect_pdf_report(v_df, v_date_str, v_day_str, section_title=f"حصص المعلم: {v_teacher}")
                st.download_button(
                    label="🖨️ تحميل جدول حصصي (PDF)",
                    data=v_pdf,
                    file_name=f"حصص_{v_teacher}_{v_date_str}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

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
            # ترتيب الحصص حسب تسلسلها (الأولى ← السابعة)
            df = sort_by_period(df)

            day_name_str = arabic_day_name(selected_date)

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
                # إضافة عمود "وقت الحصة" (يُشتق تلقائيًا من رقم الحصة)
                if 'الحصة' in display_df.columns:
                    _pos = display_df.columns.get_loc('الحصة') + 1
                    display_df.insert(_pos, 'وقت الحصة', display_df['الحصة'].map(get_period_time))

                st.dataframe(display_df, use_container_width=True)

                st.divider()

                st.markdown("### 🖨️ خيارات الطباعة والتصدير (PDF / HTML / Excel)")

                tab1, tab2, tab3 = st.tabs(["📄 التقرير العام الشامل", "🎯 تقرير فصل منفصل", "📊 تصدير Excel"])

                with tab1:
                    st.write("تقرير كلي لجميع الحصص والصفوف المسجلة لهذا اليوم — اختر صيغة التصدير:")
                    fmt_all = st.radio(
                        "صيغة الملف:", ["PDF", "HTML"],
                        horizontal=True, key="fmt_all"
                    )
                    if fmt_all == "PDF":
                        pdf_bytes_all = generate_perfect_pdf_report(df, date_str, day_name_str, section_title="جميع الفصول")
                        st.download_button(
                            label="🖨️ تحميل التقرير الشامل (PDF)",
                            data=pdf_bytes_all,
                            file_name=f"تقرير_جميع_الفصول_{date_str}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        html_bytes_all = generate_html_report(df, date_str, day_name_str, section_title="جميع الفصول")
                        st.download_button(
                            label="🌐 تحميل التقرير الشامل (HTML)",
                            data=html_bytes_all,
                            file_name=f"تقرير_جميع_الفصول_{date_str}.html",
                            mime="text/html",
                            use_container_width=True
                        )
                        st.caption("💡 ملف HTML يفتح في أي متصفح، ويمكن طباعته أو حفظه PDF من المتصفح (Ctrl + P).")

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

                    fmt_sec = st.radio(
                        "صيغة الملف:", ["PDF", "HTML"],
                        horizontal=True, key="fmt_sec"
                    )
                    if fmt_sec == "PDF":
                        pdf_bytes_sec = generate_perfect_pdf_report(df_sec, date_str, day_name_str, section_title=f"فصل {target_sec}")
                        st.download_button(
                            label=f"📄 تحميل تقرير (فصل {target_sec}) منفصل (PDF)",
                            data=pdf_bytes_sec,
                            file_name=f"تقرير_فصل_{target_sec}_{date_str}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    else:
                        html_bytes_sec = generate_html_report(df_sec, date_str, day_name_str, section_title=f"فصل {target_sec}")
                        st.download_button(
                            label=f"🌐 تحميل تقرير (فصل {target_sec}) منفصل (HTML)",
                            data=html_bytes_sec,
                            file_name=f"تقرير_فصل_{target_sec}_{date_str}.html",
                            mime="text/html",
                            use_container_width=True
                        )
                        st.caption("💡 ملف HTML يفتح في أي متصفح، ويمكن طباعته أو حفظه PDF من المتصفح (Ctrl + P).")

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
            df_mgt = sort_by_period(df_mgt)

            if df_mgt is None or df_mgt.empty:
                st.info("لا توجد سجلات متاحة للتعديل أو الحذف في هذا التاريخ.")
            else:
                # عرض السجلات في جدول واضح (بدل الـ expander المتداخل) لتفادي تداخل النص العربي
                st.markdown("#### 📋 الحصص المسجلة في هذا التاريخ")
                _mgt_cols = [c for c in ['teacher_name', 'subject', 'grade', 'section', 'period'] if c in df_mgt.columns]
                tbl = df_mgt[_mgt_cols].copy()
                _rename = {'teacher_name': 'المعلم', 'subject': 'المادة', 'grade': 'الصف', 'section': 'الفصل', 'period': 'الحصة'}
                tbl = tbl.rename(columns=_rename)
                if 'المادة' in tbl.columns:
                    tbl['المادة'] = tbl['المادة'].map(lambda s: s if (s and str(s).strip()) else 'بدون مادة')
                if 'الحصة' in tbl.columns:
                    _p = tbl.columns.get_loc('الحصة') + 1
                    tbl.insert(_p, 'وقت الحصة', df_mgt['period'].map(get_period_time).values)
                st.dataframe(tbl, use_container_width=True, hide_index=True)

                st.divider()
                st.markdown("#### 🗑️ حذف حصة مسجلة")
                st.caption("لتعديل حصة استخدم تبويب (✏️ تعديل حصة مسجلة) في صفحة تسجيل المعلم.")

                # أداة اختيار واضحة بدل عناوين الـ expander المتداخلة
                mgt_options = {}
                for _, row in df_mgt.iterrows():
                    lbl = f"① {row.get('period','-')} — {row.get('teacher_name','-')} — {row.get('subject') or 'بدون مادة'} — ({row.get('grade','-')} / {row.get('section','-')})"
                    mgt_options[lbl] = row
                sel_lbl = st.selectbox("اختر الحصة:", list(mgt_options.keys()), key="mgt_sel")
                srow = mgt_options[sel_lbl]

                # عرض تفاصيل الحصة في بطاقة مرتبة (أعمدة منفصلة بلا تداخل)
                d1, d2, d3 = st.columns(3)
                d1.markdown(f"**المعلم:** {srow.get('teacher_name','-')}")
                d2.markdown(f"**المادة:** {srow.get('subject') or 'غير محددة'}")
                d3.markdown(f"**الحصة:** {srow.get('period','-')} ({get_period_time(srow.get('period',''))})")
                d4, d5 = st.columns(2)
                d4.markdown(f"**الصف / الفصل:** {srow.get('grade','-')} - {srow.get('section','-')}")
                _lnk = str(srow.get('zoom_link') or '')
                if _lnk.startswith("http"):
                    d5.markdown(f"**الرابط:** [فتح الرابط]({_lnk})")
                else:
                    d5.markdown("**الرابط:** —")

                if st.button(f"❌ حذف هذه الحصة (رقم {srow.get('id')})", key=f"mgt_del_{srow.get('id')}", use_container_width=True):
                    if delete_record(srow.get('id')):
                        st.success("تم حذف السجل بنجاح من Supabase!")
                        st.rerun()
                    else:
                        st.error("تعذر حذف السجل من Supabase.")

st.markdown("---")
st.markdown("<p style='text-align: center; color: #777; font-size: 13px;'>تطوير نظام إدارة التعليم | متوسطة الثغر النموذجية الأهلية - بالرياض © 1448 هـ</p>", unsafe_allow_html=True)
