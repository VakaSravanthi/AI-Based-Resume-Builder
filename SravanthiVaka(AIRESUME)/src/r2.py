from __future__ import annotations

import io
import base64
import re
from datetime import datetime, date
from typing import Any, Dict, List, Tuple, Optional, Union
from PIL import Image

# Try WeasyPrint first (preferred on systems with GTK/Pango/Cairo)
try:
    from weasyprint import HTML, CSS  # type: ignore
    _HAS_WEASYPRINT = True
except Exception:
    HTML = None  # type: ignore
    CSS = None  # type: ignore
    _HAS_WEASYPRINT = False


def debug_photo_data(photo_data):
    """Debug function to check photo data"""
    if not photo_data:
        print("No photo data provided")
        return False
    
    if not isinstance(photo_data, str):
        print(f"Photo data is not string, type: {type(photo_data)}")
        return False
    
    if not photo_data.startswith('data:image'):
        print(f"Photo data doesn't start with data:image, starts with: {photo_data[:50]}")
        return False
    
    if ',' not in photo_data:
        print("Photo data missing comma separator")
        return False
    
    try:
        header, data = photo_data.split(',', 1)
        base64.b64decode(data, validate=True)
        print(f"Photo data is valid base64, header: {header}")
        print(f"Photo data length: {len(data)} characters")
        return True
    except Exception as e:
        print(f"Photo data base64 validation failed: {e}")
        return False


def process_photo_for_reportlab(photo_data: str):
    """Process photo data for ReportLab compatibility"""
    try:
        if not photo_data or not isinstance(photo_data, str):
            return None
            
        if photo_data.startswith('data:image'):
            # Extract base64 data
            if ',' in photo_data:
                header, data = photo_data.split(',', 1)
                photo_bytes = base64.b64decode(data)
                
                # Create PIL Image
                img = Image.open(io.BytesIO(photo_bytes))
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to appropriate size
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                
                # Save to BytesIO for ReportLab
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG', quality=85)
                img_buffer.seek(0)
                
                return img_buffer
    except Exception as e:
        print(f"Photo processing error for ReportLab: {e}")
        return None
    
    return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats to datetime object"""
    if not date_str or date_str.lower() in ['present', 'current', 'ongoing']:
        return datetime.now()
    
    # Common date formats
    formats = [
        '%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y',
        '%Y-%m', '%Y/%m', '%m/%Y', '%m-%Y',
        '%Y', '%B %Y', '%b %Y', '%B %d, %Y', '%b %d, %Y'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    # Try to extract year if nothing else works
    year_match = re.search(r'\b(19|20)\d{2}\b', date_str)
    if year_match:
        return datetime(int(year_match.group()), 1, 1)
    
    return None


def calculate_experience_gaps(experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate gaps in employment history"""
    gaps = []
    if not experience or len(experience) < 2:
        return gaps
    
    # Sort experience by start date
    sorted_exp = []
    for exp in experience:
        start_date = parse_date(str(exp.get("start", "")))
        end_date = parse_date(str(exp.get("end", "")))
        if start_date:
            sorted_exp.append({
                'start': start_date,
                'end': end_date or datetime.now(),
                'title': str(exp.get("title", "")).strip(),
                'company': str(exp.get("company", "")).strip()
            })
    
    sorted_exp.sort(key=lambda x: x['start'])
    
    # Find gaps between consecutive jobs
    for i in range(len(sorted_exp) - 1):
        current_end = sorted_exp[i]['end']
        next_start = sorted_exp[i + 1]['start']
        
        # Calculate gap in months
        gap_months = (next_start.year - current_end.year) * 12 + (next_start.month - current_end.month)
        
        if gap_months > 1:  # Gap of more than 1 month
            gaps.append({
                'type': 'employment',
                'start_date': current_end.strftime('%B %Y'),
                'end_date': next_start.strftime('%B %Y'),
                'duration_months': gap_months,
                'description': f"Gap between {sorted_exp[i]['title']} at {sorted_exp[i]['company']} and {sorted_exp[i+1]['title']} at {sorted_exp[i+1]['company']}"
            })
    
    return gaps


