import random
from database import get_connection


def select_questions(subject, units, difficulty_ratio, mcq_count, short_count, long_count,
                     mcq_marks=1, short_marks=4, long_marks=10):
    """
    Selects questions from the database based on given parameters.
    Respects manual MCQ, Short, Long counts entered by faculty.
    difficulty_ratio: dict like {"Easy": 40, "Medium": 40, "Hard": 20}
    mcq_marks, short_marks, long_marks: marks to assign per question type (overrides DB values)
    Returns a list of question dicts.
    """
    conn = get_connection()
    cursor = conn.cursor()
    selected = []
    used_ids = set()

    # Marks override map
    marks_map = {"MCQ": mcq_marks, "Short": short_marks, "Long": long_marks}

    def fetch_questions(q_type, difficulty, count):
        placeholders = ','.join('?' for _ in units)
        cursor.execute(f'''
            SELECT * FROM questions
            WHERE subject=? AND question_type=? AND difficulty=? AND unit IN ({placeholders})
        ''', [subject, q_type, difficulty] + units)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        questions = [dict(zip(columns, row)) for row in rows if row[0] not in used_ids]
        random.shuffle(questions)
        chosen = questions[:count]
        for q in chosen:
            used_ids.add(q['id'])
        return chosen

    def fill_remaining(q_type, count):
        """Fallback: pick any question of this type regardless of difficulty."""
        placeholders = ','.join('?' for _ in units)
        cursor.execute(f'''
            SELECT * FROM questions
            WHERE subject=? AND question_type=? AND unit IN ({placeholders})
        ''', [subject, q_type] + units)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        extras = [dict(zip(columns, row)) for row in rows if row[0] not in used_ids]
        random.shuffle(extras)
        chosen = extras[:count]
        for q in chosen:
            used_ids.add(q['id'])
        return chosen

    def split_by_difficulty(count, ratio):
        easy   = round(count * ratio.get("Easy", 0) / 100)
        hard   = round(count * ratio.get("Hard", 0) / 100)
        medium = count - easy - hard
        return {"Easy": easy, "Medium": medium, "Hard": hard}

    for q_type, count in [("MCQ", mcq_count), ("Short", short_count), ("Long", long_count)]:
        if count == 0:
            continue
        split = split_by_difficulty(count, difficulty_ratio)
        type_selected = []
        for difficulty, d_count in split.items():
            if d_count > 0:
                fetched = fetch_questions(q_type, difficulty, d_count)
                type_selected.extend(fetched)

        # Fallback if not enough questions found
        if len(type_selected) < count:
            remaining = count - len(type_selected)
            type_selected.extend(fill_remaining(q_type, remaining))

        # Override marks with faculty-specified values
        for q in type_selected:
            q['marks'] = marks_map[q_type]

        selected.extend(type_selected)

    conn.close()

    actual_marks = sum(q['marks'] for q in selected)
    print(f"[Engine] Selected {len(selected)} questions, Total marks: {actual_marks}")
    return selected


def validate_marks(questions, total_marks):
    """Check if selected questions total marks match expected total."""
    actual = sum(q['marks'] for q in questions)
    return actual, actual == total_marks