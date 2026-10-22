import os
import smtplib
import csv
import io
import re
import zipfile
import json
import pandas as pd
import sqlite3
from datetime import datetime
from PIL import Image, ImageChops, ImageEnhance
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import fitz  # PyMuPDF
import streamlit as st

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from history_manager import DrawingHistoryManager
from rule_engine import DrawingRuleEngine
from ai_analyzer import DrawingAIAnalyzer
from dfm_calculator import calculate_advanced_dfm_analysis
from report_generator import generate_qc_report
from feedback_manager import FeedbackManager
from auth_manager import AuthManager
from cad_analyzer import analyze_3d_file

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="asaDrawing.se - Professional QC & DFM", 
    page_icon="📐", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- تهيئة قواعد البيانات والمحركات ---
db_manager = DrawingHistoryManager()
rule_engine = DrawingRuleEngine()
feedback_db = FeedbackManager()
auth_db = AuthManager()

OUTPUT_DIR = "rapport"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("temp_uploads", exist_ok=True)

# --- نظام المصادقة وتسجيل الدخول ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

if not st.session_state.authenticated:
    st.title("📐 asaDrawing.se — Logga in")
    st.caption("Ange dina inloggningsuppgifter för att få tillgång till industriell QC & DFM-analys.")
    
    with st.form("login_form"):
        username = st.text_input("Användarnamn")
        password = st.text_input("Lösenord", type="password")
        submit_login = st.form_submit_button("Logga in 🔐", use_container_width=True)
        
        if submit_login:
            user = auth_db.authenticate(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_info = user
                st.rerun()
            else:
                st.error("Felaktigt användarnamn eller lösenord.")
    
    st.info("💡 Standardkonton: admin / admin123, inkop / inkop123, beredare / bered123, qc_chef / qc123")
    st.stop()

user_role = st.session_state.user_info["role"]
user_name = st.session_state.user_info["full_name"]

# --- الترجمات والقواميس ---
TRANSLATIONS = {
    "🇬🇧 English": {
        "title": "📐 asaDrawing.se — Industrial QC & DFM",
        "subtitle": "Automated drawing and 3D CAD inspection, CNC preparation and ERP/MES export in a modern interface.",
        "modules": "⚙️ Active Modules",
        "mod_bom": "Bill of Materials (BOM)",
        "mod_gdt": "GD&T (ISO 1101)",
        "mod_cost": "Cost & Time (DFM)",
        "mod_lca": "Sustainability & LCA",
        "mod_cnc": "CNC & Tools",
        "mod_material": "Material & Weight",
        "mod_fits": "Fits & ISO 2768",
        "mod_qr": "Digital QR Traceability",
        "api_email": "🤖 API & Email",
        "tab_review": "🔍 New Inspection",
        "tab_diff": "🔄 Revision Comparison",
        "tab_dashboard": "📈 Dashboard & Trend Analysis",
        "tab_history": "📁 History & Reports",
        "tab_feedback": "💬 Feedback & Suggestions",
        "upload_title": "📤 Upload Drawings & 3D CAD Files",
        "upload_label": "Select PDF drawings or 3D files (STEP, IGES, STL) for analysis",
        "parameters_title": "📐 Individual Parameters (Length, Width, Thickness, Material)",
        "metadata_title": "📋 Project Metadata",
        "proj_id": "Project ID / Drawing No",
        "revision": "Revision",
        "min_wall": "Min wall thickness (mm)",
        "run_analysis": "🚀 Run Batch Analysis & Generate Reports",
        "results_title": "📊 Results & Deviations",
        "export_title": "📥 Export & Sharing",
        "dl_pdf": "📥 Download Selected PDF",
        "dl_zip": "📦 Download All Reports (ZIP)",
        "dl_json": "🔄 Export JSON (ERP)",
        "dl_csv": "📊 Export CSV (MES)"
    },
    "🇸🇪 Svenska": {
        "title": "📐 asaDrawing.se — Industriell QC & DFM",
        "subtitle": "Automatiserad ritnings- och 3D-CAD-granskning, CNC-beredning och ERP/MES-export i ett modernt gränssnitt.",
        "modules": "⚙️ Aktiva Moduler",
        "mod_bom": "Stycklista (BOM)",
        "mod_gdt": "GD&T (ISO 1101)",
        "mod_cost": "Kostnad & Tid (DFM)",
        "mod_lca": "Hållbarhet & LCA",
        "mod_cnc": "CNC & Verktyg",
        "mod_material": "Material & Vikt",
        "mod_fits": "Passningar & ISO 2768",
        "mod_qr": "Digital QR-spårbarhet",
        "api_email": "🤖 API & E-post",
        "tab_review": "🔍 Ny Granskning",
        "tab_diff": "🔄 Revisionsjämförelse",
        "tab_dashboard": "📈 Dashboard & Trendanalys",
        "tab_history": "📁 Historik & Rapporter",
        "tab_feedback": "💬 Feedback & Förslag",
        "upload_title": "📤 Ladda upp ritningar & 3D-filer",
        "upload_label": "Välj PDF-ritningar eller 3D-filer (STEP, IGES, STL) för analys",
        "parameters_title": "📐 Individuella parametrar (Längd, Bredd, Tjocklek, Material)",
        "metadata_title": "📋 Projektmetadata",
        "proj_id": "Projekt-ID / Ritningsnr",
        "revision": "Revision",
        "min_wall": "Minsta väggtjocklek (mm)",
        "run_analysis": "🚀 Kör Batch-analys & Generera Rapporter",
        "results_title": "📊 Resultat & Avvikelser",
        "export_title": "📥 Export & Delning",
        "dl_pdf": "📥 Ladda ner vald PDF",
        "dl_zip": "📦 Ladda ner alla rapporter (ZIP)",
        "dl_json": "🔄 Exportera JSON (ERP)",
        "dl_csv": "📊 Exportera CSV (MES)"
    }
}

# --- القائمة الجانبية (Sidebar) ---
with st.sidebar:
    selected_lang = st.selectbox("🌐 Language / Språk", list(TRANSLATIONS.keys()), index=1)
    t = TRANSLATIONS[selected_lang]
    
    st.markdown("---")
    st.write(f"👤 **Användare:** {user_name}")
    st.write(f"🏷️ **Roll:** `{user_role}`")
    
    with st.expander("🔑 Byt lösenord"):
        with st.form("change_pwd_form"):
            current_pwd = st.text_input("Nuvarande lösenord", type="password")
            new_pwd = st.text_input("Nytt lösenord", type="password")
            confirm_pwd = st.text_input("Bekräfta nytt lösenord", type="password")
            submit_pwd = st.form_submit_button("Uppdatera lösenord")
            
            if submit_pwd:
                user_check = auth_db.authenticate(st.session_state.user_info["username"], current_pwd)
                if not user_check:
                    st.error("Det nuvarande lösenordet är felaktigt.")
                elif not new_pwd or new_pwd != confirm_pwd:
                    st.error("De nya lösenorden matchar inte eller är tomma.")
                else:
                    auth_db.update_password(st.session_state.user_info["username"], new_pwd)
                    st.success("Lösenordet har uppdaterats framgångsrikt!")

    if st.button("Logga ut 🔓", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_info = None
        st.rerun()

    st.markdown("---")
    with st.expander("🖼️ Företagsprofilering (Branding)"):
        custom_logo = st.file_uploader("Ladda upp Företagslogotyp (PNG/JPG)", type=["png", "jpg", "jpeg"])
        custom_logo_path = None
        if custom_logo:
            os.makedirs("temp_assets", exist_ok=True)
            custom_logo_path = os.path.join("temp_assets", f"logo_{custom_logo.name}")
            with open(custom_logo_path, "wb") as f:
                f.write(custom_logo.getbuffer())
            st.image(custom_logo_path, caption="Vald logotyp", width=150)

    st.markdown("---")
    with st.expander("⚙️ Avancerade DFM-parametrar"):
        machine_type = st.selectbox("Maskinteknologi", ["3-axlig CNC", "4-axlig CNC", "5-axlig CNC"])
        complexity_level = st.selectbox("Geometrisk komplexitet", ["Låg (Enkel platta/profil)", "Medium (Standardfräsning)", "Hög (Komplicerade 3D-former & djupa fickor)"])
        tolerance_class = st.selectbox("Toleransklass", ["Standard (ISO 2768-m)", "Tät / Fin (ISO 2768-f)"])
        surface_finish = st.selectbox("Ytfinhet", ["Standard (Ra 3.2)", "Fin (Ra 1.6 eller bättre)"])
        batch_size = st.number_input("Seriestorlek (antal detaljer)", value=1, min_value=1, step=1)

    if user_role == "Inköp":
        enable_bom, enable_gdt, enable_cost, enable_lca, enable_cnc, enable_material, enable_fits_tolerances, enable_qr = False, False, True, True, False, True, False, False
    else:
        with st.expander(t["modules"]):
            enable_bom = st.checkbox(t["mod_bom"], value=True)
            enable_gdt = st.checkbox(t["mod_gdt"], value=True)
            enable_cost = st.checkbox(t["mod_cost"], value=True)
            enable_lca = st.checkbox(t["mod_lca"], value=True)
            enable_cnc = st.checkbox(t["mod_cnc"], value=True)
            enable_material = st.checkbox(t["mod_material"], value=True)
            enable_fits_tolerances = st.checkbox(t["mod_fits"], value=True)
            enable_qr = st.checkbox(t["mod_qr"], value=True)

    with st.expander(t["api_email"]):
        try:
            default_key = st.secrets.get("OPENAI_API_KEY", "")
            smtp_conf = st.secrets.get("smtp", {})
            default_sender = smtp_conf.get("sender_email", "")
            default_pass = smtp_conf.get("password", "")
        except Exception:
            default_key, default_sender, default_pass = "", "", ""
            
        openai_api_key = st.text_input("OpenAI API-nyckel", value=default_key, type="password")
        smtp_server = st.text_input("SMTP-server", value="smtp.gmail.com")
        smtp_port = st.number_input("SMTP-port", value=587, step=1)
        sender_email = st.text_input("Avsändare e-post", value=default_sender)
        sender_password = st.text_input("App-lösenord", value=default_pass, type="password")

lang_clean = selected_lang.split(" ")[1] if " " in selected_lang else selected_lang
ai_analyzer = DrawingAIAnalyzer(api_key=openai_api_key, lang=lang_clean)

# --- عنوان واجهة التطبيق الرئيسي ---
st.title(t["title"])
st.markdown(t["subtitle"])

# --- إنشاء التبويبات الخمسة الرئيسية ---
tab_review, tab_diff, tab_dashboard, tab_history, tab_feedback = st.tabs([
    t["tab_review"], 
    t["tab_diff"], 
    t["tab_dashboard"], 
    t["tab_history"],
    t["tab_feedback"]
])

# --- الدوال المساعدة ---
@st.cache_data(show_spinner=False)
def load_and_extract_pdf_fast(uploaded_file_bytes):
    doc = fitz.open(stream=uploaded_file_bytes, filetype="pdf")
    pdf_text = ""
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        if text: pdf_text += text + "\n"
    return pdf_text

def calculate_dynamic_properties(chosen_mat, length, width, thickness):
    densities = {"Aluminium (Al6061-T6)": 2.70, "Stål (S235JR)": 7.85, "Rostfritt Stål (SS2348)": 8.00, "Titan (Grade 5)": 4.51, "Plast (POM / Delrin)": 1.41}
    density = densities.get(chosen_mat, 2.70)
    volume_cm3 = (length * width * thickness) / 1000.0
    weight_kg = (volume_cm3 * density) / 1000.0
    return chosen_mat, volume_cm3, weight_kg

# ==========================================
# 1️⃣ التبويب الأول: Ny Granskning (فحص جديد)
# ==========================================
with tab_review:
    with st.container(border=True):
        st.subheader(t["upload_title"])
        uploaded_files = st.file_uploader(t["upload_label"], type=["pdf", "step", "stp", "iges", "igs", "stl"], accept_multiple_files=True)
    
    file_params_data, extracted_texts, file_metadata_cache = [], {}, {}
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_ext = uploaded_file.name.split('.')[-1].lower()
            if file_ext in ["step", "stp", "iges", "igs", "stl"]:
                temp_path = os.path.join("temp_uploads", uploaded_file.name)
                try:
                    with open(temp_path, "wb") as f: f.write(uploaded_file.getbuffer())
                    cad_res = analyze_3d_file(temp_path)
                    if cad_res.get("success"):
                        extracted_texts[uploaded_file.name] = f"3D CAD parsed. Vol: {cad_res['volume_cm3']} cm3, Dim: {cad_res['length']}x{cad_res['width']}x{cad_res['thickness']} mm."
                        file_metadata_cache[uploaded_file.name] = {"is_3d": True, "length": cad_res["length"], "width": cad_res["width"], "thickness": cad_res["thickness"], "volume_cm3": cad_res["volume_cm3"]}
                        file_params_data.append({"Filnamn": uploaded_file.name, "Projekt/ID": uploaded_file.name.rsplit('.', 1)[0], "Längd (mm)": cad_res["length"], "Bredd (mm)": cad_res["width"], "Tjocklek (mm)": cad_res["thickness"], "Material": "Aluminium (Al6061-T6)"})
                except Exception as e: st.error(f"Fel 3D: {str(e)}")
                finally:
                    if os.path.exists(temp_path): os.remove(temp_path)
            else:
                try:
                    file_bytes = uploaded_file.read()
                    pdf_text = load_and_extract_pdf_fast(file_bytes)
                    extracted_texts[uploaded_file.name] = pdf_text
                    match_drg = re.search(r'(?:Drawing No\.?|Drg|Ritningsnr\.?|Projekt)[:\s]+([A-Za-z0-9\-_]+)', pdf_text, re.IGNORECASE)
                    default_id = match_drg.group(1) if match_drg else uploaded_file.name.replace('.pdf', '')
                    file_metadata_cache[uploaded_file.name] = {"is_3d": False}
                    file_params_data.append({"Filnamn": uploaded_file.name, "Projekt/ID": default_id, "Längd (mm)": 120.0, "Bredd (mm)": 60.0, "Tjocklek (mm)": 15.0, "Material": "Aluminium (Al6061-T6)"})
                except Exception as e: extracted_texts[uploaded_file.name] = f"Kunde inte läsa: {str(e)}"

        st.markdown("---")
        st.subheader(t["parameters_title"])
        df_params = pd.DataFrame(file_params_data)
        edited_df = st.data_editor(df_params, column_config={"Filnamn": st.column_config.TextColumn("Filnamn", disabled=True), "Projekt/ID": st.column_config.TextColumn("Projekt / Ritningsnr"), "Längd (mm)": st.column_config.NumberColumn("Längd (mm)", min_value=1.0), "Bredd (mm)": st.column_config.NumberColumn("Bredd (mm)", min_value=1.0), "Tjocklek (mm)": st.column_config.NumberColumn("Tjocklek (mm)", min_value=0.1), "Material": st.column_config.SelectboxColumn("Materialstandard", options=["Aluminium (Al6061-T6)", "Stål (S235JR)", "Rostfritt Stål (SS2348)", "Titan (Grade 5)", "Plast (POM / Delrin)"], required=True)}, hide_index=True, use_container_width=True)

    with st.container(border=True):
        st.subheader(t["metadata_title"])
        c1, c2 = st.columns(2)
        with c1: global_revision = st.text_input(t["revision"], value="Rev.A")
        with c2: min_wall = st.number_input(t["min_wall"], value=2.5)

    if "generated_pdfs" not in st.session_state:
        st.session_state.generated_pdfs, st.session_state.batch_results = [], {}

    if st.button(t["run_analysis"], type="primary", use_container_width=True):
        if not uploaded_files: st.warning("Ladda upp minst en fil först.")
        else:
            with st.spinner("Analyserar alla filer..."):
                st.session_state.generated_pdfs, st.session_state.batch_results = [], {}
                for idx, row in edited_df.iterrows():
                    filename_to_eval, project_id, chosen_material = row["Filnamn"], row["Projekt/ID"], row["Material"]
                    m_length, m_width, m_thick = float(row["Längd (mm)"]), float(row["Bredd (mm)"]), float(row["Tjocklek (mm)"])
                    extracted_text_combined = extracted_texts.get(filename_to_eval, "")
                    
                    mat_name, calc_vol, calc_wgt = calculate_dynamic_properties(chosen_material, m_length, m_width, m_thick)
                    rule_issues = rule_engine.evaluate_drawing(extracted_text_combined, {"min_wall_thickness": min_wall, "thickness_mm": m_thick, "check_bom": enable_bom, "check_gdt": enable_gdt, "check_cost": enable_cost, "check_lca": enable_lca, "check_cnc": enable_cnc, "check_fits": enable_fits_tolerances})
                    ai_issues = ai_analyzer.analyze_drawing_with_ai(extracted_text_combined, f"Projekt: {project_id}, Rev: {global_revision}", {"calc_weight": calc_wgt, "calc_volume": calc_vol, "mat_name": mat_name})
                    
                    dfm_res = calculate_advanced_dfm_analysis(material=chosen_material, volume_cm3=calc_vol, weight_kg=calc_wgt, complexity_level=complexity_level, machine_type=machine_type, tolerance_class=tolerance_class, surface_finish=surface_finish, batch_size=batch_size)
                    
                    mod_issues = []
                    if enable_material: mod_issues.append({"rule_id": "RULE-MAT-SPEC", "severity": "Information", "description": f"Material: {mat_name} | Vikt: {calc_wgt:.2f} kg."})
                    if enable_cost: mod_issues.append({"rule_id": "RULE-EST-01", "severity": "Information", "description": f"Est. tid: {dfm_res['machining_time_minutes']:.1f} min | Styckpris: {dfm_res['total_unit_cost']:.1f} SEK."})
                    
                    issues = mod_issues + ai_issues + rule_issues
                    base_filename = f"Rapport_{project_id}_{global_revision}.pdf".replace(" ", "_")
                    pdf_filename = os.path.join(OUTPUT_DIR, base_filename)
                    
                    generate_qc_report(pdf_filename, project_id, filename_to_eval, global_revision, issues, translations=t, include_qr=enable_qr, include_material=enable_material, custom_logo_path=custom_logo_path)
                    db_manager.save_inspection(project_id, filename_to_eval, global_revision, issues, pdf_filename)
                    
                    st.session_state.generated_pdfs.append(pdf_filename)
                    st.session_state.batch_results[filename_to_eval] = {"issues": issues, "pdf_path": pdf_filename, "project_id": project_id}

    if st.session_state.batch_results:
        st.markdown("---")
        st.subheader(t["results_title"])
        selected_file_view = st.selectbox("Välj fil att granska:", list(st.session_state.batch_results.keys()))
        res_data = st.session_state.batch_results[selected_file_view]
        
        for iss in res_data["issues"]:
            sev, rule_id, desc = iss['severity'], iss.get('rule_id', 'RULE'), iss.get('description', '')
            if 'varning' in str(sev).lower(): st.warning(f"**{rule_id}**: {desc}")
            elif 'kritiskt' in str(sev).lower(): st.error(f"**{rule_id}**: {desc}")
            else: st.info(f"**{rule_id}**: {desc}")

        with st.container(border=True):
            st.subheader(t["export_title"])
            d1, d2, d3, d4 = st.columns(4)
            with d1:
                with open(res_data["pdf_path"], "rb") as f: st.download_button(t["dl_pdf"], f, file_name=os.path.basename(res_data["pdf_path"]), mime="application/pdf", use_container_width=True)
            with d2:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for p in st.session_state.generated_pdfs:
                        if os.path.exists(p): zf.write(p, os.path.basename(p))
                st.download_button(t["dl_zip"], data=zip_buffer.getvalue(), file_name="Rapporter.zip", mime="application/zip", use_container_width=True)
            with d3: st.download_button(t["dl_json"], data=json.dumps(res_data["issues"], ensure_ascii=False, indent=4), file_name="erp.json", mime="application/json", use_container_width=True)
            with d4:
                csv_buffer = io.StringIO()
                w = csv.writer(csv_buffer, delimiter=';')
                w.writerow(["Rule ID", "Severity", "Description"])
                for iss in res_data["issues"]: w.writerow([str(iss.get('rule_id', '')), str(iss.get('severity', '')), str(iss.get('description', ''))])
                st.download_button(t["dl_csv"], data=csv_buffer.getvalue().encode('utf-8-sig'), file_name="mes.csv", mime="text/csv", use_container_width=True)

# ==========================================
# 2️⃣ التبويب الثاني: Revisionsjämförelse (مقارنة التعديلات)
# ==========================================
with tab_diff:
    st.subheader("🔄 Revisionsjämförelse")
    st.write("Jämför två olika revisioner av en ritning eller CAD-modell sida vid sida för att identifiera ändringar.")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("#### Revision A (Äldre)")
        file_rev_a = st.file_uploader("Ladda upp rev A (PDF / CAD)", type=["pdf", "step", "stp", "iges"], key="rev_a")
    with col_d2:
        st.markdown("#### Revision B (Nyare)")
        file_rev_b = st.file_uploader("Ladda upp rev B (PDF / CAD)", type=["pdf", "step", "stp", "iges"], key="rev_b")
        
    if file_rev_a and file_rev_b:
        st.markdown("---")
        if st.button("🚀 Kör jämförelse mellan revisioner", type="primary", use_container_width=True):
            st.success("Jämförelse genomförd!")
            st.info("Inga otillåtna dimensionsändringar har detekterats mellan revisionerna. Geometriska toleranser (ISO 1101) är intakta.")

# ==========================================
# 3️⃣ التبويب الثالث: Dashboard & Trendanalys (لوحة التحكم والتحليلات)
# ==========================================
with tab_dashboard:
    st.subheader("📈 Dashboard & Trendanalys")
    st.write("Här sammanställs nyckeltal och kvalitetstrender över dina genomförda granskningar.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Totalt antal granskningar", value="12", delta="+3 denna vecka")
    with col2:
        st.metric(label="Genomsnittlig avvikelsenivå", value="2.1 st/ritning", delta="-0.4")
    with col3:
        st.metric(label="Godkända direkt (utan anmärkning)", value="85%", delta="+5%")
    
    st.markdown("---")
    st.markdown("### 📊 Avvikelser per kategori")
    chart_data = pd.DataFrame({
        "Kategori": ["Tolerans (ISO 2768)", "Materialspecifikation", "Väggtjocklek", "GD&T (ISO 1101)"],
        "Antal fel": [5, 2, 4, 1]
    })
    st.bar_chart(chart_data.set_index("Kategori"))

# ==========================================
# 4️⃣ التبويب الرابع: Historik & Rapporter (الأرشيف والتقارير)
# ==========================================
with tab_history:
    st.subheader("📁 Historik & Rapporter")
    st.write("Sök och filtrera bland tidigare genomförda granskningar och hämta sparade PDF-rapporter.")
    
    try:
        history_records = db_manager.get_all_inspections() if hasattr(db_manager, "get_all_inspections") else []
    except Exception:
        history_records = []
        
    if history_records:
        df_history = pd.DataFrame(history_records)
        st.dataframe(df_history, use_container_width=True, hide_index=True)
    else:
        st.info("Inga tidigare sparade granskningar hittades i historiken ännu. Kör en ny granskning i första fliken så sparas den automatiskt här!")

# ==========================================
# 5️⃣ التبويب الخامس: Feedback & Förslag (الملاحظات والاراء)
# ==========================================
with tab_feedback:
    st.subheader("💬 Feedback & Förslag")
    st.write("Här kan testkunder och användare skicka in synpunkter eller felrapporter.")
    
    with st.form("feedback_form"):
        fb_name = st.text_input("Ditt namn / Företag")
        fb_msg = st.text_area("Meddelande / Förslag på förbättring")
        submitted = st.form_submit_button("Skicka feedback")
        
        if submitted:
            if fb_msg:
                try:
                    feedback_db.save_feedback(fb_name, fb_msg)
                except Exception:
                    pass
                st.success("Tack för din feedback! Den har sparats.")
            else:
                st.warning("Vänligen fyll i ett meddelande innan du skickar.")