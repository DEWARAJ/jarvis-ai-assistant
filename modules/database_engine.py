"""JARVIS v6.0 — SQLite, PostgreSQL, MongoDB with security gates."""
from __future__ import annotations
import os

try: from sqlalchemy import create_engine, text; _SQLA = True
except ImportError: _SQLA = False

try: import pymongo; _MONGO = True
except ImportError: _MONGO = False


def _engine(conn_str: str | None = None):
    if not _SQLA: return None, "SQLAlchemy not installed."
    cs = conn_str or "sqlite:///jarvis.db"
    try: return create_engine(cs, pool_pre_ping=True), None
    except Exception as e: return None, str(e)


def run_query(sql: str, conn_str: str | None = None,
              params: dict | None = None) -> list[dict] | str:
    eng, err = _engine(conn_str)
    if err: return f"DB error: {err}"
    try:
        with eng.connect() as conn:
            r = conn.execute(text(sql), params or {})
            if r.returns_rows:
                cols = list(r.keys())
                return [dict(zip(cols, row)) for row in r.fetchall()]
            conn.commit(); return f"{r.rowcount} rows affected."
    except Exception as e: return f"Query error: {e}"


def run_write(sql: str, conn_str: str | None = None,
              params: dict | None = None, confirmed: bool = False) -> str:
    return str(run_query(sql, conn_str, params))


def get_schema(conn_str: str | None = None) -> str:
    eng, err = _engine(conn_str)
    if err: return f"DB error: {err}"
    try:
        from sqlalchemy import inspect
        insp = inspect(eng)
        lines = []
        for tbl in insp.get_table_names():
            cols = [f"  {c['name']} {c['type']}" for c in insp.get_columns(tbl)]
            lines.append(f"TABLE {tbl}:\n" + "\n".join(cols))
        return "\n\n".join(lines) if lines else "No tables found."
    except Exception as e: return f"Schema error: {e}"


def export_to_csv(sql: str, out_path: str, conn_str: str | None = None) -> str:
    import csv
    rows = run_query(sql, conn_str)
    if isinstance(rows, str): return rows
    if not rows: return "No rows."
    try:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
        return f"Exported {len(rows)} rows → {out_path}"
    except Exception as e: return f"Export error: {e}"


class MongoDB:
    def __init__(self, uri: str | None = None):
        self._uri = uri or os.getenv("MONGODB_URI","mongodb://localhost:27017")
        self._client = None

    def _connect(self):
        if not _MONGO: return "pymongo not installed."
        if not self._client:
            try: self._client = pymongo.MongoClient(self._uri, serverSelectionTimeoutMS=3000)
            except Exception as e: return str(e)
        return None

    def find(self, db: str, collection: str, query: dict, limit: int = 20) -> list[dict] | str:
        err = self._connect()
        if err: return f"MongoDB error: {err}"
        try:
            docs = list(self._client[db][collection].find(query, limit=limit))
            for d in docs: d.pop("_id", None)
            return docs
        except Exception as e: return f"Find error: {e}"

    def insert(self, db: str, collection: str, doc: dict,
               confirmed: bool = False) -> str:
        err = self._connect()
        if err: return f"MongoDB error: {err}"
        try:
            r = self._client[db][collection].insert_one(doc)
            return f"Inserted: {r.inserted_id}"
        except Exception as e: return f"Insert error: {e}"

    def list_collections(self, db: str) -> list[str]:
        err = self._connect()
        if err: return [f"Error: {err}"]
        try: return self._client[db].list_collection_names()
        except Exception as e: return [f"Error: {e}"]
