from __future__ import annotations

import io
import base64
from typing import Any, Dict, List, Tuple

# Try WeasyPrint first (preferred on systems with GTK/Pango/Cairo)
try:
    from weasyprint import HTML, CSS  # type: ignore
    _HAS_WEASYPRINT = True
except Exception:
    HTML = None  # type: ignore
    CSS = None  # type: ignore
    _HAS_WEASYPRINT = False


def generate_pdf_report(
    candidate_name: str,
    match_score: float,
    confidence: float,
    explanation: str,
    missing_skills: List[str],
    top_snippets: List[Tuple[str, float]],
) -> bytes:
    if _HAS_WEASYPRINT:
        html_snippets = "".join(
            f"<tr><td>{text[:120]}{'...' if len(text) > 120 else ''}</td><td style='text-align:center'>{sim:.2f}</td></tr>"
            for text, sim in (top_snippets or [])[:5]
        )
        html_missing = ", ".join(missing_skills or [])
        html = f"""
        <html>
          <head>
            <meta charset='utf-8' />
            <style>
              body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 24px; color: #333; }}
              h1 {{ margin: 0 0 8px; color: #2c3e50; }}
              h2 {{ margin: 16px 0 8px; color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 4px; }}
              .meta p {{ margin: 2px 0; }}
              table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
              th, td {{ border: 1px solid #ddd; padding: 12px 8px; }}
              th {{ background: #f8f9fa; text-align: left; font-weight: 600; }}
              .score {{ color: #27ae60; font-size: 1.2em; }}
            </style>
          </head>
          <body>
            <h1>Resume–Job Match Report</h1>
            <div class='meta'>
              <p>Candidate: <b>{candidate_name or 'Unknown'}</b></p>
              <p>Match Score: <b class='score'>{match_score:.1f}%</b></p>
              <p>Confidence: <b>{confidence:.2f}</b></p>
            </div>
            <h2>Explanation</h2>
            <p>{explanation}</p>
            {f"<h2>Missing/Gap Skills</h2><p>{html_missing}</p>" if html_missing else ''}
            {"" if not html_snippets else "<h2>Top Matching Resume Snippets</h2>"}
            {"" if not html_snippets else f"<table><thead><tr><th>Snippet</th><th>Similarity</th></tr></thead><tbody>{html_snippets}</tbody></table>"}
          </body>
        </html>
        """
        buf = io.BytesIO()
        HTML(string=html).write_pdf(target=buf, stylesheets=[CSS(string="@page { size: A4; margin: 24pt; }")])
        return buf.getvalue()
    
    # Fallback: ReportLab
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()

    elements: List[Any] = []
    elements.append(Paragraph("Resume–Job Match Report", styles["Title"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"Candidate: <b>{candidate_name or 'Unknown'}</b>", styles["Normal"]))
    elements.append(Paragraph(f"Match Score: <b>{match_score:.1f}%</b>", styles["Normal"]))
    elements.append(Paragraph(f"Confidence: <b>{confidence:.2f}</b>", styles["Normal"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Explanation", styles["Heading2"]))
    elements.append(Paragraph(explanation, styles["BodyText"]))
    elements.append(Spacer(1, 6))
    if missing_skills:
        elements.append(Paragraph("Missing/Gap Skills", styles["Heading2"]))
        elements.append(Paragraph(", ".join(missing_skills), styles["BodyText"]))
        elements.append(Spacer(1, 6))
    if top_snippets:
        data = [["Snippet", "Similarity"]]
        for text, sim in top_snippets[:5]:
            data.append([text[:100] + ("..." if len(text) > 100 else ""), f"{sim:.2f}"])
        tbl = Table(data, colWidths=[360, 100])
        tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("ALIGN", (1, 1), (-1, -1), "CENTER")]))
        elements.append(tbl)
    doc.build(elements)
    return buf.getvalue()


def generate_ats_resume_pdf(data: Dict[str, Any]) -> bytes:
    if _HAS_WEASYPRINT:
        def join_nonempty(parts: List[str], sep: str = " · ") -> str:
            return sep.join([p for p in parts if p])

        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip()
        phone = str(data.get("phone", "")).strip()
        location = str(data.get("location", "")).strip()
        links = [str(x).strip() for x in (data.get("links") or []) if str(x).strip()]
        summary = str(data.get("summary", "")).strip()
        skills = [str(s).strip() for s in (data.get("skills") or []) if str(s).strip()]
        photo = data.get("photo", None)

        def list_items(items: List[str]) -> str:
            if not items:
                return ""
            li = "".join(f"<li>{item}</li>" for item in items)
            return f"<ul class='bullet-list'>{li}</ul>"

        # Photo HTML - centered at top
        photo_html = ""
        if photo:
            if isinstance(photo, str) and photo.startswith('data:image'):
                photo_html = f'<div class="photo-container"><img src="{photo}" class="profile-photo" alt="Profile Photo"></div>'
            elif isinstance(photo, str):
                photo_html = f'<div class="photo-container"><div class="photo-placeholder">Photo</div></div>'
            else:
                photo_html = '<div class="photo-container"><div class="photo-placeholder">Photo</div></div>'

        # Experience section
        exp_html = ""
        for exp in (data.get("experience") or []):
            title = str(exp.get("title", "")).strip()
            company = str(exp.get("company", "")).strip()
            eloc = str(exp.get("location", "")).strip()
            start = str(exp.get("start", "")).strip()
            end = str(exp.get("end", "")).strip()
            
            header_left = join_nonempty([title, company], sep=" at ")
            header_right = join_nonempty([start, end], sep=" - ")
            location_line = f"<div class='item-location'>{eloc}</div>" if eloc else ""
            
            bullets = [str(b).strip() for b in (exp.get("bullets") or []) if str(b).strip()]
            exp_html += f"""
            <div class='experience-item'>
                <div class='item-header'>
                    <h3 class='item-title'>{header_left}</h3>
                    <span class='item-date'>{header_right}</span>
                </div>
                {location_line}
                {list_items(bullets)}
            </div>
            """

        # Education section
        edu_html = ""
        for ed in (data.get("education") or []):
            degree = str(ed.get("degree", "")).strip()
            school = str(ed.get("school", "")).strip()
            eloc = str(ed.get("location", "")).strip()
            year = str(ed.get("year", "")).strip()
            
            header_left = join_nonempty([degree, school], sep=" - ")
            location_line = f"<div class='item-location'>{eloc}</div>" if eloc else ""
            
            details = [str(b).strip() for b in (ed.get("details") or []) if str(b).strip()]
            edu_html += f"""
            <div class='education-item'>
                <div class='item-header'>
                    <h3 class='item-title'>{header_left}</h3>
                    <span class='item-date'>{year}</span>
                </div>
                {location_line}
                {list_items(details) if details else ""}
            </div>
            """

        # Projects section
        proj_html = ""
        for pr in (data.get("projects") or []):
            pname = str(pr.get("name", "")).strip()
            pdesc = str(pr.get("description", "")).strip()
            tech = [str(t).strip() for t in (pr.get("tech") or []) if str(t).strip()]
            tech_line = f"<div class='tech-stack'><strong>Technologies:</strong> {', '.join(tech)}</div>" if tech else ""
            
            proj_html += f"""
            <div class='project-item'>
                <h3 class='item-title'>{pname}</h3>
                <div class='project-desc'>{pdesc}</div>
                {tech_line}
            </div>
            """

        # Certifications
        certs = [str(c).strip() for c in (data.get("certifications") or []) if str(c).strip()]
        cert_html = list_items(certs)

        # Skills formatting - clean categories
        skills_html = ""
        if skills:
            categorized_skills = {}
            uncategorized_skills = []
            
            for skill in skills:
                if ':' in skill:
                    category, skill_list = skill.split(':', 1)
                    categorized_skills[category.strip()] = skill_list.strip()
                else:
                    uncategorized_skills.append(skill)
            
            if categorized_skills:
                for category, skill_list in categorized_skills.items():
                    skills_html += f"<div class='skill-category'><strong>{category}:</strong> {skill_list}</div>"
            
            if uncategorized_skills:
                skills_html += f"<div class='skill-category'>{', '.join(uncategorized_skills)}</div>"
            
            if not skills_html:
                skills_html = f"<div class='skill-category'>{', '.join(skills)}</div>"

        # Contact info
        contact_parts = []
        if email:
            contact_parts.append(f'<a href="mailto:{email}" class="contact-link">{email}</a>')
        if phone:
            contact_parts.append(f'<span class="contact-item">{phone}</span>')
        if location:
            contact_parts.append(f'<span class="contact-item">{location}</span>')
        for link in links:
            if link.startswith('http'):
                contact_parts.append(f'<a href="{link}" class="contact-link">{link}</a>')
            else:
                contact_parts.append(f'<span class="contact-item">{link}</span>')
        
        contact_line = ' | '.join(contact_parts)

        # Clean Single-Column HTML Template
        html = f"""
        <html>
          <head>
            <meta charset='utf-8' />
            <style>
              * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
              }}
              
              body {{ 
                font-family: 'Arial', sans-serif; 
                line-height: 1.6;
                color: #333;
                font-size: 11pt;
                background: white;
              }}
              
              .container {{
                max-width: 8.5in;
                margin: 0 auto;
                padding: 0.75in;
                background: white;
              }}
              
              /* Photo Section */
              .photo-container {{
                text-align: center;
                margin-bottom: 20px;
              }}
              
              .profile-photo {{
                width: 100px;
                height: 100px;
                border-radius: 50%;
                object-fit: cover;
                border: 3px solid #2c3e50;
              }}
              
              .photo-placeholder {{
                width: 100px;
                height: 100px;
                border-radius: 50%;
                background: #ecf0f1;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                color: #7f8c8d;
                font-weight: bold;
                border: 3px solid #2c3e50;
              }}
              
              /* Header Section */
              .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #2c3e50;
              }}
              
              h1 {{ 
                font-size: 28pt;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
                letter-spacing: 1px;
              }}
              
              .contact-info {{
                font-size: 10pt;
                color: #555;
                line-height: 1.4;
              }}
              
              .contact-link {{
                color: #2980b9;
                text-decoration: none;
              }}
              
              .contact-item {{
                color: #555;
              }}
              
              /* Section Headers */
              h2 {{ 
                font-size: 14pt;
                font-weight: bold;
                color: #2c3e50;
                margin: 25px 0 15px 0;
                padding-bottom: 5px;
                border-bottom: 1px solid #bdc3c7;
                text-transform: uppercase;
                letter-spacing: 1px;
              }}
              
              /* Summary Section */
              .summary {{
                font-size: 11pt;
                line-height: 1.7;
                color: #444;
                text-align: justify;
                margin-bottom: 20px;
              }}
              
              /* Skills Section */
              .skills-container {{
                margin-bottom: 20px;
              }}
              
              .skill-category {{
                margin-bottom: 8px;
                font-size: 11pt;
                line-height: 1.5;
              }}
              
              .skill-category strong {{
                color: #2c3e50;
                font-weight: bold;
              }}
              
              /* Experience & Education Items */
              .experience-item, .education-item, .project-item {{
                margin-bottom: 20px;
                page-break-inside: avoid;
              }}
              
              .item-header {{
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                margin-bottom: 5px;
                flex-wrap: wrap;
              }}
              
              .item-title {{
                font-size: 12pt;
                font-weight: bold;
                color: #2c3e50;
                margin: 0;
                flex: 1;
              }}
              
              .item-date {{
                font-size: 10pt;
                color: #7f8c8d;
                font-weight: normal;
                white-space: nowrap;
                margin-left: 15px;
              }}
              
              .item-location {{
                font-size: 10pt;
                color: #7f8c8d;
                font-style: italic;
                margin-bottom: 8px;
              }}
              
              /* Bullet Lists */
              .bullet-list {{
                margin: 10px 0 0 20px;
                padding: 0;
              }}
              
              .bullet-list li {{
                margin-bottom: 6px;
                line-height: 1.6;
                color: #444;
                font-size: 11pt;
              }}
              
              /* Projects */
              .project-desc {{
                margin: 8px 0;
                color: #444;
                line-height: 1.6;
                font-size: 11pt;
              }}
              
              .tech-stack {{
                margin-top: 8px;
                padding: 6px 10px;
                background: #f8f9fa;
                border-left: 3px solid #2980b9;
                font-size: 10pt;
                color: #555;
              }}
              
              /* Page breaks */
              .section {{
                page-break-inside: avoid;
              }}
              
              /* Print optimizations */
              @media print {{
                .container {{
                  padding: 0.5in;
                }}
                
                .profile-photo, .photo-placeholder {{
                  width: 80px;
                  height: 80px;
                }}
                
                h1 {{
                  font-size: 24pt;
                }}
              }}
            </style>
          </head>
          <body>
            <div class='container'>
              {photo_html}
              
              <div class='header'>
                {f"<h1>{name}</h1>" if name else '<h1>Your Name</h1>'}
                {f"<div class='contact-info'>{contact_line}</div>" if contact_line else ''}
              </div>
              
              {f"<h2>Professional Summary</h2><div class='summary'>{summary}</div>" if summary else ''}
              
              {f"<h2>Core Skills</h2><div class='skills-container'>{skills_html}</div>" if skills else ''}
              
              {f"<h2>Professional Experience</h2>{exp_html}" if exp_html else ''}
              
              {f"<h2>Education</h2>{edu_html}" if edu_html else ''}
              
              {f"<h2>Projects</h2>{proj_html}" if proj_html else ''}
              
              {f"<h2>Certifications</h2>{cert_html}" if cert_html else ''}
            </div>
          </body>
        </html>
        """
        
        buf = io.BytesIO()
        HTML(string=html).write_pdf(
            target=buf, 
            stylesheets=[CSS(string="@page { size: A4; margin: 0.6in; }")]
        )
        return buf.getvalue()
    
    # Fallback: ReportLab version
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, ListFlowable, ListItem  # type: ignore
    from reportlab.lib.enums import TA_CENTER, TA_LEFT  # type: ignore

    def join_nonempty(parts: List[str], sep: str = " · ") -> str:
        return sep.join([p for p in parts if p])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.75*72, bottomMargin=0.75*72)
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=12,
        alignment=TA_CENTER,
        textColor=colors.Color(44/255, 62/255, 80/255)  # #2c3e50
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.Color(44/255, 62/255, 80/255),
        borderWidth=1,
        borderColor=colors.Color(189/255, 195/255, 199/255),
        borderPadding=5
    ))

    elements: List[Any] = []

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip()
    phone = str(data.get("phone", "")).strip()
    location = str(data.get("location", "")).strip()
    links = [str(x).strip() for x in (data.get("links") or []) if str(x).strip()]
    
    # Header
    if name:
        elements.append(Paragraph(name, styles["CustomTitle"]))
        elements.append(Spacer(1, 6))
    
    contact_line = join_nonempty([email, phone, location] + links, " | ")
    if contact_line:
        elements.append(Paragraph(contact_line, styles["Normal"]))
        elements.append(Spacer(1, 12))

    # Summary
    summary = str(data.get("summary", "")).strip()
    if summary:
        elements.append(Paragraph("PROFESSIONAL SUMMARY", styles["SectionHeader"]))
        elements.append(Paragraph(summary, styles["BodyText"]))
        elements.append(Spacer(1, 12))

    # Skills
    skills = [str(s).strip() for s in (data.get("skills") or []) if str(s).strip()]
    if skills:
        elements.append(Paragraph("CORE SKILLS", styles["SectionHeader"]))
        elements.append(Paragraph(", ".join(skills), styles["BodyText"]))
        elements.append(Spacer(1, 12))

    # Experience
    experience = data.get("experience", [])
    if experience:
        elements.append(Paragraph("PROFESSIONAL EXPERIENCE", styles["SectionHeader"]))
        for exp in experience:
            title = str(exp.get("title", "")).strip()
            company = str(exp.get("company", "")).strip()
            if not title and not company:
                continue
                
            header = join_nonempty([title, company], " at ")
            dates = join_nonempty([str(exp.get("start", "")).strip(), str(exp.get("end", "")).strip()], " - ")
            
            elements.append(Paragraph(f"<b>{header}</b> | {dates}", styles["Normal"]))
            
            location = str(exp.get("location", "")).strip()
            if location:
                elements.append(Paragraph(f"<i>{location}</i>", styles["Normal"]))
            
            bullets = [str(b).strip() for b in (exp.get("bullets", []) or []) if str(b).strip()]
            if bullets:
                for bullet in bullets:
                    elements.append(Paragraph(f"• {bullet}", styles["BodyText"]))
            
            elements.append(Spacer(1, 8))

    # Education
    education = data.get("education", [])
    if education:
        elements.append(Paragraph("EDUCATION", styles["SectionHeader"]))
        for ed in education:
            degree = str(ed.get("degree", "")).strip()
            school = str(ed.get("school", "")).strip()
            if not degree and not school:
                continue
                
            header = join_nonempty([degree, school], " - ")
            year = str(ed.get("year", "")).strip()
            
            elements.append(Paragraph(f"<b>{header}</b> | {year}", styles["Normal"]))
            
            location = str(ed.get("location", "")).strip()
            if location:
                elements.append(Paragraph(f"<i>{location}</i>", styles["Normal"]))
            
            details = [str(d).strip() for d in (ed.get("details", []) or []) if str(d).strip()]
            if details:
                for detail in details:
                    elements.append(Paragraph(f"• {detail}", styles["BodyText"]))
            
            elements.append(Spacer(1, 8))

    # Projects
    projects = data.get("projects", [])
    if projects:
        elements.append(Paragraph("PROJECTS", styles["SectionHeader"]))
        for proj in projects:
            name = str(proj.get("name", "")).strip()
            if not name:
                continue
                
            elements.append(Paragraph(f"<b>{name}</b>", styles["Normal"]))
            
            desc = str(proj.get("description", "")).strip()
            if desc:
                elements.append(Paragraph(desc, styles["BodyText"]))
            
            tech = [str(t).strip() for t in (proj.get("tech", []) or []) if str(t).strip()]
            if tech:
                elements.append(Paragraph(f"<b>Technologies:</b> {', '.join(tech)}", styles["BodyText"]))
            
            elements.append(Spacer(1, 8))

    # Certifications
    certs = [str(c).strip() for c in (data.get("certifications", []) or []) if str(c).strip()]
    if certs:
        elements.append(Paragraph("CERTIFICATIONS", styles["SectionHeader"]))
        for cert in certs:
            elements.append(Paragraph(f"• {cert}", styles["BodyText"]))

    doc.build(elements)
    return buf.getvalue()