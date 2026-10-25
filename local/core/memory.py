"""
Module Mémoire Persistante Locale — Inspiré d'OpenJarvis
Gère la mémoire sémantique et les faits mémorisés de session en session.
"""

import json
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.expanduser("~/jarvis/memory.db")

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Table des faits permanents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT DEFAULT 'general',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Table de l'historique des requêtes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Initialisation de faits par défaut si vide
        cursor.execute("SELECT COUNT(*) FROM facts")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO facts (key, value, category) VALUES (?, ?, ?)", [
                ("nom_utilisateur", "Nikkoola", "profil"),
                ("projets", "Développeur SaaS et LegalTech (gruuuprimes), intégration IA, interfaces web avancées", "profil"),
                ("machine", "MacBook Pro 15\" 2017 avec OpenCore Legacy Patcher et double GPU (Intel/AMD)", "systeme"),
                ("personnalite", "Majordome IA poli, ultra-efficace, réactif, style JARVIS Iron Man", "role")
            ])
        conn.commit()

def get_all_facts() -> dict:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM facts")
        return {k: v for k, v in cursor.fetchall()}

def remember_fact(key: str, value: str, category: str = "general") -> str:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO facts (key, value, category, updated_at) 
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
        """, (key, value, category))
        conn.commit()
    return f"Information mémorisée : {key} = {value}"

def forget_fact(key: str) -> str:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM facts WHERE key = ?", (key,))
        conn.commit()
    return f"Information oubliée : {key}"

def log_interaction(role: str, content: str):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (role, content) VALUES (?, ?)", (role, content))
        conn.commit()

def get_recent_history(limit: int = 10) -> list:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM history ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
