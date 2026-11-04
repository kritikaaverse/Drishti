import json
from database.models import HistoryRecord, HistoryResponse

class HistoryService:
    def __init__(self, db, retention):
        self.db, self.retention = db, retention
    def add(self, response, source):
        with self.db.connect() as con:
            con.execute('INSERT INTO events VALUES (?,?,?,?,?)',
                        (response.event_id, response.timestamp.isoformat(), response.device_id,
                         source, response.model_dump_json()))
            con.execute('DELETE FROM events WHERE event_id IN (SELECT event_id FROM events ORDER BY timestamp DESC LIMIT -1 OFFSET ?)', (self.retention,))
    def get(self, limit=50, offset=0, device_id=None):
        where, args = (' WHERE device_id=?', [device_id]) if device_id else ('', [])
        with self.db.connect() as con:
            total = con.execute('SELECT count(*) FROM events' + where, args).fetchone()[0]
            rows = con.execute('SELECT * FROM events' + where + ' ORDER BY timestamp DESC LIMIT ? OFFSET ?', [*args, limit, offset]).fetchall()
        return HistoryResponse(records=[HistoryRecord(event_id=r['event_id'], timestamp=r['timestamp'], device_id=r['device_id'], source=r['source'], response=json.loads(r['payload'])) for r in rows], total=total, limit=limit, offset=offset)
    def delete(self, device_id=None):
        with self.db.connect() as con:
            cursor = con.execute('DELETE FROM events' + (' WHERE device_id=?' if device_id else ''), (device_id,) if device_id else ())
            return cursor.rowcount
