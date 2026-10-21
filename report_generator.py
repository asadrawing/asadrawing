# report_generator.py

import os
import html
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import qrcode

def clean_text_for_pdf(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.replace('■', '').replace('▪', '').replace('•', '')
    return html.escape(text.strip())

def add_header_footer(canvas, doc, project_id, drawing_name, revision):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor('#64748B'))
    canvas.drawString(36, 25, "asaDrawing.se - QC Report & Traceability")
    page_num = canvas.getPageNumber()
    canvas.drawRightString(A4[0] - 36, 25, f"Page {page_num}")
    canvas.restoreState()

def generate_qc_report(pdf_filename, project_id, drawing_name, revision, issues, translations=None, include_qr=True, include_material=True, custom_logo_path=None):
    if translations is None: t = {}
    else: t = translations

    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=15, leading=18, textColor=colors.HexColor('#0F172A'))
    heading2_style = ParagraphStyle('Heading2', parent=styles['Heading2'], fontSize=11, leading=14, textColor=colors.HexColor('#1E293B'))
    normal_style = ParagraphStyle('ReportNormal', parent=styles['Normal'], fontSize=8.5, leading=11, textColor=colors.HexColor('#0F172A'))

    story = []

    header_data = []
    if custom_logo_path and os.path.exists(custom_logo_path):
        try:
            img = Image(custom_logo_path, width=100, height=35)
            header_data = [[img, Paragraph(f"<b>asaDrawing.se - Professionell QC-Rapport &amp; CNC-beredning</b>", title_style)]]
        except Exception:
            header_data = [[Paragraph(f"<b>asaDrawing.se - Professionell QC-Rapport &amp; CNC-beredning</b>", title_style)]]
    else:
        header_data = [[Paragraph(f"<b>asaDrawing.se - Professionell QC-Rapport &amp; CNC-beredning</b>", title_style)]]

    header_table = Table(header_data, colWidths=[110, 410] if len(header_data[0]) > 1 else [520])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (-1,-1), 'LEFT')]))
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#0EA5E9'), spaceAfter=10))

    meta_text = (
        f"<b>Projekt-ID:</b> {clean_text_for_pdf(project_id)} | "
        f"<b>Ritning:</b> {clean_text_for_pdf(drawing_name)} | "
        f"<b>Revision:</b> {clean_text_for_pdf(revision)} | "
        f"<b>Datum:</b> {datetime.now().strftime('%Y-%m-%d')}"
    )
    story.append(Paragraph(meta_text, normal_style))
    story.append(Spacer(1, 8))

    crit_count = sum(1 for i in issues if 'kritiskt' in str(i.get('severity','')).lower() or 'critical' in str(i.get('severity','')).lower())
    warn_count = sum(1 for i in issues if 'varning' in str(i.get('severity','')).lower() or 'warning' in str(i.get('severity','')).lower())
    other_count = len(issues) - crit_count - warn_count

    summary_html = (
        f"<b>Sammanfattning:</b> "
        f"<font color='#DC2626'><b>Kritiska: {crit_count}</b></font> | "
        f"<font color='#D97706'><b>Varningar: {warn_count}</b></font> | "
        f"<font color='#16A34A'><b>Godkända/Info: {other_count}</b></font>"
    )
    story.append(Paragraph(summary_html, normal_style))
    story.append(Spacer(1, 10))

    # Materialspecifikation Box
    if include_material:
        mat_issues = [i for i in issues if 'RULE-MAT-SPEC' in str(i.get('rule_id', ''))]
        if mat_issues:
            story.append(Paragraph(f"<b>Materialspecifikation &amp; Vikt</b>", heading2_style))
            story.append(Spacer(1, 3))
            mat_table_data = [[Paragraph(f"<b>Parameter</b>", normal_style), Paragraph(f"<b>Värde</b>", normal_style)]]
            for m in mat_issues:
                desc_parts = m.get('description', '').split('|')
                for part in desc_parts:
                    if ':' in part:
                        k, v = part.split(':', 1)
                        mat_table_data.append([Paragraph(k.strip(), normal_style), Paragraph(v.strip(), normal_style)])
                    else:
                        mat_table_data.append([Paragraph("Material", normal_style), Paragraph(clean_text_for_pdf(part), normal_style)])
            mat_table = Table(mat_table_data, colWidths=[140, 380])
            mat_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(mat_table)
            story.append(Spacer(1, 8))

    # Kostnads- och DFM-sammanfattningsbox
    cost_issues = [i for i in issues if 'RULE-EST-01' in str(i.get('rule_id', '')) or 'RULE-LCA-01' in str(i.get('rule_id', ''))]
    if cost_issues:
        story.append(Paragraph(f"<b>Kostnads- och Beredningssammanfattning (DFM / LCA)</b>", heading2_style))
        story.append(Spacer(1, 3))
        cost_table_data = [[Paragraph(f"<b>Nyckeltal</b>", normal_style), Paragraph(f"<b>Värde</b>", normal_style)]]
        for c in cost_issues:
            desc_parts = c.get('description', '').split('|')
            for part in desc_parts:
                if ':' in part:
                    k, v = part.split(':', 1)
                    cost_table_data.append([Paragraph(k.strip(), normal_style), Paragraph(v.strip(), normal_style)])
                else:
                    cost_table_data.append([Paragraph(c.get('rule_id', ''), normal_style), Paragraph(clean_text_for_pdf(part), normal_style)])
        cost_table = Table(cost_table_data, colWidths=[140, 380])
        cost_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(cost_table)
        story.append(Spacer(1, 10))

    # Filtrera bort metadata-regler från huvudtabellen så de inte dubbletterar
    filtered_issues = [i for i in issues if i.get('rule_id') not in ['RULE-MAT-SPEC', 'RULE-EST-01', 'RULE-LCA-01']]

    story.append(Paragraph(f"<b>Detaljerat granskningsresultat &amp; Åtgärder:</b>", heading2_style))
    story.append(Spacer(1, 4))

    table_data = [[
        Paragraph(f"<b>Regel-ID</b>", normal_style),
        Paragraph(f"<b>Nivå</b>", normal_style),
        Paragraph(f"<b>Beskrivning &amp; Åtgärd</b>", normal_style)
    ]]

    for iss in filtered_issues:
        rule_id = clean_text_for_pdf(iss.get('rule_id', 'RULE'))
        sev_raw = iss.get('severity', 'Information')
        sev = clean_text_for_pdf(sev_raw)
        desc = clean_text_for_pdf(iss.get('description', ''))
        remediation = iss.get('remediation', '')

        desc_html = desc
        if remediation:
            desc_html += f"<br/><font color='#0284C7'><b>Åtgärdsförslag:</b> {clean_text_for_pdf(remediation)}</font>"

        if 'kritiskt' in str(sev_raw).lower() or 'critical' in str(sev_raw).lower():
            sev_p = Paragraph(f"<font color='#DC2626'><b>{sev}</b></font>", normal_style)
        elif 'varning' in str(sev_raw).lower() or 'warning' in str(sev_raw).lower():
            sev_p = Paragraph(f"<font color='#D97706'><b>{sev}</b></font>", normal_style)
        else:
            sev_p = Paragraph(f"<font color='#16A34A'><b>{sev}</b></font>", normal_style)

        table_data.append([
            Paragraph(f"<b>{rule_id}</b>", normal_style),
            sev_p,
            Paragraph(desc_html, normal_style)
        ])

    issues_table = Table(table_data, colWidths=[80, 70, 370])
    issues_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(issues_table)
    story.append(Spacer(1, 12))

    approval_status = "GODKÄND MED ANMÄRKNING" if crit_count > 0 else "GODKÄND"
    status_color = '#DC2626' if crit_count > 0 else '#16A34A'

    status_data = [
        [Paragraph("<b>Status:</b>", normal_style), Paragraph(f"<font color='{status_color}'><b>{approval_status}</b></font>", normal_style)],
        [Paragraph("<b>Granskare:</b>", normal_style), Paragraph("Ahmad Almasmoum", normal_style)],
        [Paragraph("<b>Datum:</b>", normal_style), Paragraph(datetime.now().strftime('%Y-%m-%d'), normal_style)],
        [Paragraph("<b>QR-Spårbarhet:</b>", normal_style), Paragraph("asaDrawing.se - QC Report & Traceability", normal_style)]
    ]

    if include_qr:
        qr_dir = "temp_assets"
        os.makedirs(qr_dir, exist_ok=True)
        qr_path = os.path.join(qr_dir, f"qr_{project_id}.png")
        qr_img_data = f"asaDrawing QC | Project: {project_id} | Drawing: {drawing_name} | Rev: {revision} | Status: {approval_status}"
        try:
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(qr_img_data)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color="black", back_color="white")
            img_qr.save(qr_path)
            if os.path.exists(qr_path) and os.path.getsize(qr_path) > 0:
                qr_element = Image(qr_path, width=60, height=60)
            else:
                qr_element = Paragraph("[QR]", normal_style)
        except Exception:
            qr_element = Paragraph("[QR]", normal_style)

        footer_box_data = [[Table(status_data, colWidths=[110, 290]), qr_element]]
        footer_box = Table(footer_box_data, colWidths=[420, 100])
    else:
        footer_box = Table([[Table(status_data, colWidths=[110, 410])]], colWidths=[520])

    footer_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))

    story.append(footer_box)
    doc.build(story, onFirstPage=lambda c, d: add_header_footer(c, d, project_id, drawing_name, revision),
                     onLaterPages=lambda c, d: add_header_footer(c, d, project_id, drawing_name, revision))