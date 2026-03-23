from groq import Groq
import json
import re

def extract_text_from_file(filepath):
    ext = filepath.lower().split(".")[-1]
    if ext == "txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == "pdf":
        try:
            import fitz
            doc = fitz.open(filepath)
            return "".join([page.get_text() for page in doc])
        except ImportError:
            return "[ERROR] Run: pip install pymupdf"
    elif ext in ["docx", "doc"]:
        try:
            from docx import Document
            doc = Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        except ImportError:
            return "[ERROR] Run: pip install python-docx"
    return "[ERROR] Unsupported file format."


def generate_questions_with_ai(topic_text, subject, unit, levels, mcq_per_level, short_per_level, long_per_level, api_key):
    client = Groq(api_key=api_key)

    # Clean and trim topic text
    topic_text = topic_text.strip()
    if not topic_text or len(topic_text) < 50:
        print("[AI] Warning: Topic text is too short or empty!")
        return []

    # Use more of the content
    content_chunk = topic_text[:4000]

    prompt = f"""You are an expert university professor creating exam questions.

STRICT RULE: Every single question you generate MUST be directly based on the content provided below. 
Do NOT generate generic questions. Do NOT use your general knowledge.
ONLY use facts, concepts, definitions, and ideas found in the content below.

=== SUBJECT: {subject} ===
=== UNIT/TOPIC: {unit} ===

=== CONTENT TO USE (generate questions ONLY from this) ===
{content_chunk}
=== END OF CONTENT ===

Now generate questions at these Bloom's Taxonomy levels: {", ".join(levels)}

Rules:
- Remember ({mcq_per_level} MCQ, 1 mark): Ask students to recall specific facts, terms, definitions FROM THE CONTENT ABOVE
- Understand ({short_per_level} Short Answer, 4 marks): Ask students to explain concepts FROM THE CONTENT ABOVE
- Apply ({short_per_level} Short Answer, 4 marks): Ask students to apply concepts FROM THE CONTENT ABOVE to new situations
- Analyze ({long_per_level} Long Answer, 7 marks): Ask students to compare or differentiate concepts FROM THE CONTENT ABOVE
- Evaluate ({long_per_level} Long Answer, 7 marks): Ask students to justify or assess ideas FROM THE CONTENT ABOVE
- Create ({long_per_level} Long Answer, 10 marks): Ask students to design or propose something based on concepts FROM THE CONTENT ABOVE

For MCQ questions, options must be plausible and based on the content.

Return ONLY a valid JSON array. No markdown. No explanation. No code blocks. Just the raw JSON:
[
  {{"blooms_level": "Remember", "question_type": "MCQ", "question_text": "According to the content, what is...?", "marks": 1, "option_a": "...", "option_b": "...", "option_c": "...", "option_d": "...", "answer": "A"}},
  {{"blooms_level": "Understand", "question_type": "Short", "question_text": "Explain the concept of... as described in the content.", "marks": 4, "option_a": null, "option_b": null, "option_c": null, "option_d": null, "answer": null}}
]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict exam question generator. You ONLY generate questions based on the exact content provided by the user. Never use outside knowledge."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=4000,
            temperature=0.3  # Lower temperature = more focused on content
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()

        # Find JSON array in response
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            raw = raw[start:end]

        questions = json.loads(raw)
        for q in questions:
            q["subject"] = subject
            q["unit"] = unit
        print(f"[AI] Generated {len(questions)} questions from content.")
        return questions
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

    saved = 0
    for q in questions:
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
            saved += 1
        except Exception as e:
            print(f"[DB] Error: {e}")
    conn.commit()
    return saved


def blooms_to_difficulty(level):
    return {"Remember": "Easy", "Understand": "Easy", "Apply": "Medium",
            "Analyze": "Medium", "Evaluate": "Hard", "Create": "Hard"}.get(level, "Medium")
