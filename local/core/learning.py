"""
Module d'Auto-Apprentissage & Compétences — Inspiré de Hermes Agent (Nous Research)
Permet à JARVIS de créer, affiner et persister de nouvelles compétences apprises au fil des interactions.
"""

import sqlite3
import os

DB_PATH = os.path.expanduser("~/jarvis/memory.db")

def init_learning_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger TEXT UNIQUE,
                action_type TEXT,
                instruction TEXT,
                usage_count INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def learn_skill(trigger: str, instruction: str, action_type: str = "custom") -> str:
    """Enregistre une nouvelle compétence inspirée du learning loop de Hermes."""
    init_learning_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO learned_skills (trigger, action_type, instruction, usage_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(trigger) DO UPDATE SET 
                instruction=excluded.instruction, 
                usage_count=usage_count + 1
        """, (trigger.lower().strip(), action_type, instruction))
        conn.commit()
    return f"Compétence Hermes apprise pour : '{trigger}'"

def get_learned_skills() -> list:
    init_learning_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT trigger, instruction, usage_count FROM learned_skills ORDER BY usage_count DESC")
        return cursor.fetchall()
