from groq import Groq
import json
import re


# ── FIX 1: Clean extracted text to remove metadata/headers ───
def clean_extracted_text(text):
    """
    Removes syllabus metadata, module headers, hour counts, assessment patterns
    and other non-content lines that confuse the AI into generating wrong questions.
    """
    lines = text.split('\n')
    cleaned = []

    # Patterns to skip — these are syllabus/course structure lines, not content
    skip_patterns = [
        r'^\s*module[\s\-]*\d',           # Module-1, Module 2 etc
        r'^\s*unit[\s\-]*\d',             # Unit 1, Unit-2
        r'hours?\s*:?\s*\d',              # Hours: 8, 6 hours
        r'^\s*\d+\s*hours?',              # 8 hours
        r'sl\.?\s*no',                    # Sl. No
        r'assessment\s*pattern',          # Assessment pattern
        r'total\s*marks',                 # Total marks
        r'cie\s*marks',                   # CIE marks
        r'see\s*marks',                   # SEE marks
        r'credits?\s*:',                  # Credits:
        r'l:t:p',                         # L:T:P:S
        r'course\s*(code|name|title)',    # Course code/name
        r'prerequisite',                  # Prerequisites
        r'^\s*text\s*book',               # Text book
        r'^\s*reference',                 # References
        r'^\s*co\s*\d',                   # CO1, CO2
        r'course\s*outcome',              # Course outcomes
        r'^\s*\d+\.\s*$',                # Lone numbers
        r'^\s*[-–—]+\s*$',               # Separator lines
        r'jdk|jre|jvm\s*(purpose|install|download)',  # JDK/JRE metadata
        r'^\s*topics?\s*to\s*be\s*covered',
        r'^\s*syllabus',
    ]

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        # Skip short lines that are likely headers (less than 15 chars)
        if len(line_stripped) < 15 and not any(c.isalpha() for c in line_stripped[5:]):
            continue
        # Skip lines matching metadata patterns
        if any(re.search(p, line_stripped, re.IGNORECASE) for p in skip_patterns):
            continue
        cleaned.append(line)

    return '\n'.join(cleaned)


def extract_text_from_file(filepath):
    ext = filepath.lower().split(".")[-1]
    if ext == "txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == "pdf":
        try:
            import fitz
            doc = fitz.open(filepath)
            # FIX 2: Extract more pages and clean text
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            return full_text
        except ImportError:
            return "[ERROR] Run: pip install pymupdf"
    elif ext in ["docx", "doc"]:
        try:
            from docx import Document
            doc = Document(filepath)
            # Include table text as well for richer content
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text += "\n" + cell.text.strip()
            return text
        except ImportError:
            return "[ERROR] Run: pip install python-docx"
    return "[ERROR] Unsupported file format."


# ── FIX 3: Duplicate detection ────────────────────────────────
def is_duplicate(new_q, existing_questions, threshold=0.75):
    """
    Returns True if new_q is too similar to any existing question.
    Uses simple word overlap ratio to detect near-duplicates.
    """
    def word_set(text):
        return set(re.sub(r'[^\w\s]', '', text.lower()).split())

    new_words = word_set(new_q.get("question_text", ""))
    if not new_words:
        return False

    for eq in existing_questions:
        existing_words = word_set(eq.get("question_text", ""))
        if not existing_words:
            continue
        overlap = len(new_words & existing_words) / max(len(new_words), len(existing_words))
        if overlap >= threshold:
            print(f"[AI] Duplicate detected: '{new_q['question_text'][:60]}...'")
            return True
    return False


