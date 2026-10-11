نظام جمع روابط حصص الزوم — متوسطة الثغر النموذجية الأهلية
=========================================================

محتويات الحزمة:
- zoom_links_app.py   : التطبيق (مع الشعار الرسمي والتنسيقات الاحترافية الجديدة).
- logo_data.py        : شعار المدرسة الرسمي مضمّن Base64 (لا ينكسر عند الرفع/التنزيل).
- fonts/              : الخطوط العربية الاحترافية المرفقة:
    * NotoNaskhArabic-Regular.ttf / NotoNaskhArabic-Bold.ttf (خط النسخ للمتن والعناوين)
    * DejaVuSans.ttf (خط احتياطي للأقواس وعلامات الترقيم اللاتينية)
- requirements.txt    : حزم بايثون المطلوبة.
- packages.txt        : حزم النظام (خطوط) عند النشر على Streamlit Cloud.

التشغيل محليًا:
  pip install -r requirements.txt
  streamlit run zoom_links_app.py

إعداد Supabase (الأسرار):
  أنشئ ملف .streamlit/secrets.toml وضع فيه:
    [supabase]
    url = "https://xxxx.supabase.co"
    key = "YOUR_ANON_KEY"

ملاحظات:
- الشعار يظهر الآن في ترويسة التطبيق على الشاشة وفي ترويسة تقارير PDF.
- التقارير أصبحت بخط النسخ العربي الاحترافي، مع ترويسة وتذييل رسميين وجدول منسّق وصندوق ملخص.
- يجب إبقاء مجلد fonts/ وملف logo_data.py بجانب zoom_links_app.py.
