import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime
from fpdf import FPDF
import io
import os

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

SUPABASE_URL = ""
SUPABASE_KEY = ""

if "supabase" in st.secrets:
    SUPABASE_URL = st.secrets["supabase"].get("url", "")
    SUPABASE_KEY = st.secrets["supabase"].get("key", "")
elif "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
else:
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

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

def fetch_records(filter_date=None, filter_grade=None):
    endpoint = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    params = {
        "select": "id,teacher_name,day_name,lesson_date,grade,section,period,zoom_link,subject",
        "order": "lesson_date.desc,period.asc"
    }
    if filter_date:
        params["lesson_date"] = f"eq.{filter_date}"
    if filter_grade and filter_grade != "الكل":
        params["grade"] = f"eq.{filter_grade}"
        
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
# 3. دالة إنشاء تقرير PDF برئاسة الهوية السعودية
# ---------------------------------------------------------
class PDFReport(FPDF):
    def header(self):
        font_path = '/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf'
        self.add_font('NotoBold', '', font_path)
        self.set_font('NotoBold', size=14)
        
        self.cell(0, 7, 'المملكة العربية السعودية - وزارة التعليم', align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_font('NotoBold', size=12)
        self.cell(0, 6, 'إدارة التعليم بمحافظة جدة', align='C', new_x='LMARGIN', new_y='NEXT')
        self.set_font('NotoBold', size=13)
        self.cell(0, 7, 'مدرسة متوسطة الثغر النموذجية الأهلية', align='C', new_x='LMARGIN', new_y='NEXT')
        
        self.set_draw_color(0, 108, 53)
        self.set_line_width(1)
        self.line(10, 32, 200, 32)
        self.ln(8)

def generate_pdf_report(df, selected_date, day_str):
    pdf = PDFReport()
    pdf.add_page()
    
    font_reg = '/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'
    font_bold = '/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf'
    pdf.add_font('NotoReg', '', font_reg)
    pdf.add_font('NotoBold', '', font_bold)
    
    pdf.set_font('NotoBold', size=13)
    pdf.cell(0, 8, f'تقرير روابط حصص الزوم اليومية - يوم {day_str} ({selected_date})', align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(4)
    
    pdf.set_font('NotoBold', size=10)
    pdf.set_fill_color(0, 108, 53)
    pdf.set_text_color(255, 255, 255)
    
    col_widths = [45, 30, 25, 25, 20, 45]
    headers = ['المعلم', 'المادة', 'الصف', 'الفصل', 'الحصة', 'رابط الحصة']
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align='C', fill=True)
    pdf.ln()
    
    pdf.set_font('NotoReg', size=9)
    pdf.set_text_color(0, 0, 0)
    
    if df.empty:
        pdf.cell(sum(col_widths), 10, 'لا توجد حصص مسجلة لهذا اليوم', border=1, align='C')
    else:
        fill = False
        for _, row in df.iterrows():
            pdf.set_fill_color(240, 245, 240) if fill else pdf.set_fill_color(255, 255, 255)
            pdf.cell(col_widths[0], 8, str(row.get('teacher_name', '-')), border=1, align='C', fill=fill)
            pdf.cell(col_widths[1], 8, str(row.get('subject') or '-'), border=1, align='C', fill=fill)
            pdf.cell(col_widths[2], 8, str(row.get('grade', '-')), border=1, align='C', fill=fill)
            pdf.cell(col_widths[3], 8, str(row.get('section', '-')), border=1, align='C', fill=fill)
            pdf.cell(col_widths[4], 8, str(row.get('period', '-')), border=1, align='C', fill=fill)
            link_display = "رابط الحصة"
            pdf.cell(col_widths[5], 8, link_display, border=1, align='C', fill=fill, link=str(row.get('zoom_link', '')))
            pdf.ln()
            fill = not fill
            
    pdf.ln(10)
    pdf.set_font('NotoBold', size=10)
    pdf.cell(90, 6, 'إعداد/ المنسق الإعلامي والتقني', align='R')
    pdf.cell(100, 6, 'اعتماد مدير المدرسة: متوسطة الثغر النموذجية الأهلية', align='L')
    
    return bytes(pdf.output())

# ---------------------------------------------------------
# 4. الواجهة الرئيسية للبرنامج
# ---------------------------------------------------------

st.markdown("""
<div class="saudi-header">
    <h1>المملكة العربية السعودية - وزارة التعليم</h1>
    <h2>إدارة التعليم بمحافظة جدة</h2>
    <h3>مدرسة متوسطة الثغر النموذجية الأهلية</h3>
    <hr style="border: 0; height: 1px; background: #C5A059; margin: 10px 0;">
    <p style="margin: 0; font-size: 18px; font-weight: 700;">منصة تسجيل ورصد روابط حصص الزوم (Supabase Cloud Sync)</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.success("⚡ النظام متصل بقاعدة بيانات Supabase")

menu = st.sidebar.radio(
    "📌 القائمة الرئيسية",
    ["📝 تسجيل رابط حصة (المعلم)", "📊 التقرير اليومي ولوحة التحكم (الإدارة)", "⚙️ إدارة وتعديل السجلات"]
)

DAYS_LIST = ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس"]
GRADES_LIST = ["الأول متوسط", "الثاني متوسط", "الثالث متوسط"]
PERIODS_LIST = ["الحصة الأولى", "الحصة الثانية", "الحصة الثالثة", "الحصة الرابعة", "الحصة الخامسة", "الحصة السادسة", "الحصة السابعة"]

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
    st.info("💡 عند تغيير الصف الدراسي، ستتحدث قائمة الفصول المتاحة تلقائياً بلمسة واحدة.")
    
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
        # اختيار الصف بدون st.form ليعمل الربط الديناميكي الفوري للفصول
        grade = st.selectbox("الصف الدراسي:", GRADES_LIST, key="grade_selectbox")
        
        # ربط الفصول المتاحة بناءً على الصف المختار ديناميكياً
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

elif menu == "📊 التقرير اليومي ولوحة التحكم (الإدارة)":
    st.subheader("📊 جدول ورصد روابط الحصص اليومية")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_date = st.date_input("اختر تاريخ التقرير:", value=date.today())
    with col_f2:
        selected_grade = st.selectbox("تصفية حسب الصف:", ["الكل"] + GRADES_LIST)
        
    date_str = selected_date.strftime("%Y-%m-%d")
    df = fetch_records(filter_date=date_str, filter_grade=selected_grade)
    
    day_name_str = DAYS_LIST[selected_date.weekday() % 5] if selected_date.weekday() < 5 else "اليوم"
    
    st.markdown(f"### 📋 حصص يوم {day_name_str} الموافق ({date_str})")
    
    if df.empty:
        st.warning("ℹ️ لا توجد روابط حصص مسجلة لهذا التاريخ في Supabase حتى الآن.")
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
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            pdf_bytes = generate_pdf_report(df, date_str, day_name_str)
            st.download_button(
                label="📄 تحميل التقرير الرسمي المطبوع (PDF)",
                data=pdf_bytes,
                file_name=f"تقرير_حصص_الزوم_{date_str}.pdf",
                mime="application/pdf"
            )
            
        with col_exp2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                display_df.to_excel(writer, index=False, sheet_name="الحصص")
            excel_bytes = excel_buffer.getvalue()
            
            st.download_button(
                label="📊 تصدير البيانات إلى Excel (.xlsx)",
                data=excel_bytes,
                file_name=f"جدول_الحصص_{date_str}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
st.markdown("<p style='text-align: center; color: #777; font-size: 13px;'>تطوير نظام إدارة التعليم | متوسطة الثغر النموذجية الأهلية - بجدة © 1448 هـ</p>", unsafe_allow_html=True)