def analyze_education_gaps(education: List[Dict[str, Any]], experience: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze education-related gaps and requirements"""
    gaps = []
    
    if not education:
        gaps.append({
            'type': 'education_missing',
            'severity': 'high',
            'description': 'No formal education information provided'
        })
        return gaps
    
    # Common degree levels and their typical requirements
    degree_hierarchy = {
        'high school': 1, 'diploma': 1, 'ged': 1,
        'associate': 2, 'associates': 2,
        'bachelor': 3, 'bachelors': 3, 'ba': 3, 'bs': 3, 'bsc': 3,
        'master': 4, 'masters': 4, 'ma': 4, 'ms': 4, 'msc': 4, 'mba': 4,
        'phd': 5, 'doctorate': 5, 'doctoral': 5
    }
    
    # Analyze degree levels
    highest_degree_level = 0
    degrees = []
    
    for edu in education:
        degree = str(edu.get("degree", "")).lower().strip()
        year = str(edu.get("year", "")).strip()
        school = str(edu.get("school", "")).strip()
        
        if degree:
            degrees.append({
                'degree': degree,
                'year': year,
                'school': school,
                'original': edu
            })
            
            # Find degree level
            for deg_type, level in degree_hierarchy.items():
                if deg_type in degree:
                    highest_degree_level = max(highest_degree_level, level)
                    break
    
    # Check for common education gaps
    if highest_degree_level == 0:
        gaps.append({
            'type': 'education_level',
            'severity': 'medium',
            'description': 'Degree level unclear or not recognized'
        })
    
    if highest_degree_level < 3:  # Less than bachelor's
        gaps.append({
            'type': 'education_level',
            'severity': 'medium',
            'description': 'No bachelor\'s degree - may limit opportunities for senior positions'
        })
    
    # Check for education timeline gaps
    current_year = datetime.now().year
    for degree in degrees:
        if degree['year']:
            year_match = re.search(r'\b(19|20)\d{2}\b', degree['year'])
            if year_match:
                grad_year = int(year_match.group())
                years_since_grad = current_year - grad_year
                
                if years_since_grad > 15:
                    gaps.append({
                        'type': 'education_currency',
                        'severity': 'low',
                        'description': f'Education from {grad_year} may need updating with recent developments'
                    })
    
    # Check for education-experience alignment
    if experience:
        first_job_start = None
        for exp in experience:
            start_date = parse_date(str(exp.get("start", "")))
            if start_date and (not first_job_start or start_date < first_job_start):
                first_job_start = start_date
        
        if first_job_start and degrees:
            latest_grad_year = 0
            for degree in degrees:
                if degree['year']:
                    year_match = re.search(r'\b(19|20)\d{2}\b', degree['year'])
                    if year_match:
                        latest_grad_year = max(latest_grad_year, int(year_match.group()))
            
            if latest_grad_year and first_job_start.year < latest_grad_year:
                gaps.append({
                    'type': 'timeline_mismatch',
                    'severity': 'low',
                    'description': f'First job started before graduation ({first_job_start.year} vs {latest_grad_year})'
                })
    
    return gaps


def analyze_skill_gaps(skills: List[str], job_requirements: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Analyze skill gaps based on common industry requirements"""
    gaps = []
    
    if not skills:
        gaps.append({
            'type': 'skills_missing',
            'severity': 'high',
            'description': 'No skills information provided'
        })
        return gaps
    
    # Flatten skills list and normalize
    all_skills = []
    for skill in skills:
        skill_str = str(skill).lower()
        if ':' in skill_str:
            _, skill_list = skill_str.split(':', 1)
            all_skills.extend([s.strip() for s in skill_list.split(',')])
        else:
            all_skills.append(skill_str.strip())
    
    # Common skill categories and requirements
    skill_categories = {
        'technical': ['python', 'java', 'javascript', 'sql', 'html', 'css', 'react', 'node', 'docker', 'kubernetes', 'aws', 'azure', 'git'],
        'data': ['excel', 'powerbi', 'tableau', 'sql', 'python', 'r', 'statistics', 'analytics'],
        'soft': ['communication', 'leadership', 'teamwork', 'problem solving', 'project management'],
        'certifications': ['pmp', 'scrum', 'agile', 'cisco', 'microsoft', 'aws', 'google cloud']
    }
    
    # Check for missing categories
    found_categories = set()
    for category, category_skills in skill_categories.items():
        if any(cat_skill in ' '.join(all_skills) for cat_skill in category_skills):
            found_categories.add(category)
    
    missing_categories = set(skill_categories.keys()) - found_categories
    for missing_cat in missing_categories:
        gaps.append({
            'type': 'skill_category',
            'severity': 'medium',
            'description': f'Limited {missing_cat} skills mentioned'
        })
    
    # Check against job requirements if provided
    if job_requirements:
        missing_requirements = []
        job_skills = [req.lower().strip() for req in job_requirements]
        
        for req_skill in job_skills:
            if not any(req_skill in skill for skill in all_skills):
                missing_requirements.append(req_skill)
        
        if missing_requirements:
            gaps.append({
                'type': 'job_requirements',
                'severity': 'high',
                'description': f'Missing required skills: {", ".join(missing_requirements)}'
            })
    
    return gaps


def comprehensive_gap_analysis(data: Dict[str, Any], job_requirements: Optional[Dict[str, Any]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Perform comprehensive gap analysis on resume data"""
    
    experience = data.get("experience", [])
    education = data.get("education", [])
    skills = data.get("skills", [])
    
    job_skills = job_requirements.get("skills", []) if job_requirements else None
    
    gap_analysis = {
        'experience_gaps': calculate_experience_gaps(experience),
        'education_gaps': analyze_education_gaps(education, experience),
        'skill_gaps': analyze_skill_gaps(skills, job_skills),
        'overall_assessment': []
    }
    
    # Overall assessment
    total_gaps = sum(len(gaps) for gaps in gap_analysis.values() if isinstance(gaps, list))
    high_severity_gaps = sum(1 for gap_list in gap_analysis.values() 
                           if isinstance(gap_list, list) 
                           for gap in gap_list 
                           if gap.get('severity') == 'high')
    
    if total_gaps == 0:
        gap_analysis['overall_assessment'].append({
            'type': 'positive',
            'description': 'Strong candidate with comprehensive background'
        })
    elif high_severity_gaps > 2:
        gap_analysis['overall_assessment'].append({
            'type': 'concern',
            'description': f'Multiple high-priority gaps identified ({high_severity_gaps} critical areas)'
        })
    else:
        gap_analysis['overall_assessment'].append({
            'type': 'moderate',
            'description': f'Some gaps identified but overall solid profile ({total_gaps} total gaps)'
        })
    
    return gap_analysis


def generate_pdf_report(
    candidate_name: str,
    match_score: float,
    confidence: float,
    explanation: str,
    missing_skills: List[str],
    top_snippets: List[Tuple[str, float]],
    gap_analysis: Optional[Dict[str, List[Dict[str, Any]]]] = None
) -> bytes:
    if _HAS_WEASYPRINT:
        html_snippets = "".join(
            f"<tr><td>{text[:120]}{'...' if len(text) > 120 else ''}</td><td style='text-align:center'>{sim:.2f}</td></tr>"
            for text, sim in (top_snippets or [])[:5]
        )
        html_missing = ", ".join(missing_skills or [])
        
        # Generate gap analysis HTML
        gap_html = ""
        if gap_analysis:
            gap_html = "<h2>Gap Analysis</h2>"
            
            for gap_type, gaps in gap_analysis.items():
                if not gaps or gap_type == 'overall_assessment':
                    continue
                    
                section_title = gap_type.replace('_', ' ').title()
                gap_html += f"<h3>{section_title}</h3>"
                
                if gaps:
                    gap_html += "<ul class='gap-list'>"
                    for gap in gaps:
                        severity_class = gap.get('severity', 'medium')
                        gap_html += f"<li class='gap-{severity_class}'><strong>{gap.get('type', '').replace('_', ' ').title()}:</strong> {gap.get('description', '')}</li>"
                    gap_html += "</ul>"
                else:
                    gap_html += "<p class='no-gaps'>No significant gaps identified in this area.</p>"
            
            # Overall assessment
            if gap_analysis.get('overall_assessment'):
                gap_html += "<h3>Overall Assessment</h3>"
                for assessment in gap_analysis['overall_assessment']:
                    assessment_class = assessment.get('type', 'moderate')
                    gap_html += f"<p class='assessment-{assessment_class}'>{assessment.get('description', '')}</p>"
        
        html = f"""
        <html>
          <head>
            <meta charset='utf-8' />
            <style>
              body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 24px; color: #333; line-height: 1.6; }}
              h1 {{ margin: 0 0 8px; color: #2c3e50; font-size: 24pt; }}
              h2 {{ margin: 20px 0 12px; color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 4px; font-size: 16pt; }}
              h3 {{ margin: 16px 0 8px; color: #2c3e50; font-size: 14pt; }}
              .meta p {{ margin: 2px 0; font-size: 12pt; }}
              table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
              th, td {{ border: 1px solid #ddd; padding: 12px 8px; }}
              th {{ background: #f8f9fa; text-align: left; font-weight: 600; }}
              .score {{ color: #27ae60; font-size: 1.2em; font-weight: bold; }}
              
              /* Gap Analysis Styles */
              .gap-list {{ margin: 10px 0; padding-left: 20px; }}
              .gap-list li {{ margin: 8px 0; padding: 8px; border-radius: 4px; }}
              .gap-high {{ background: #fff5f5; border-left: 4px solid #e53e3e; }}
              .gap-medium {{ background: #fffaf0; border-left: 4px solid #dd6b20; }}
              .gap-low {{ background: #f7fafc; border-left: 4px solid #4299e1; }}
              .no-gaps {{ color: #38a169; font-style: italic; }}
              
              .assessment-positive {{ color: #38a169; font-weight: bold; padding: 10px; background: #f0fff4; border-radius: 4px; }}
              .assessment-concern {{ color: #e53e3e; font-weight: bold; padding: 10px; background: #fff5f5; border-radius: 4px; }}
              .assessment-moderate {{ color: #dd6b20; font-weight: bold; padding: 10px; background: #fffaf0; border-radius: 4px; }}
              
              @page {{ size: A4; margin: 24pt; }}
            </style>
          </head>
          <body>
            <h1>Resume–Job Match Report</h1>
            <div class='meta'>
              <p>Candidate: <b>{candidate_name or 'Unknown'}</b></p>
              <p>Match Score: <b class='score'>{match_score:.1f}%</b></p>
              <p>Confidence: <b>{confidence:.2f}</b></p>
              <p>Generated: <b>{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</b></p>
            </div>
            
            <h2>Explanation</h2>
            <p>{explanation}</p>
            
            {f"<h2>Missing/Gap Skills</h2><p>{html_missing}</p>" if html_missing else ''}
            
            {gap_html}
            
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
    elements.append(Paragraph(f"Generated: <b>{datetime.now().strftime('%B %d, %Y at %I:%M %p')}</b>", styles["Normal"]))
    elements.append(Spacer(1, 12))
    
    elements.append(Paragraph("Explanation", styles["Heading2"]))
    elements.append(Paragraph(explanation, styles["BodyText"]))
    elements.append(Spacer(1, 10))
    
    if missing_skills:
        elements.append(Paragraph("Missing/Gap Skills", styles["Heading2"]))
        elements.append(Paragraph(", ".join(missing_skills), styles["BodyText"]))
        elements.append(Spacer(1, 10))
    
    # Add gap analysis
    if gap_analysis:
        elements.append(Paragraph("Gap Analysis", styles["Heading2"]))
        
        for gap_type, gaps in gap_analysis.items():
            if not gaps or gap_type == 'overall_assessment':
                continue
                
            section_title = gap_type.replace('_', ' ').title()
            elements.append(Paragraph(section_title, styles["Heading3"]))
            
            if gaps:
                for gap in gaps:
                    elements.append(Paragraph(f"• <b>{gap.get('type', '').replace('_', ' ').title()}:</b> {gap.get('description', '')}", styles["BodyText"]))
            else:
                elements.append(Paragraph("No significant gaps identified in this area.", styles["BodyText"]))
            
            elements.append(Spacer(1, 8))
        
        # Overall assessment
        if gap_analysis.get('overall_assessment'):
            elements.append(Paragraph("Overall Assessment", styles["Heading3"]))
            for assessment in gap_analysis['overall_assessment']:
                elements.append(Paragraph(assessment.get('description', ''), styles["BodyText"]))
    
    if top_snippets:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Top Matching Resume Snippets", styles["Heading2"]))
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

        # Photo HTML - improved validation and processing
        photo_html = ""
        if photo:
            # Debug photo data
            print("Processing photo for WeasyPrint...")
            debug_photo_data(photo)
            
            try:
                if isinstance(photo, str) and photo.startswith('data:image'):
                    # Validate the base64 data
                    if ',' in photo:
                        header, data = photo.split(',', 1)
                        # Test if it's valid base64
                        base64.b64decode(data, validate=True)
                        photo_html = f'<div class="photo-container"><img src="{photo}" class="profile-photo" alt="Profile Photo"></div>'
                        print("Photo HTML created successfully")
                    else:
                        photo_html = '<div class="photo-container"><div class="photo-placeholder">Photo</div></div>'
                        print("Invalid photo format - using placeholder")
                elif isinstance(photo, str) and photo:
                    # If it's a string but not data URL, show placeholder
                    photo_html = '<div class="photo-container"><div class="photo-placeholder">Photo</div></div>'
                    print("Non-data URL photo - using placeholder")
                else:
                    photo_html = '<div class="photo-container"><div class="photo-placeholder">Photo</div></div>'
                    print("No valid photo data - using placeholder")
            except Exception as e:
                print(f"Photo processing error: {e}")
                photo_html = '<div class="photo-container"><div class="photo-placeholder">Photo Error</div></div>'

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

        # Enhanced HTML Template with improved photo support
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
              
              /* Photo Section - Enhanced */
              .photo-container {{
                text-align: center;
                margin-bottom: 25px;
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
              }}
              
              .profile-photo {{
                width: 120px !important;
                height: 120px !important;
                border-radius: 50%;
                object-fit: cover;
                border: 4px solid #2c3e50;
                box-shadow: 0 6px 12px rgba(0,0,0,0.15);
                display: block;
                background: white;
              }}
              
              .photo-placeholder {{
                width: 120px;
                height: 120px;
                border-radius: 50%;
                background: linear-gradient(135deg, #ecf0f1 0%, #d5dbdb 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                color: #7f8c8d;
                font-weight: bold;
                border: 4px solid #2c3e50;
                font-size: 14px;
                box-shadow: 0 6px 12px rgba(0,0,0,0.15);
              }}
              
              /* Header Section */
              .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 3px solid #2c3e50;
              }}
              
              h1 {{ 
                font-size: 28pt;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 12px;
                letter-spacing: 1px;
              }}
              
              .contact-info {{
                font-size: 10pt;
                color: #555;
                line-height: 1.5;
                margin-top: 8px;
              }}
              
              .contact-link {{
                color: #2980b9;
                text-decoration: none;
              }}
              
              .contact-link:hover {{
                text-decoration: underline;
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
                border-bottom: 2px solid #bdc3c7;
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
                padding: 10px;
                background: #f8f9fa;
                border-left: 4px solid #3498db;
              }}
              
              /* Skills Section */
              .skills-container {{
                margin-bottom: 20px;
              }}
              
              .skill-category {{
                margin-bottom: 10px;
                font-size: 11pt;
                line-height: 1.6;
                padding: 5px 0;
              }}
              
              .skill-category strong {{
                color: #2c3e50;
                font-weight: bold;
              }}
              
              /* Experience & Education Items */
              .experience-item, .education-item, .project-item {{
                margin-bottom: 25px;
                page-break-inside: avoid;
                padding: 10px 0;
                border-bottom: 1px solid #ecf0f1;
              }}
              
              .item-header {{
                display: flex;
                justify-content: space-between;
                align-items: baseline;
                margin-bottom: 6px;
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
                font-style: italic;
              }}
              
              .item-location {{
                font-size: 10pt;
                color: #7f8c8d;
                font-style: italic;
                margin-bottom: 10px;
              }}
              
              /* Bullet Lists */
              .bullet-list {{
                margin: 12px 0 0 20px;
                padding: 0;
              }}
              
              .bullet-list li {{
                margin-bottom: 8px;
                line-height: 1.6;
                color: #444;
                font-size: 11pt;
              }}
              
              /* Projects */
              .project-desc {{
                margin: 10px 0;
                color: #444;
                line-height: 1.6;
                font-size: 11pt;
              }}
              
              .tech-stack {{
                margin-top: 10px;
                padding: 8px 12px;
                background: #f8f9fa;
                border-left: 4px solid #2980b9;
                font-size: 10pt;
                color: #555;
                border-radius: 0 4px 4px 0;
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
                  width: 100px !important;
                  height: 100px !important;
                }}
                
                h1 {{
                  font-size: 24pt;
                }}
                
                .photo-container {{
                  margin-bottom: 20px;
                }}
              }}
              
              /* Page layout */
              @page {{
                size: A4;
                margin: 0.6in;
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
    
    # Enhanced ReportLab fallback with photo support
    from reportlab.lib import colors  # type: ignore
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore
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
    
    # Add photo support for ReportLab fallback
    photo_data = data.get("photo")
    if photo_data:
        print("Processing photo for ReportLab fallback...")
        debug_photo_data(photo_data)
        
        try:
            from reportlab.platypus import Image as ReportLabImage
            from reportlab.lib.utils import ImageReader
            
            processed_photo = process_photo_for_reportlab(photo_data)
            if processed_photo:
                # Create centered photo
                photo_img = ReportLabImage(ImageReader(processed_photo), width=100, height=100)
                
                # Center the photo using a table
                photo_table = Table([[photo_img]], colWidths=[100])
                photo_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(photo_table)
                elements.append(Spacer(1, 12))
                print("Photo added to ReportLab PDF successfully")
            else:
                # Add placeholder text
                elements.append(Paragraph("<para align='center'>[Professional Photo]</para>", styles["Normal"]))
                elements.append(Spacer(1, 12))
                print("Photo placeholder added to ReportLab PDF")
        except Exception as e:
            print(f"ReportLab photo error: {e}")
            # Add placeholder text
            elements.append(Paragraph("<para align='center'>[Photo]</para>", styles["Normal"]))
            elements.append(Spacer(1, 12))

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
        
        # Handle categorized skills
        categorized_skills = {}
        uncategorized_skills = []
        
        for skill in skills:
            if ':' in skill:
                category, skill_list = skill.split(':', 1)
                categorized_skills[category.strip()] = skill_list.strip()
            else:
                uncategorized_skills.append(skill)
        
        skill_text = ""
        if categorized_skills:
            for category, skill_list in categorized_skills.items():
                skill_text += f"<b>{category}:</b> {skill_list}<br/>"
        
        if uncategorized_skills:
            skill_text += f"{', '.join(uncategorized_skills)}"
        
        if not skill_text:
            skill_text = ", ".join(skills)
        
        elements.append(Paragraph(skill_text, styles["BodyText"]))
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
            proj_name = str(proj.get("name", "")).strip()
            if not proj_name:
                continue
                
            elements.append(Paragraph(f"<b>{proj_name}</b>", styles["Normal"]))
            
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


# Example usage and utility functions
def create_sample_resume_data() -> Dict[str, Any]:
    """Create sample resume data for testing"""
    return {
        "name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "+1 (555) 123-4567",
        "location": "New York, NY",
        "links": ["https://linkedin.com/in/johndoe", "https://github.com/johndoe"],
        "summary": "Experienced software engineer with 5+ years of experience in full-stack development, specializing in Python, JavaScript, and cloud technologies. Proven track record of delivering scalable web applications and leading cross-functional teams.",
        "skills": [
            "Programming Languages: Python, JavaScript, TypeScript, Java",
            "Web Technologies: React, Node.js, Express, HTML5, CSS3",
            "Databases: PostgreSQL, MongoDB, Redis",
            "Cloud & DevOps: AWS, Docker, Kubernetes, CI/CD"
        ],
        "experience": [
            {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "location": "New York, NY",
                "start": "2021-03",
                "end": "present",
                "bullets": [
                    "Led development of microservices architecture serving 1M+ users",
                    "Implemented CI/CD pipelines reducing deployment time by 60%",
                    "Mentored 3 junior developers and conducted code reviews"
                ]
            },
            {
                "title": "Software Engineer",
                "company": "StartupXYZ",
                "location": "San Francisco, CA",
                "start": "2019-01",
                "end": "2021-02",
                "bullets": [
                    "Built full-stack web applications using React and Node.js",
                    "Optimized database queries improving performance by 40%",
                    "Collaborated with product team on feature requirements"
                ]
            }
        ],
        "education": [
            {
                "degree": "Bachelor of Science in Computer Science",
                "school": "University of Technology",
                "location": "Boston, MA",
                "year": "2018",
                "details": [
                    "Magna Cum Laude, GPA: 3.8/4.0",
                    "Relevant Coursework: Data Structures, Algorithms, Database Systems"
                ]
            }
        ],
        "projects": [
            {
                "name": "E-commerce Platform",
                "description": "Built a full-featured e-commerce platform with payment processing, inventory management, and user authentication.",
                "tech": ["React", "Node.js", "PostgreSQL", "Stripe API"]
            }
        ],
        "certifications": [
            "AWS Certified Solutions Architect - Associate",
            "Certified Kubernetes Administrator (CKA)"
        ]
    }


def create_sample_job_requirements() -> Dict[str, Any]:
    """Create sample job requirements for gap analysis"""
    return {
        "skills": [
            "Python", "JavaScript", "React", "Node.js", "AWS",
            "Docker", "PostgreSQL", "Git", "Agile", "REST APIs"
        ],
        "experience_years": 5,
        "education_level": "Bachelor's",
        "certifications": ["AWS", "Scrum Master"]
    }


# Main execution functions
def generate_comprehensive_report(
    resume_data: Dict[str, Any],
    job_requirements: Optional[Dict[str, Any]] = None,
    candidate_name: Optional[str] = None,
    match_score: float = 85.0,
    confidence: float = 0.89
) -> bytes:
    """Generate comprehensive PDF report with gap analysis"""
    
    # Perform gap analysis
    gap_analysis = comprehensive_gap_analysis(resume_data, job_requirements)
    
    # Generate explanation based on gaps
    total_gaps = sum(len(gaps) for gaps in gap_analysis.values() if isinstance(gaps, list))
    high_severity = sum(1 for gap_list in gap_analysis.values() 
                       if isinstance(gap_list, list) 
                       for gap in gap_list 
                       if gap.get('severity') == 'high')
    
    if total_gaps == 0:
        explanation = "This candidate demonstrates a comprehensive and well-rounded profile with strong alignment across all key areas. No significant gaps were identified in their background."
    elif high_severity > 2:
        explanation = f"While this candidate shows promise, there are {high_severity} high-priority areas that need attention. The gaps primarily relate to missing critical skills, education requirements, or significant experience discontinuities."
    else:
        explanation = f"This candidate presents a solid overall profile with {total_gaps} minor areas for improvement. Most gaps are addressable through training or additional experience."
    
    # Extract missing skills from gap analysis
    missing_skills = []
    for gap_list in gap_analysis.values():
        if isinstance(gap_list, list):
            for gap in gap_list:
                if gap.get('type') == 'job_requirements' and 'Missing required skills:' in gap.get('description', ''):
                    skills_part = gap['description'].split('Missing required skills: ')[1]
                    missing_skills.extend([s.strip() for s in skills_part.split(',')])
    
    # Generate top snippets (mock data for demonstration)
    top_snippets = [
        ("Experienced software engineer with 5+ years of experience", 0.95),
        ("Led development of microservices architecture serving 1M+ users", 0.92),
        ("AWS Certified Solutions Architect - Associate", 0.88),
        ("Built full-stack web applications using React and Node.js", 0.85),
        ("Bachelor of Science in Computer Science", 0.82)
    ]
    
    return generate_pdf_report(
        candidate_name=candidate_name or resume_data.get("name", "Unknown Candidate"),
        match_score=match_score,
        confidence=confidence,
        explanation=explanation,
        missing_skills=missing_skills,
        top_snippets=top_snippets,
        gap_analysis=gap_analysis
    )


if __name__ == "__main__":
    # Example usage
    sample_data = create_sample_resume_data()
    job_reqs = create_sample_job_requirements()
    
    # Generate ATS resume
    resume_pdf = generate_ats_resume_pdf(sample_data)
    with open("sample_resume.pdf", "wb") as f:
        f.write(resume_pdf)
    print("Generated sample_resume.pdf")
    
    # Generate comprehensive report with gap analysis
    report_pdf = generate_comprehensive_report(
        resume_data=sample_data,
        job_requirements=job_reqs,
        candidate_name="John Doe",
        match_score=87.5,
        confidence=0.91
    )
    with open("comprehensive_report.pdf", "wb") as f:
        f.write(report_pdf)
    print("Generated comprehensive_report.pdf with gap analysis")
    
    # Demo gap analysis
    gaps = comprehensive_gap_analysis(sample_data, job_reqs)
    print("\nGap Analysis Results:")
    for gap_type, gap_list in gaps.items():
        print(f"\n{gap_type.replace('_', ' ').title()}:")
        if isinstance(gap_list, list) and gap_list:
            for gap in gap_list:
                severity = gap.get('severity', 'unknown')
                print(f"  [{severity.upper()}] {gap.get('description', 'No description')}")
        else:
            print("  No gaps identified")