import sqlite3
from core.state import ResearchState

class MemoryDB:
    def __init__(self, db_path: str = "agent_memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Creates the SQLite table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    objective TEXT,
                    state_json TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def save_state(self, session_id: str, state: ResearchState):
        """Serializes the Pydantic state to JSON and saves it."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            state_json = state.model_dump_json()
            cursor.execute('''
                INSERT INTO sessions (session_id, objective, state_json)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    last_updated=CURRENT_TIMESTAMP
            ''', (session_id, state.objective, state_json))
            conn.commit()

    def load_state(self, session_id: str) -> ResearchState:
        """Retrieves and reconstructs the Pydantic state from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT state_json FROM sessions WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                return ResearchState.model_validate_json(row[0])
            return None