import sqlite3
from pathlib import Path

class Database:
    def __init__(self, path):
        self.path = str(path)
    def connect(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA busy_timeout=10000')
        return con
    def initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.execute('PRAGMA journal_mode=WAL')
            con.execute('''CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY, timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL, source TEXT NOT NULL, payload TEXT NOT NULL)''')
            con.execute('CREATE INDEX IF NOT EXISTS ix_events_time ON events(timestamp DESC)')
            con.execute('CREATE INDEX IF NOT EXISTS ix_events_device ON events(device_id)')