def generate_questions_with_ai(topic_text, subject, unit, levels, mcq_per_level, short_per_level, long_per_level, api_key):
    client = Groq(api_key=api_key)

    # Clean and trim topic text
    topic_text = topic_text.strip()
    if not topic_text or len(topic_text) < 50:
        print("[AI] Warning: Topic text is too short or empty!")
        return []

    # FIX 1: Clean metadata/headers before sending to AI
    cleaned_text = clean_extracted_text(topic_text)
    print(f"[AI] Original text: {len(topic_text)} chars → Cleaned: {len(cleaned_text)} chars")

    if len(cleaned_text.strip()) < 100:
        print("[AI] Warning: Cleaned text too short, using original.")
        cleaned_text = topic_text

    # FIX 2: Use up to 6000 chars (larger chunk for better question quality)
    content_chunk = cleaned_text[:6000]

    prompt = f"""You are an expert university professor creating exam questions.

CRITICAL RULES — YOU MUST FOLLOW ALL OF THESE:
1. Every question MUST be based ONLY on the actual concepts, definitions, and explanations in the content below.
2. Do NOT ask questions about syllabus structure, module numbers, hours, marks, credits, or course patterns.
3. Do NOT ask "what is the purpose of JDK/JRE" or similar tool/setup questions UNLESS the content explicitly explains them in detail.
4. Do NOT repeat or paraphrase the same question twice — every question must be completely unique.
5. Do NOT use your general knowledge — ONLY use what is written in the content.
6. Questions must test understanding of the TOPIC CONCEPTS, not the document structure.

=== SUBJECT: {subject} ===
=== UNIT/TOPIC: {unit} ===

=== CONTENT (generate questions ONLY from the concepts explained here) ===
{content_chunk}
=== END OF CONTENT ===

Generate questions at these Bloom's Taxonomy levels: {", ".join(levels)}

Question type rules:
- Remember ({mcq_per_level} MCQ, 1 mark each): Recall specific facts, terms, definitions from the content. MCQ options must all be plausible.
- Understand ({short_per_level} Short Answer, 4 marks each): Explain concepts from the content in own words.
- Apply ({short_per_level} Short Answer, 4 marks each): Apply concepts from the content to solve a problem or new situation.
- Analyze ({long_per_level} Long Answer, 7 marks each): Compare, differentiate, or break down concepts from the content.
- Evaluate ({long_per_level} Long Answer, 7 marks each): Justify, assess, or critique ideas from the content.
- Create ({long_per_level} Long Answer, 10 marks each): Design, propose, or construct something using concepts from the content.

Return ONLY a valid JSON array. No markdown. No explanation. No code blocks. Just raw JSON:
[
  {{"blooms_level": "Remember", "question_type": "MCQ", "question_text": "...", "marks": 1, "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...", "answer": "A"}},
  {{"blooms_level": "Understand", "question_type": "Short", "question_text": "...", "marks": 4, "option_a": null, "option_b": null, "option_c": null, "option_d": null, "answer": null}}
]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict university exam question generator. "
                        "You ONLY generate questions based on the actual topic concepts in the content provided. "
                        "You NEVER ask about syllabus structure, module numbers, hours, credits, or course patterns. "
                        "You NEVER generate duplicate or near-duplicate questions. "
                        "Every question must be completely unique and test a different concept."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=4000,
            temperature=0.4
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        # Find JSON array in response
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            raw = raw[start:end]

        questions = json.loads(raw)

        # FIX 3: Remove duplicates from the generated list itself
        unique_questions = []
        for q in questions:
            if not is_duplicate(q, unique_questions):
                q["subject"] = subject
                q["unit"] = unit
                unique_questions.append(q)
            else:
                print(f"[AI] Skipped duplicate: {q.get('question_text', '')[:50]}")

        print(f"[AI] Generated {len(questions)} questions → {len(unique_questions)} unique after dedup.")
        return unique_questions

    except Exception as e:
        print(f"[AI] Error: {e}")
        return []


def save_ai_questions_to_db(questions, conn):
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE questions ADD COLUMN blooms_level TEXT DEFAULT "Remember"')
        conn.commit()
    except Exception:
        pass

    # FIX 3: Also check against existing DB questions before saving
    cursor.execute("SELECT question_text FROM questions")
    existing_in_db = [{"question_text": row[0]} for row in cursor.fetchall()]

    saved = 0
    skipped = 0
    for q in questions:
        # Skip if too similar to something already in DB
        if is_duplicate(q, existing_in_db, threshold=0.80):
            print(f"[DB] Skipped (already in DB): {q.get('question_text', '')[:50]}")
            skipped += 1
            continue
        try:
            cursor.execute('''
                INSERT INTO questions (subject, unit, question_text, question_type,
                difficulty, marks, option_a, option_b, option_c, option_d, answer, blooms_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                q.get("subject", ""), q.get("unit", ""), q.get("question_text", ""),
                q.get("question_type", "MCQ"), blooms_to_difficulty(q.get("blooms_level", "Remember")),
                q.get("marks", 1), q.get("option_a"), q.get("option_b"),
                q.get("option_c"), q.get("option_d"), q.get("answer"), q.get("blooms_level", "Remember")
            ))
            existing_in_db.append({"question_text": q.get("question_text", "")})
            saved += 1
        except Exception as e:
            print(f"[DB] Error: {e}")

    conn.commit()
    print(f"[DB] Saved: {saved}, Skipped (duplicates): {skipped}")
    return saved


def blooms_to_difficulty(level):
    return {"Remember": "Easy", "Understand": "Easy", "Apply": "Medium",
            "Analyze": "Medium", "Evaluate": "Hard", "Create": "Hard"}.get(level, "Medium")