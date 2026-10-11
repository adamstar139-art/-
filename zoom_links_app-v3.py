import streamlit as st
import pandas as pd
import sqlalchemy as sa
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

# تطبيق تنسيقات CSS للهوية السعودية
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
# 2. ربط قاعدة البيانات الدائمة (Supabase PostgreSQL / SQLite)
# ---------------------------------------------------------
# يقرأ رابط الاتصال بقاعدة بيانات Supabase من Streamlit Secrets أو المتغيرات البيئية
# صيغة رابط Supabase:
# postgresql://postgres:[PASSWORD]@db.looldhswootseeqltohg.supabase.co:5432/postgres

DATABASE_URL = None

if "SUPABASE_DB_URL" in st.secrets:
    DATABASE_URL = st.secrets["SUPABASE_DB_URL"]
elif "DATABASE_URL" in os.environ:
    DATABASE_URL = os.environ["DATABASE_URL"]

# إذا لم يُحدد رابط Supabase، يتم استخدام قاعدة بيانات SQLite محلية مؤقتاً
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///zoom_links.db"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = sa.create_engine(DATABASE_URL, pool_pre_ping=True)

def init_db():
    is_sqlite = DATABASE_URL.startswith("sqlite")
    id_col = "INTEGER PRIMARY KEY AUTOINCREMENT" if is_sqlite else "SERIAL PRIMARY KEY"
    
    create_sql = f'''
        CREATE TABLE IF NOT EXISTS zoom_records (
            id {id_col},
            teacher_name TEXT NOT NULL,
            day_name TEXT NOT NULL,
            lesson_date DATE NOT NULL,
            grade TEXT NOT NULL,
            section TEXT NOT NULL,
            period TEXT NOT NULL,
            zoom_link TEXT NOT NULL,
            subject TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    '''
    with engine.begin() as conn:
        conn.execute(sa.text(create_sql))

init_db()

def insert_record(teacher, day, date_val, grade, section, period, link, subject):
    insert_sql = sa.text('''
        INSERT INTO zoom_records (teacher_name, day_name, lesson_date, grade, section, period, zoom_link, subject)
        VALUES (:teacher, :day, :date_val, :grade, :section, :period, :link, :subject)
    ''')
    with engine.begin() as conn:
        conn.execute(insert_sql, {
            "teacher": teacher,
            "day": day,
            "date_val": date_val,
            "grade": grade,
            "section": section,
            "period": period,
            "link": link,
            "subject": subject
        })

def fetch_records(filter_date=None, filter_grade=None):
    query = "SELECT id, teacher_name, day_name, lesson_date, grade, section, period, zoom_link, subject FROM zoom_records WHERE 1=1"
    params = {}
    if filter_date:
        query += " AND lesson_date = :filter_date"
        params["filter_date"] = filter_date
    if filter_grade and filter_grade != "الكل":
        query += " AND grade = :filter_grade"
        params["filter_grade"] = filter_grade
    
    query += " ORDER BY lesson_date DESC, period ASC, grade ASC, section ASC"
    
    with engine.connect() as conn:
        df = pd.read_sql_query(sa.text(query), conn, params=params)
    return df

def delete_record(record_id):
    del_sql = sa.text("DELETE FROM zoom_records WHERE id = :record_id")
    with engine.begin() as conn:
        conn.execute(del_sql, {"record_id": record_id})

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
            pdf.cell(col_widths[0], 8, str(row['teacher_name']), border=1, align='C', fill=fill)
            pdf.cell(col_widths[1], 8, str(row['subject'] or '-'), border=1, align='C', fill=fill)
            pdf.cell(col_widths[2], 8, str(row['grade']), border=1, align='C', fill=fill)
            pdf.cell(col_widths[3], 8, str(row['section']), border=1, align='C', fill=fill)
            pdf.cell(col_widths[4], 8, str(row['period']), border=1, align='C', fill=fill)
            link_display = "رابط الحصة"
            pdf.cell(col_widths[5], 8, link_display, border=1, align='C', fill=fill, link=str(row['zoom_link']))
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
    <p style="margin: 0; font-size: 18px; font-weight: 700;">منصة تسجيل ورصد روابط حصص الزوم (Supabase Database)</p>
