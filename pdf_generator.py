from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os


def generate_pdf(output_path, config, questions):
    # Override marks from config if provided
    mcq_marks   = config.get('mcq_marks', None)
    short_marks = config.get('short_marks', None)
    long_marks  = config.get('long_marks', None)

    type_marks = {}
    if mcq_marks:   type_marks['MCQ']   = mcq_marks
    if short_marks: type_marks['Short'] = short_marks
    if long_marks:  type_marks['Long']  = long_marks

    # Apply configured marks to all questions
    for q in questions:
        if q['question_type'] in type_marks:
            q['marks'] = type_marks[q['question_type']]
    """
    Generates a formatted question paper PDF.
    config: dict with keys - college_name, subject, exam_type, total_marks, duration, date, units
    questions: list of question dicts from the selection engine
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # Custom styles
    college_style = ParagraphStyle('College', fontSize=14, fontName='Helvetica-Bold',
                                    alignment=TA_CENTER, spaceAfter=2)
    title_style = ParagraphStyle('Title', fontSize=11, fontName='Helvetica-Bold',
                                  alignment=TA_CENTER, spaceAfter=2)
    sub_style = ParagraphStyle('Sub', fontSize=10, fontName='Helvetica',
                                alignment=TA_CENTER, spaceAfter=4)
    section_style = ParagraphStyle('Section', fontSize=11, fontName='Helvetica-Bold',
                                    spaceBefore=12, spaceAfter=6,
                                    textColor=colors.HexColor('#1a1a2e'))
    question_style = ParagraphStyle('Question', fontSize=10, fontName='Helvetica',
                                     spaceBefore=4, spaceAfter=2, leading=14)
    option_style = ParagraphStyle('Option', fontSize=10, fontName='Helvetica',
                                   leftIndent=20, spaceAfter=1, leading=12)
    marks_style = ParagraphStyle('Marks', fontSize=9, fontName='Helvetica-Oblique',
                                  alignment=TA_RIGHT)

    story = []

    # ── HEADER ──────────────────────────────────────────────
    story.append(Paragraph(config.get('college_name', 'Your College Name'), college_style))
    story.append(Paragraph("Department of Computer Science & Engineering", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.black))
    story.append(Spacer(1, 6))

    # Exam info table
    exam_data = [
        ["Subject:", config['subject'], "Exam Type:", config['exam_type']],
        ["Total Marks:", str(config['total_marks']), "Duration:", f"{config['duration']} Minutes"],
        ["Date:", config.get('date', datetime.now().strftime("%d-%m-%Y")),
         "Units Covered:", ", ".join(config.get('units', []))],
    ]
    info_table = Table(exam_data, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 4))

    # Instructions
    story.append(Paragraph("<b>Instructions:</b> Answer all questions. Each question carries marks as indicated.", question_style))
    story.append(Spacer(1, 8))

    # ── QUESTIONS BY SECTION ────────────────────────────────
    sections = [
        ("SECTION A — Multiple Choice Questions (MCQ)", "MCQ"),
        ("SECTION B — Short Answer Questions", "Short"),
        ("SECTION C — Long Answer Questions", "Long"),
    ]

    for section_title, q_type in sections:
        section_qs = [q for q in questions if q['question_type'] == q_type]
        if not section_qs:
            continue

        story.append(Paragraph(section_title, section_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Spacer(1, 4))

        for i, q in enumerate(section_qs, 1):
            # Question text with marks
            q_text = f"<b>Q{i}.</b> {q['question_text']}"
            marks_text = f"[{q['marks']} Mark{'s' if q['marks'] > 1 else ''}]"

            row = Table(
                [[Paragraph(q_text, question_style), Paragraph(marks_text, marks_style)]],
                colWidths=[14*cm, 3.5*cm]
            )
            row.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            story.append(row)

            # MCQ options
            if q_type == "MCQ":
                options = [
                    ('A', q.get('option_a')),
                    ('B', q.get('option_b')),
                    ('C', q.get('option_c')),
                    ('D', q.get('option_d')),
                ]
                for opt_label, opt_text in options:
                    if opt_text:
                        story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;({opt_label}) {opt_text}", option_style))

            story.append(Spacer(1, 8))

    # ── FOOTER ──────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    total = sum(q['marks'] for q in questions)
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Total Marks: {total} &nbsp;&nbsp;&nbsp; Total Questions: {len(questions)}</b>",
                            ParagraphStyle('Footer', fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)))
    story.append(Spacer(1, 6))
    story.append(Paragraph("— End of Question Paper —",
                            ParagraphStyle('End', fontSize=9, fontName='Helvetica-Oblique', alignment=TA_CENTER,
                                           textColor=colors.grey)))

    doc.build(story)
    print(f"[PDF] Question paper saved to: {output_path}")


def generate_answer_key_pdf(output_path, config, questions, api_key=None):
    """
    Generates a formatted Answer Key / Answer Schema PDF.
    Lists every question with its correct answer / model answer.
    config: same dict as generate_pdf
    questions: same list of question dicts
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    # ── Custom styles ──────────────────────────────────────
    college_style = ParagraphStyle('AKCollege', fontSize=14, fontName='Helvetica-Bold',
                                    alignment=TA_CENTER, spaceAfter=2)
    sub_style     = ParagraphStyle('AKSub', fontSize=10, fontName='Helvetica',
                                    alignment=TA_CENTER, spaceAfter=4)
    badge_style   = ParagraphStyle('AKBadge', fontSize=12, fontName='Helvetica-Bold',
                                    alignment=TA_CENTER, spaceAfter=6,
                                    textColor=colors.HexColor('#c0392b'))
    section_style = ParagraphStyle('AKSection', fontSize=11, fontName='Helvetica-Bold',
                                    spaceBefore=12, spaceAfter=6,
                                    textColor=colors.HexColor('#1a1a2e'))
    q_style       = ParagraphStyle('AKQuestion', fontSize=10, fontName='Helvetica',
                                    spaceBefore=4, spaceAfter=2, leading=14)
    ans_style     = ParagraphStyle('AKAnswer', fontSize=10, fontName='Helvetica-Bold',
                                    leftIndent=20, spaceAfter=4, leading=13,
                                    textColor=colors.HexColor('#1a6f1a'))
    hint_style    = ParagraphStyle('AKHint', fontSize=9, fontName='Helvetica-Oblique',
                                    leftIndent=20, spaceAfter=6, leading=12,
                                    textColor=colors.HexColor('#555555'))
    marks_style   = ParagraphStyle('AKMarks', fontSize=9, fontName='Helvetica-Oblique',
                                    alignment=TA_RIGHT)
    footer_style  = ParagraphStyle('AKFooter', fontSize=10, fontName='Helvetica-Bold',
                                    alignment=TA_CENTER)
    end_style     = ParagraphStyle('AKEnd', fontSize=9, fontName='Helvetica-Oblique',
                                    alignment=TA_CENTER, textColor=colors.grey)

    story = []

    # ── HEADER ─────────────────────────────────────────────
    story.append(Paragraph(config.get('college_name', 'Your College Name'), college_style))
    story.append(Paragraph("Department of Computer Science & Engineering", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.black))
    story.append(Spacer(1, 4))
    story.append(Paragraph("✦ ANSWER KEY / ANSWER SCHEMA ✦", badge_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#c0392b')))
    story.append(Spacer(1, 6))

    # Exam info table (same layout as question paper for easy matching)
    exam_data = [
        ["Subject:", config['subject'],      "Exam Type:",    config['exam_type']],
        ["Total Marks:", str(config['total_marks']), "Duration:", f"{config['duration']} Minutes"],
        ["Date:", config.get('date', datetime.now().strftime("%d-%m-%Y")),
         "Units Covered:", ", ".join(config.get('units', []))],
    ]
    info_table = Table(exam_data, colWidths=[3.5*cm, 6*cm, 3.5*cm, 5*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 8))

    # ── CONFIDENTIAL watermark notice ───────────────────────
    story.append(Paragraph(
        "<b>CONFIDENTIAL — For Examiner Use Only. Do not distribute to students.</b>",
        ParagraphStyle('Conf', fontSize=9, fontName='Helvetica-Bold',
                       alignment=TA_CENTER, textColor=colors.HexColor('#c0392b'),
                       spaceAfter=10)
    ))

    # ── ANSWERS BY SECTION ──────────────────────────────────
    sections = [
        ("SECTION A — Multiple Choice Questions (MCQ)", "MCQ"),
        ("SECTION B — Short Answer Questions",          "Short"),
        ("SECTION C — Long Answer Questions",           "Long"),
    ]

    # Apply marks overrides (same as question paper)
    mcq_marks   = config.get('mcq_marks')
    short_marks = config.get('short_marks')
    long_marks  = config.get('long_marks')
    type_marks  = {}
    if mcq_marks:   type_marks['MCQ']   = mcq_marks
    if short_marks: type_marks['Short'] = short_marks
    if long_marks:  type_marks['Long']  = long_marks
    for q in questions:
        if q['question_type'] in type_marks:
            q['marks'] = type_marks[q['question_type']]

    # AI-generated model answers for short/long questions
    ai_answers = {}
    if api_key:
        try:
            from ai_generator import generate_answers_for_questions
            ai_answers = generate_answers_for_questions(questions, config.get('subject', ''), api_key)
        except Exception as e:
            print(f"[PDF] AI answer generation skipped: {e}")

    q_global = 0  # running question counter across sections
    for section_title, q_type in sections:
        section_qs = [q for q in questions if q['question_type'] == q_type]
        if not section_qs:
            continue

        story.append(Paragraph(section_title, section_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Spacer(1, 4))

        for i, q in enumerate(section_qs, 1):
            q_global += 1
            q_text    = f"<b>Q{i}.</b> {q['question_text']}"
            marks_txt = f"[{q['marks']} Mark{'s' if q['marks'] > 1 else ''}]"

            # Question row
            row_table = Table(
                [[Paragraph(q_text, q_style), Paragraph(marks_txt, marks_style)]],
                colWidths=[14*cm, 3.5*cm]
            )
            row_table.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ]))
            story.append(row_table)

            answer = (q.get('answer') or '').strip()

            if q_type == "MCQ":
                # Show all options, highlight the correct one
                option_map = {
                    'A': q.get('option_a'), 'B': q.get('option_b'),
                    'C': q.get('option_c'), 'D': q.get('option_d'),
                }
                correct_key = answer.upper() if answer else None
                for opt_label, opt_text in option_map.items():
                    if not opt_text:
                        continue
                    is_correct = (opt_label == correct_key)
                    prefix = "✔ " if is_correct else "    "
                    opt_color = colors.HexColor('#1a6f1a') if is_correct else colors.HexColor('#444444')
                    opt_font  = 'Helvetica-Bold' if is_correct else 'Helvetica'
                    story.append(Paragraph(
                        f"{prefix}({opt_label}) {opt_text}",
                        ParagraphStyle(f'Opt{opt_label}', fontSize=10,
                                       fontName=opt_font, leftIndent=20,
                                       spaceAfter=1, leading=12,
                                       textColor=opt_color)
                    ))
                # Explicit correct answer line
                correct_text = option_map.get(correct_key, '') if correct_key else ''
                if correct_key and correct_text:
                    story.append(Paragraph(
                        f"<b>Correct Answer: ({correct_key}) {correct_text}</b>",
                        ans_style
                    ))
                elif not answer:
                    story.append(Paragraph("<i>Correct Answer: Not specified</i>", hint_style))

            else:
                # Short / Long — use AI-generated answer if available, else stored answer, else refer note
                q_text_key = q.get("question_text", "")
                generated  = ai_answers.get(q_text_key, "").strip()
                stored_ans = (q.get("answer") or "").strip()
                final_ans  = generated or stored_ans

                if final_ans:
                    label = "Model Answer:" if q_type == "Short" else "Answer Scheme:"
                    story.append(Paragraph(f"<b>{label}</b>", hint_style))
                    story.append(Paragraph(final_ans, ans_style))
                    if generated:
                        story.append(Paragraph(
                            "<i>(AI-generated model answer — verify against course material)</i>",
                            ParagraphStyle("AKAINote", fontSize=8, fontName="Helvetica-Oblique",
                                           leftIndent=20, textColor=colors.HexColor("#888888"),
                                           spaceAfter=4)
                        ))
                else:
                    if q_type == "Short":
                        story.append(Paragraph(
                            "<i>Refer to textbook / course PDF / module notes for model answer.</i>",
                            hint_style
                        ))
                    else:
                        story.append(Paragraph(
                            "<i>Refer to textbook / course PDF / module notes for answer scheme. "
                            "Award marks based on coverage of key concepts, diagrams, and examples.</i>",
                            hint_style
                        ))

            # Bloom's level tag if present
            blooms = q.get('blooms_level') or q.get('bloom_level') or ''
            if blooms:
                story.append(Paragraph(
                    f"<i>Bloom's Level: {blooms} &nbsp;|&nbsp; Difficulty: {q.get('difficulty','—')}</i>",
                    ParagraphStyle('BL', fontSize=8, fontName='Helvetica-Oblique',
                                   leftIndent=20, textColor=colors.HexColor('#888888'),
                                   spaceAfter=6)
                ))

            story.append(Spacer(1, 8))

    # ── QUICK REFERENCE TABLE (MCQ only) ────────────────────
    mcq_qs = [q for q in questions if q['question_type'] == 'MCQ']
    if mcq_qs:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
        story.append(Spacer(1, 6))
        story.append(Paragraph("MCQ Quick Reference", section_style))

        # Build rows of 5 Q-Answer pairs per row for compact layout
        ref_data = [["Q.No", "Answer"] * 5]
        chunk = []
        for idx, q in enumerate(mcq_qs, 1):
            ans = (q.get('answer') or '—').upper()
            chunk.append(str(idx))
            chunk.append(ans)
            if len(chunk) == 10:
                ref_data.append(chunk)
                chunk = []
        if chunk:
            # Pad incomplete last row
            while len(chunk) < 10:
                chunk.append('')
            ref_data.append(chunk)

        ref_table = Table(ref_data, colWidths=[1.35*cm] * 10)
        ref_table.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, 0),  colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
            ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTNAME',     (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',     (0, 0), (-1, -1), 9),
            ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',         (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ]))
        story.append(ref_table)
        story.append(Spacer(1, 8))

    # ── FOOTER ──────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    total = sum(q['marks'] for q in questions)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>Total Marks: {total} &nbsp;&nbsp;&nbsp; Total Questions: {len(questions)}</b>",
        footer_style
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph("— End of Answer Key —", end_style))

    doc.build(story)
    print(f"[PDF] Answer key saved to: {output_path}")