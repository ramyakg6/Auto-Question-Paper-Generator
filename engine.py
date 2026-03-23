import random
import sqlite3
from database import get_connection


def select_questions(subject, units, difficulty_ratio, mcq_count, short_count, long_count):
    """
    Selects questions from the database based on given parameters.
    
    difficulty_ratio: dict like {"Easy": 40, "Medium": 40, "Hard": 20} (percentages)
    Returns a list of question dicts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    total_q = mcq_count + short_count + long_count
    selected = []
    used_ids = set()

    def fetch_questions(q_type, difficulty, count, units):
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

    # Calculate difficulty split for each type
    def split_by_difficulty(count, ratio):
        easy = round(count * ratio.get("Easy", 0) / 100)
        hard = round(count * ratio.get("Hard", 0) / 100)
        medium = count - easy - hard
        return {"Easy": easy, "Medium": medium, "Hard": hard}

    for q_type, count in [("MCQ", mcq_count), ("Short", short_count), ("Long", long_count)]:
        if count == 0:
            continue
        split = split_by_difficulty(count, difficulty_ratio)
        for difficulty, d_count in split.items():
            if d_count > 0:
                fetched = fetch_questions(q_type, difficulty, d_count, units)
                selected.extend(fetched)
                # If not enough questions, fill with any difficulty
                if len(fetched) < d_count:
                    remaining = d_count - len(fetched)
                    placeholders = ','.join('?' for _ in units)
                    cursor.execute(f'''
                        SELECT * FROM questions
                        WHERE subject=? AND question_type=? AND unit IN ({placeholders})
                    ''', [subject, q_type] + units)
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    extras = [dict(zip(columns, row)) for row in rows if row[0] not in used_ids]
                    random.shuffle(extras)
                    for q in extras[:remaining]:
                        used_ids.add(q['id'])
                        selected.append(q)

    conn.close()
    return selected


def validate_marks(questions, total_marks):
    """Check if selected questions' total marks match expected total."""
    actual = sum(q['marks'] for q in questions)
    return actual, actual == total_marks