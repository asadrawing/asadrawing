# app.py

import fitz  # PyMuPDF
import streamlit as st
import os
import csv
import io
import re
import smtplib
import zipfile
import json
import pandas as pd
import sqlite3
from datetime import datetime
from PIL import Image, ImageChops, ImageEnhance
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ReportLab för PDF-broschyr
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

# Sidkonfiguration
st.set_page_config(
    page_title="asaDrawing.se - Professional QC & DFM", 
    page_icon="📐", 
    layout="wide",
    initial_sidebar_state="expanded"
)

db_manager = DrawingHistoryManager()
rule_engine = DrawingRuleEngine()
feedback_db = FeedbackManager()
auth_db = AuthManager()

OUTPUT_DIR = "rapport"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("temp_uploads", exist_ok=True)

# Session State för inloggning
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_info = None

# --- INLOGGNINGSSKÄRM ---
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

# --- NÄR ANVÄNDAREN ÄR INLOGGAD ---
user_role = st.session_state.user_info["role"]
user_name = st.session_state.user_info["full_name"]

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

# Funktion för att generera produktbroschyr PDF
def create_product_brochure_pdf():
    filename = "asaDrawing_Produktbroschyr.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=45)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor('#0F172A'))
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Heading2'], fontSize=11, leading=15, textColor=colors.HexColor('#0284C7'))
    h2_style = ParagraphStyle('H2Style', parent=styles['Heading2'], fontSize=11, leading=15, textColor=colors.HexColor('#1E293B'))
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#334155'))
    bullet_style = ParagraphStyle('BulletStyle', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor('#334155'), leftIndent=10)

    story = []
    story.append(Paragraph("<b>asaDrawing.se — Industriell Plattform för QC &amp; DFM</b>", title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("<b>Komplett funktionskatalog och teknisk specifikation för tillverkningsindustrin</b>", subtitle_style))
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#0EA5E9'), spaceAfter=10))

    intro_text = (
        "<b>asaDrawing.se</b> är en molnbaserad enterprise-plattform som automatiserar granskning av 2D-ritningar (PDF) "
        "och 3D-CAD-filer (STEP, IGES, STL). Systemet kombinerar regelmotorer, artificiell intelligens (OpenAI) och "
        "avancerade DFM-beräkningar (Design for Manufacturing) för att minska felaktigheter, korta ner beredningstider "
        "och effektivisera kommunikationen mellan konstruktion, inköp och produktion."
    )
    story.append(Paragraph(intro_text, normal_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>1. Aktiva Moduler &amp; Analysfunktioner</b>", h2_style))
    story.append(Spacer(1, 4))
    
    modules_data = [
        [Paragraph("<b>Modul</b>", normal_style), Paragraph("<b>Beskrivning &amp; Funktionsomfång</b>", normal_style)],
        [Paragraph("<b>Stycklista (BOM)</b>", normal_style), Paragraph("Detekterar och verifierar strukturerade komponentlistor och materialkrav.", normal_style)],
        [Paragraph("<b>GD&amp;T &amp; Toleranser</b>", normal_style), Paragraph("Analyserar form- och lägestoleranser enligt ISO 1101 samt allmänna toleranser (ISO 2768).", normal_style)],
        [Paragraph("<b>Kostnad &amp; Tid (DFM)</b>", normal_style), Paragraph("Beräknar maskintid, styckpriser baserat på seriestorlek och komplexitet (3-, 4-, 5-axlig CNC).", normal_style)],
        [Paragraph("<b>Hållbarhet &amp; LCA</b>", normal_style), Paragraph("Uppskattar koldioxidavtryck (CO2e) baserat på vald materialstandard och volym.", normal_style)],
        [Paragraph("<b>Material &amp; Vikt</b>", normal_style), Paragraph("Exakt beräkning av volym och massa för Aluminium, Stål, Rostfritt, Titan och Plast.", normal_style)],
        [Paragraph("<b>Digital QR-Spårbarhet</b>", normal_style), Paragraph("Genererar unika QR-koder på rapporter för direkt verifiering och spårbarhet i produktionen.", normal_style)]
    ]
    
    mod_table = Table(modules_data, colWidths=[130, 390])
    mod_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(mod_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("<b>2. Plattformens Huvudvyer &amp; Workflow</b>", h2_style))
    story.append(Spacer(1, 4))

    features = [
        "<b>Ny Granskning (Batch-analys):</b> Ladda upp flera PDF- eller 3D-filer samtidigt. Justera individuella parametrar (längd, bredd, tjocklek, material) i en interaktiv tabell och generera skräddarsydda QC-rapporter i PDF-format.",
        "<b>Revisionsjämförelse (Sida-vid-sida &amp; Färgkodad Diff):</b> Jämför två revisioner av en ritning visuellt och textuellt. Identifiera tillagda (grönt) och borttagna (rött) element direkt utan överlappande röriga vyer.",
        "<b>Dashboard &amp; Trendanalys:</b> Följ upp kvalitetstrender över tid via KPI-kort, stapeldiagram över avvikelsenivåer (Kritiska, Varningar, Godkända) och sammanställning av de vanligaste regelbrotten.",
        "<b>Historik &amp; Rapportarkiv:</b> Sökbar och filtrerbar tabell över alla tidigare granskningar med direkt nedladdning av genererade PDF-rapporter och statusindikeringar.",
        "<b>Rollbaserad Behörighet &amp; Godkännande:</b> Strikta roller för Admin, Kvalitetschef, Beredare och Inköp. Endast behöriga roller kan göra formella slutgodkännanden av upptäckta avvikelser.",
        "<b>ERP/MES &amp; E-postexport:</b> Exportera granskningsresultat direkt till JSON (ERP-system) eller CSV (MES-system). Skicka färdiga rapporter via inbyggd SMTP-klient med e-post."
    ]

    for f in features:
        story.append(Paragraph(f"• {f}", bullet_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>3. Kundnytta &amp; ROI för Verkstäder</b>", h2_style))
    story.append(Spacer(1, 4))
    
    benefit_text = (
        "Genom att implementera asaDrawing.se elimineras manuella flaskhalsar vid ritningsgranskning. "
        "Företag sparar upp till 80 % av tiden som läggs på offertberedning och DFM-analys, samtidigt som "
        "reklamationer på grund av otydliga toleranser eller saknade mått förhindras innan detaljen går till produktion."
    )
    story.append(Paragraph(benefit_text, normal_style))
    story.append(Spacer(1, 10))

    doc.build(story)
    return filename

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
    st.markdown("### 📄 Produktbroschyr (PDF)")
    if st.button("Generera & Ladda ner Broschyr", use_container_width=True):
        try:
            pdf_path = create_product_brochure_pdf()
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="📥 Ladda ner Produktbroschyr",
                        data=f,
                        file_name="asaDrawing_Produktbroschyr.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        except Exception as e:
            st.error(f"Kunde inte generera broschyr: {str(e)}")

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
        enable_bom = False
        enable_gdt = False
        enable_cost = True
        enable_lca = True
        enable_cnc = False
        enable_material = True
        enable_fits_tolerances = False
        enable_qr = False
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
        except Exception:
            default_key = ""
            
        openai_api_key = st.text_input("OpenAI API-nyckel", value=default_key, type="password")
        smtp_server = st.text_input("SMTP-server", value="smtp.gmail.com")
        smtp_port = st.number_input("SMTP-port", value=587, step=1)
        sender_email = st.text_input("Avsändare e-post", value="")
        sender_password = st.text_input("App-lösenord", value="", type="password")

lang_clean = selected_lang.split(" ")[1] if " " in selected_lang else selected_lang
ai_analyzer = DrawingAIAnalyzer(api_key=openai_api_key, lang=lang_clean)

# HUVUDLAYOUT
st.title(t["title"])
st.markdown(t["subtitle"])

tab_review, tab_diff, tab_dashboard, tab_history, tab_feedback = st.tabs([
    t["tab_review"], 
    t["tab_diff"], 
    t["tab_dashboard"], 
    t["tab_history"],
    t["tab_feedback"]
])

@st.cache_data(show_spinner=False)
def load_and_extract_pdf_fast(uploaded_file_bytes):
    doc = fitz.open(stream=uploaded_file_bytes, filetype="pdf")
    pdf_text = ""
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        if text: pdf_text += text + "\n"
    return pdf_text

def calculate_dynamic_properties(chosen_mat, length, width, thickness):
    densities = {
        "Aluminium (Al6061-T6)": 2.70, "Stål (S235JR)": 7.85,
        "Rostfritt Stål (SS2348)": 8.00, "Titan (Grade 5)": 4.51, "Plast (POM / Delrin)": 1.41
    }
    density = densities.get(chosen_mat, 2.70)
    volume_cm3 = (length * width * thickness) / 1000.0
    weight_kg = (volume_cm3 * density) / 1000.0
    return chosen_mat, volume_cm3, weight_kg

with tab_review:
    with st.container(border=True):
        st.subheader(t["upload_title"])
        uploaded_files = st.file_uploader(t["upload_label"], type=["pdf", "step", "stp", "iges", "igs", "stl"], accept_multiple_files=True)
    
    file_params_data = []
    extracted_texts = {}
    file_metadata_cache = {}
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_ext = uploaded_file.name.split('.')[-1].lower()
            
            if file_ext in ["step", "stp", "iges", "igs", "stl"]:
                temp_path = os.path.join("temp_uploads", uploaded_file.name)
                try:
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    cad_res = analyze_3d_file(temp_path)
                    if cad_res.get("success"):
                        extracted_texts[uploaded_file.name] = f"3D CAD Geometry parsed. Volume: {cad_res['volume_cm3']} cm3, Extents: {cad_res['length']}x{cad_res['width']}x{cad_res['thickness']} mm."
                        file_metadata_cache[uploaded_file.name] = {
                            "is_3d": True,
                            "length": cad_res["length"],
                            "width": cad_res["width"],
                            "thickness": cad_res["thickness"],
                            "volume_cm3": cad_res["volume_cm3"]
                        }
                        file_params_data.append({
                            "Filnamn": uploaded_file.name,
                            "Projekt/ID": uploaded_file.name.rsplit('.', 1)[0],
                            "Längd (mm)": cad_res["length"],
                            "Bredd (mm)": cad_res["width"],
                            "Tjocklek (mm)": cad_res["thickness"],
                            "Material": "Aluminium (Al6061-T6)"
                        })
                    else:
                        st.error(f"Kunde inte analysera 3D-fil {uploaded_file.name}: {cad_res.get('error')}")
                except Exception as e:
                    st.error(f"Fel vid inläsning av 3D-fil: {str(e)}")
                finally:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception:
                            pass
            else:
                try:
                    file_bytes = uploaded_file.read()
                    pdf_text = load_and_extract_pdf_fast(file_bytes)
                    extracted_texts[uploaded_file.name] = pdf_text
                    
                    match_drg = re.search(r'(?:Drawing No\.?|Drg|Ritningsnr\.?|Projekt)[:\s]+([A-Za-z0-9\-_]+)', pdf_text, re.IGNORECASE)
                    default_id = match_drg.group(1) if match_drg else uploaded_file.name.replace('.pdf', '')
                    
                    file_metadata_cache[uploaded_file.name] = {"is_3d": False}
                    file_params_data.append({
                        "Filnamn": uploaded_file.name,
                        "Projekt/ID": default_id,
                        "Längd (mm)": 120.0,
                        "Bredd (mm)": 60.0,
                        "Tjocklek (mm)": 15.0,
                        "Material": "Aluminium (Al6061-T6)"
                    })
                except Exception as e:
                    extracted_texts[uploaded_file.name] = f"Kunde inte läsa fil: {str(e)}"

        st.markdown("---")
        st.subheader(t["parameters_title"])
        
        df_params = pd.DataFrame(file_params_data)
        edited_df = st.data_editor(
            df_params,
            column_config={
                "Filnamn": st.column_config.TextColumn("Filnamn", disabled=True),
                "Projekt/ID": st.column_config.TextColumn("Projekt / Ritningsnr"),
                "Längd (mm)": st.column_config.NumberColumn("Längd (mm)", min_value=1.0, step=1.0),
                "Bredd (mm)": st.column_config.NumberColumn("Bredd (mm)", min_value=1.0, step=1.0),
                "Tjocklek (mm)": st.column_config.NumberColumn("Tjocklek (mm)", min_value=0.1, step=0.1),
                "Material": st.column_config.SelectboxColumn(
                    "Materialstandard",
                    options=["Aluminium (Al6061-T6)", "Stål (S235JR)", "Rostfritt Stål (SS2348)", "Titan (Grade 5)", "Plast (POM / Delrin)"],
                    required=True
                )
            },
            hide_index=True,
            use_container_width=True
        )

    with st.container(border=True):
        st.subheader(t["metadata_title"])
        c1, c2 = st.columns(2)
        with c1: global_revision = st.text_input(t["revision"], value="Rev.A")
        with c2: min_wall = st.number_input(t["min_wall"], value=2.5)

    if "generated_pdfs" not in st.session_state:
        st.session_state.generated_pdfs = []
        st.session_state.batch_results = {}

    if st.button(t["run_analysis"], type="primary", use_container_width=True):
        if not uploaded_files:
            st.warning("Ladda upp minst en fil först.")
        else:
            with st.spinner("Analyserar alla filer i batchen med individuella parametrar och AI..."):
                st.session_state.generated_pdfs = []
                st.session_state.batch_results = {}

                for idx, row in edited_df.iterrows():
                    filename_to_eval = row["Filnamn"]
                    project_id = row["Projekt/ID"]
                    chosen_material = row["Material"]
                    m_length = float(row["Längd (mm)"])
                    m_width = float(row["Bredd (mm)"])
                    m_thick = float(row["Tjocklek (mm)"])
                    
                    extracted_text_combined = extracted_texts.get(filename_to_eval, "")
                    
                    meta_info = file_metadata_cache.get(filename_to_eval, {})
                    if meta_info.get("is_3d") and "volume_cm3" in meta_info:
                        calc_vol = meta_info["volume_cm3"]
                        densities = {"Aluminium (Al6061-T6)": 2.70, "Stål (S235JR)": 7.85, "Rostfritt Stål (SS2348)": 8.00, "Titan (Grade 5)": 4.51, "Plast (POM / Delrin)": 1.41}
                        density = densities.get(chosen_material, 2.70)
                        calc_wgt = (calc_vol * density) / 1000.0
                        mat_name = chosen_material
                    else:
                        mat_name, calc_vol, calc_wgt = calculate_dynamic_properties(chosen_material, m_length, m_width, m_thick)

                    rule_issues = rule_engine.evaluate_drawing(extracted_text_combined, {
                        "min_wall_thickness": min_wall, 
                        "thickness_mm": m_thick,
                        "check_bom": enable_bom, 
                        "check_gdt": enable_gdt, 
                        "check_cost": enable_cost,
                        "check_lca": enable_lca,
                        "check_cnc": enable_cnc,
                        "check_fits": enable_fits_tolerances
                    })
                    
                    metadata_str = f"Projekt: {project_id}, Revision: {global_revision}, Material: {mat_name}, Mått: {m_length}x{m_width}x{m_thick} mm"
                    ai_issues = ai_analyzer.analyze_drawing_with_ai(extracted_text_combined, metadata_str, {"calc_weight": calc_wgt, "calc_volume": calc_vol, "mat_name": mat_name})
                    
                    mod_issues = []
                    
                    dfm_res = calculate_advanced_dfm_analysis(
                        material=chosen_material, 
                        volume_cm3=calc_vol, 
                        weight_kg=calc_wgt, 
                        complexity_level=complexity_level, 
                        machine_type=machine_type, 
                        tolerance_class=tolerance_class, 
                        surface_finish=surface_finish, 
                        batch_size=batch_size
                    )

                    if enable_material:
                        mod_issues.append({
                            "rule_id": "RULE-MAT-SPEC", 
                            "severity": "Information", 
                            "description": f"Material: {mat_name} | Vikt: {calc_wgt:.2f} kg | Volym: {calc_vol:.1f} cm3."
                        })
                    
                    if enable_cost:
                        mod_issues.append({
                            "rule_id": "RULE-EST-01", 
                            "severity": "Information", 
                            "description": f"Maskin: {machine_type} | Est. tid: {dfm_res['machining_time_minutes']:.1f} min | Styckpris (batch {batch_size}st): {dfm_res['total_unit_cost']:.1f} SEK."
                        })
                    
                    if enable_lca:
                        mod_issues.append({
                            "rule_id": "RULE-LCA-01", 
                            "severity": "Information", 
                            "description": f"CO2e-avtryck ca {dfm_res['co2_emissions_kg']:.2f} kg."
                        })

                    issues = mod_issues + ai_issues + rule_issues
                    base_filename = f"Rapport_{project_id}_{filename_to_eval.rsplit('.', 1)[0]}_{global_revision}.pdf".replace(" ", "_")
                    pdf_filename = os.path.join(OUTPUT_DIR, base_filename)
                    
                    generate_qc_report(
                        pdf_filename, 
                        project_id, 
                        filename_to_eval, 
                        global_revision, 
                        issues, 
                        translations=t, 
                        include_qr=enable_qr, 
                        include_material=enable_material,
                        custom_logo_path=custom_logo_path
                    )
                    db_manager.save_inspection(project_id, filename_to_eval, global_revision, issues, pdf_filename)
                    
                    st.session_state.generated_pdfs.append(pdf_filename)
                    st.session_state.batch_results[filename_to_eval] = {
                        "issues": issues,
                        "pdf_path": pdf_filename,
                        "project_id": project_id
                    }

    if st.session_state.batch_results:
        st.markdown("---")
        st.subheader(t["results_title"])
        selected_file_view = st.selectbox("Välj fil att granska:", list(st.session_state.batch_results.keys()))
        res_data = st.session_state.batch_results[selected_file_view]
        file_issues = res_data["issues"]
        
        for iss in file_issues:
            sev = iss['severity']
            rule_id = iss.get('rule_id', 'RULE')
            desc = iss.get('description', '')
            if 'varning' in str(sev).lower() or 'warning' in str(sev).lower(): st.warning(f"**{rule_id}**: {desc}")
            elif 'information' in str(sev).lower(): st.info(f"**{rule_id}**: {desc}")
            elif 'kritiskt' in str(sev).lower() or 'critical' in str(sev).lower(): st.error(f"**{rule_id}**: {desc}")
            else: st.success(f"**{rule_id}**: {desc}")

        # --- BEHÖRIGHETSKONTROLL FÖR ATT GODKÄNNA AVVIKELSER ---
        st.markdown("---")
        st.markdown("#### 🔐 Formellt godkännande av avvikelser")
        
        if user_role in ["Admin", "Kvalitetschef"]:
            col_app1, col_app2 = st.columns(2)
            with col_app1:
                approval_note = st.text_input("Kommentar till godkännande", placeholder="Ange orsak vid avvikelsegodkännande...", key=f"note_{selected_file_view}")
            with col_app2:
                if st.button("✅ Slutgodkänn avvikelser för denna ritning", key=f"btn_app_{selected_file_view}", use_container_width=True):
                    st.success(f"Avvikelserna för {selected_file_view} har formellt godkänts av {user_name} ({user_role}).")
        else:
            st.info(f"🔒 Din roll (`{user_role}`) har behörighet att granska och exportera, men endast **Admin** eller **Kvalitetschef** kan göra ett formellt slutgodkännande av avvikelser.")

        with st.container(border=True):
            st.subheader(t["export_title"])
            d1, d2, d3, d4 = st.columns(4)
            with d1:
                with open(res_data["pdf_path"], "rb") as f:
                    st.download_button(t["dl_pdf"], f, file_name=os.path.basename(res_data["pdf_path"]), mime="application/pdf", use_container_width=True)
            with d2:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    for pdf_path in st.session_state.generated_pdfs:
                        if os.path.exists(pdf_path):
                            zip_file.write(pdf_path, os.path.basename(pdf_path))
                st.download_button(t["dl_zip"], data=zip_buffer.getvalue(), file_name=f"QC_Rapporter_{global_revision}.zip", mime="application/zip", use_container_width=True)
            with d3:
                st.download_button(t["dl_json"], data=json.dumps(file_issues, ensure_ascii=False, indent=4), file_name="erp_export.json", mime="application/json", use_container_width=True)
            with d4:
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer, delimiter=';')
                writer.writerow(["Rule ID", "Severity", "Description"])
                for iss in file_issues:
                    writer.writerow([str(iss.get('rule_id', '')), str(iss.get('severity', '')), str(iss.get('description', ''))])
                st.download_button(t["dl_csv"], data=csv_buffer.getvalue().encode('utf-8-sig'), file_name="mes_export.csv", mime="text/csv", use_container_width=True)

            st.markdown("---")
            st.markdown("#### 📧 Skicka rapport via e-post")
            recipient_email = st.text_input("Mottagare e-postadress", value="", placeholder="exempel@foretag.se")
            
            if st.button("Skicka e-post med vald PDF-rapport"):
                if not sender_email or not sender_password or not recipient_email:
                    st.error("Vänligen fyll i avsändarens e-post, app-lösenord i sidofältet och mottagarens e-post här.")
                else:
                    try:
                        msg = MIMEMultipart()
                        msg['From'] = sender_email
                        msg['To'] = recipient_email
                        msg['Subject'] = f"QC Rapport - Granskning ({selected_file_view})"

                        body = f"Hej,\n\nBifogat finner du QC-rapporten för {selected_file_view}.\n\nVänliga hälsningar,\n{user_name}"
                        msg.attach(MIMEText(body, 'plain'))

                        with open(res_data["pdf_path"], "rb") as attachment:
                            part = MIMEApplication(attachment.read(), Name=os.path.basename(res_data["pdf_path"]))
                            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(res_data["pdf_path"])}"'
                            msg.attach(part)

                        with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                            server.starttls()
                            server.login(sender_email, sender_password)
                            server.send_message(msg)
                        
                        st.success(f"E-post skickad framgångsrikt till {recipient_email}!")
                    except Exception as e:
                        st.error(f"Ett fel uppstod vid skickande av e-post: {str(e)}")

# TAB: DASHBOARD & TRENDANALYS (FÖRBÄTTRAD ENTERPRISE-VY)
with tab_dashboard:
    st.subheader("📈 Historik & Trendanalys (Dashboard)")
    st.caption("Följ upp kvalitetstrender, vanligaste avvikelser och kostnadsutveckling över tid baserat på sparade inspektioner.")

    history_rows = db_manager.get_all_inspections()
    
    if history_rows:
        dashboard_data = []
        all_historical_issues = []
        
        for row in history_rows:
            insp_id, proj_id, drg_name, rev, timestamp, issues_raw, pdf_rep, comp, notes = row
            
            if isinstance(issues_raw, str):
                try:
                    issues_list = json.loads(issues_raw) if issues_raw else []
                except Exception:
                    issues_list = []
            elif isinstance(issues_raw, list):
                issues_list = issues_raw
            else:
                issues_list = []
            
            crit_c = sum(1 for i in issues_list if 'kritiskt' in str(i.get('severity','')).lower() or 'critical' in str(i.get('severity','')).lower())
            warn_c = sum(1 for i in issues_list if 'varning' in str(i.get('severity','')).lower() or 'warning' in str(i.get('severity','')).lower())
            ok_c = sum(1 for i in issues_list if 'godkänd' in str(i.get('severity','')).lower() or 'approved' in str(i.get('severity','')).lower() or 'information' in str(i.get('severity','')).lower())
            
            dashboard_data.append({
                "Tidstämpel": str(timestamp)[:16],
                "Datum": str(timestamp)[:10],
                "Projekt": proj_id,
                "Ritning": drg_name,
                "Revision": rev,
                "Kritiska": crit_c,
                "Varningar": warn_c,
                "Godkända/Info": ok_c,
                "Totalt fel": len(issues_list)
            })
            all_historical_issues.extend(issues_list)

        df_hist = pd.DataFrame(dashboard_data)

        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        col_kpi1.metric("Totalt antal granskningar", len(df_hist))
        col_kpi2.metric("Snitt kritiska / granskning", f"{df_hist['Kritiska'].mean():.1f}")
        col_kpi3.metric("Snitt varningar / granskning", f"{df_hist['Varningar'].mean():.1f}")
        col_kpi4.metric("Unika projekt", df_hist['Projekt'].nunique())

        st.markdown("---")

        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            st.markdown("#### 📅 Kvalitetsutveckling per granskning")
            if df_hist['Datum'].nunique() <= 1:
                df_chart = df_hist.set_index("Tidstämpel")[["Kritiska", "Varningar"]]
            else:
                df_chart = df_hist.groupby("Datum")[["Kritiska", "Varningar"]].sum()
            
            st.bar_chart(df_chart)

        with col_d2:
            st.markdown("#### 📊 Fördelning av avvikelsenivåer")
            tot_crit = df_hist['Kritiska'].sum()
            tot_warn = df_hist['Varningar'].sum()
            tot_ok = df_hist['Godkända/Info'].sum()
            
            df_sev_summary = pd.DataFrame({
                "Nivå": ["Kritiska", "Varningar", "Godkända / Info"],
                "Antal": [tot_crit, tot_warn, tot_ok]
            }).set_index("Nivå")
            
            st.bar_chart(df_sev_summary)

        st.markdown("---")

        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.markdown("#### 🚨 Vanligaste regelavvikelserna")
            rule_counter = {}
            for iss in all_historical_issues:
                r_id = iss.get('rule_id', 'Okänd')
                if r_id not in ['RULE-MAT-SPEC', 'RULE-EST-01', 'RULE-LCA-01']:
                    rule_counter[r_id] = rule_counter.get(r_id, 0) + 1
            
            if rule_counter:
                df_rules = pd.DataFrame(list(rule_counter.items()), columns=["Regel-ID", "Antal förekomster"])
                df_rules = df_rules.sort_values(by="Antal förekomster", ascending=False)
                st.dataframe(df_rules, hide_index=True, use_container_width=True)
            else:
                st.info("Inga regeldata tillgängliga.")

        with col_t2:
            st.markdown("#### 📋 Detaljerad historiköversikt")
            st.dataframe(df_hist[["Tidstämpel", "Projekt", "Ritning", "Kritiska", "Varningar"]], hide_index=True, use_container_width=True)

    else:
        st.info("Inga sparade granskningar hittades i historikdatabasen ännu. Kör några analyser i fliken 'Ny Granskning' för att fylla på trendanalysen!")

# TAB: REVISIONSJÄMFÖRELSE (FÄRGKODAD DIFF & SIDA-VID-SIDA)
with tab_diff:
    st.subheader("🔄 Revisionsjämförelse mellan ritningar")
    st.caption("Jämför två revisioner sida vid sida samt identifiera ändringar med färgmarkering.")

    col_a, col_b = st.columns(2)
    with col_a: 
        file_rev_a = st.file_uploader("Ritning Revision A", type=["pdf"], key="rev_a")
    with col_b: 
        file_rev_b = st.file_uploader("Ritning Revision B", type=["pdf"], key="rev_b")

    if file_rev_a and file_rev_b:
        bytes_a = file_rev_a.read()
        bytes_b = file_rev_b.read()
        
        if st.button("🚀 Kör Revisionsjämförelse", type="primary", use_container_width=True):
            tab_vis, tab_txt = st.tabs(["🖼️ Visuell Jämförelse & Overlay", "📊 Text- & Måttskillnader"])
            
            # --- 1. VISUELL JÄMFÖRELSE ---
            with tab_vis:
                try:
                    doc_a = fitz.open(stream=bytes_a, filetype="pdf")
                    doc_b = fitz.open(stream=bytes_b, filetype="pdf")
                    
                    pix_a = doc_a[0].get_pixmap(dpi=150)
                    pix_b = doc_b[0].get_pixmap(dpi=150)
                    
                    img_a = Image.frombytes("RGB", [pix_a.width, pix_a.height], pix_a.samples).convert("L")
                    img_b = Image.frombytes("RGB", [pix_b.width, pix_b.height], pix_b.samples).convert("L")
                    
                    if img_a.size != img_b.size:
                        img_b = img_b.resize(img_a.size)
                    
                    diff_rgb = Image.merge("RGB", (img_a, img_b, img_b))
                    
                    st.markdown("### 👁️ Jämförelse sida vid sida")
                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        st.markdown("**📄 Revision A**")
                        st.image(img_a, use_container_width=True)
                    with col_v2:
                        st.markdown("**📄 Revision B**")
                        st.image(img_b, use_container_width=True)
                        
                    st.markdown("---")
                    st.markdown("### 🔴🟢 Färgkodad avvikelsekarta (Diff)")
                    st.caption("🔴 **Rött/Rosa:** Detaljer från Rev A som saknas eller ändrats. | 🟢 **Grönt:** Nya detaljer i Rev B.")
                    st.image(diff_rgb, use_container_width=True)

                except Exception as e:
                    st.error(f"Kunde inte generera visuell jämförelse: {str(e)}")

            # --- 2. TEXT- OCH MÅTTSKILLNADER ---
            with tab_txt:
                txt_a = load_and_extract_pdf_fast(bytes_a).splitlines()
                txt_b = load_and_extract_pdf_fast(bytes_b).splitlines()
                
                added = [line.strip() for line in txt_b if line.strip() and line not in txt_a]
                removed = [line.strip() for line in txt_a if line.strip() and line not in txt_b]
                
                c_add, c_rem = st.columns(2)
                
                with c_add:
                    st.markdown("#### 🟢 Tillagt / Ändrat i Revision B")
                    if added:
                        for item in added:
                            st.success(f"+ {item}")
                    else:
                        st.info("Inga nya textrader tillagda.")
                        
                with c_rem:
                    st.markdown("#### 🔴 Borttaget från Revision A")
                    if removed:
                        for item in removed:
                            st.error(f"- {item}")
                    else:
                        st.info("Inga textrader borttagna.")

# TAB: HISTORIK & RAPPORTER (FÖRBÄTTRAD TABELL-VY)
with tab_history:
    st.subheader("📁 Tidigare granskningsrapporter & Arkiv")
    st.caption("Sök, filtrera och ladda ner tidigare genererade QC-rapporter direkt från systemet.")

    history_rows = db_manager.get_all_inspections()
    
    if history_rows:
        table_data = []
        pdf_file_map = {}
        
        for row in history_rows:
            insp_id, proj_id, drg_name, rev, timestamp, issues_raw, pdf_rep, comp, notes = row
            
            if isinstance(issues_raw, str):
                try:
                    issues_list = json.loads(issues_raw) if issues_raw else []
                except Exception:
                    issues_list = []
            elif isinstance(issues_raw, list):
                issues_list = issues_raw
            else:
                issues_list = []
                
            crit_c = sum(1 for i in issues_list if 'kritiskt' in str(i.get('severity','')).lower() or 'critical' in str(i.get('severity','')).lower())
            status_text = "⚠️ Godkänd med anmärkning" if crit_c > 0 else "✅ Godkänd"
            
            filename = os.path.basename(pdf_rep) if pdf_rep else f"Rapport_{proj_id}_{drg_name}.pdf"
            pdf_file_map[filename] = pdf_rep
            
            table_data.append({
                "Datum": str(timestamp)[:16],
                "Projekt-ID": proj_id,
                "Ritning": drg_name,
                "Revision": rev,
                "Status": status_text,
                "Filnamn": filename
            })
            
        df_history_view = pd.DataFrame(table_data)
        
        search_query = st.text_input("🔍 Sök i historik (Projekt-ID eller Ritning):", "")
        if search_query:
            df_history_view = df_history_view[
                df_history_view['Projekt-ID'].str.contains(search_query, case=False, na=False) |
                df_history_view['Ritning'].str.contains(search_query, case=False, na=False)
            ]
            
        st.dataframe(
            df_history_view,
            column_config={
                "Filnamn": st.column_config.TextColumn("Rapportfil"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("#### 📥 Ladda ner specifik rapport")
        selected_report_file = st.selectbox("Välj rapport att ladda ner:", list(pdf_file_map.keys()))
        
        if selected_report_file:
            target_path = pdf_file_map[selected_report_file]
            if target_path and os.path.exists(target_path):
                with open(target_path, "rb") as pdf_file:
                    st.download_button(
                        label=f"📥 Ladda ner {selected_report_file}",
                        data=pdf_file,
                        file_name=selected_report_file,
                        mime="application/pdf",
                        use_container_width=True
                    )
            else:
                st.warning("Den valda PDF-filen kunde inte hittas på disken.")
                
    else:
        st.info("Inga sparade granskningar eller rapporter hittades i historikdatabasen ännu.")

# TAB: FEEDBACK & FÖRSLAG
with tab_feedback:
    st.subheader("💬 Lämna feedback")
    with st.form("feedback_form", clear_on_submit=True):
        fb_rating = st.slider("Betyg (1-5)", 1, 5, 5)
        fb_category = st.selectbox("Kategori", ["Allmänt", "Bugg", "Funktionsförslag"])
        fb_comment = st.text_area("Kommentar")
        if st.form_submit_button("Skicka"):
            feedback_db.save_feedback(user_name, fb_rating, fb_category, fb_comment)
            st.success("Tack för din feedback!")

    # --- ADMIN-VY FÖR ATT LÄSA FEEDBACK ---
    st.markdown("---")
    st.markdown("### 📥 Inkommen feedback (Administratörsmeny)")

    if user_role in ["Admin", "Kvalitetschef"]:
        try:
            conn = sqlite3.connect("feedback_history.db")
            df_fb = pd.read_sql_query("SELECT * FROM feedback ORDER BY id DESC", conn)
            conn.close()
            
            if not df_fb.empty:
                st.dataframe(df_fb, hide_index=True, use_container_width=True)
            else:
                st.info("Ingen feedback har skickats in ännu.")
        except Exception:
            st.info("Ingen feedback-databas hittad än.")
    else:
        st.info(f"🔒 Endast **Admin** och **Kvalitetschef** kan se sammanställningen av inkommen feedback.")