</div>
""", unsafe_allow_html=True)

# تنبيه بحالة نوع قاعدة البيانات
if DATABASE_URL.startswith("sqlite"):
    st.sidebar.warning("⚠️ يعمل النظام حالياً بنمط التخزين المحلي (SQLite). للحفظ الدائم، يُرجى إضافة رابط Supabase في Secrets.")
else:
    st.sidebar.success("⚡ النظام متصل بنجاح بقاعدة بيانات Supabase السحابية الدائمة!")

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
    st.info("يرجى اختيار اسم المعلم واليوم والتاريخ والصف والفصل ثم لصق رابط الزوم.")
    
    with st.form("teacher_form", clear_on_submit=True):
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
            grade = st.selectbox("الصف الدراسي:", GRADES_LIST)
            
            if grade == "الأول متوسط":
                section_options = ["أول أول", "أول ثاني"]
            elif grade == "الثاني متوسط":
                section_options = ["ثاني أول", "ثاني ثاني", "ثاني ثالث"]
            elif grade == "الثالث متوسط":
                section_options = ["ثالث أول", "ثالث ثاني", "ثالث ثالث"]
            else:
                section_options = ["1", "2", "3"]
                
            section = st.selectbox("الفصل / الشعبة:", section_options)
            period = st.selectbox("رقم الحصة:", PERIODS_LIST)
            zoom_link = st.text_input("رابط الزوم (Zoom Link):", placeholder="ألصق رابط الحصة هنا")
            
        submit_button = st.form_submit_button("💾 حفظ وإرسال الرابط")
        
        if submit_button:
            if not teacher_name or not zoom_link:
                st.error("⚠️ يرجى التأكد من اختيار/كتابة اسم المعلم ولصق رابط الزوم كاملاً!")
            elif not zoom_link.startswith("http"):
                st.warning("⚠️ يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://")
            else:
                insert_record(teacher_name, day_name, lesson_date.strftime("%Y-%m-%d"), grade, section, period, zoom_link, subject)
                st.success(f"✅ تم حفظ رابط الحصة بنجاح في قاعدة البيانات المعلم ({teacher_name}) - {grade} ({section}) - {period}!")

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
        st.warning("ℹ️ لا توجد روابط حصص مسجلة لهذا التاريخ حتى الآن.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي الحصص المسجلة", len(df))
        c2.metric("عدد المعلمين المشاركين", df['teacher_name'].nunique())
        c3.metric("الصفوف المكتملة", df['grade'].nunique())
        
        st.divider()
        
        display_df = df[['teacher_name', 'subject', 'grade', 'section', 'period', 'zoom_link']].copy()
        display_df.columns = ['المعلم', 'المادة', 'الصف', 'الفصل', 'الحصة', 'رابط الزوم']
        
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
            with st.expander(f"📌 {row['teacher_name']} | {row['grade']} - {row['section']} | {row['period']}"):
                st.write(f"**المادة:** {row['subject'] or 'غير محددة'}")
                st.write(f"**الرابط:** [{row['zoom_link']}]({row['zoom_link']})")
                if st.button(f"❌ حذف هذا السجل (رقم {row['id']})", key=f"del_{row['id']}"):
                    delete_record(row['id'])
                    st.success("تم حذف السجل بنجاح!")
                    st.rerun()

st.markdown("---")
st.markdown("<p style='text-align: center; color: #777; font-size: 13px;'>تطوير نظام إدارة التعليم | متوسطة الثغر النموذجية الأهلية - بجدة © 1448 هـ</p>", unsafe_allow_html=True)
