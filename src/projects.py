"""Project management: CRUD for projects and artifacts. SQLite backend."""
import json
import os
import shutil
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PROJECTS_DIR = os.path.join(_ROOT, "data", "projects")
DB_PATH = os.path.join(_ROOT, 'data', 'researchos.db')


@dataclass
class ProjectMetadata:
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str


@dataclass
class ProjectArtifact:
    id: str
    project_id: str
    artifact_type: str
    name: str
    filename: str
    created_at: str
    metadata: dict = field(default_factory=dict)


def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                name TEXT NOT NULL,
                filename TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
    finally:
        conn.close()


def _project_dir(project_id: str) -> str:
    return os.path.join(PROJECTS_DIR, project_id)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_uuid() -> str:
    return str(uuid.uuid4())[:8]


def create_project(name: str, description: str = "") -> ProjectMetadata:
    pid = _short_uuid()
    now = _now_iso()

    os.makedirs(_project_dir(pid), exist_ok=True)

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (pid, name, description, now, now),
        )
        conn.commit()
    finally:
        conn.close()

    return ProjectMetadata(id=pid, name=name, description=description, created_at=now, updated_at=now)


def list_projects() -> list[ProjectMetadata]:
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
        return [ProjectMetadata(id=r["id"], name=r["name"], description=r["description"],
                                created_at=r["created_at"], updated_at=r["updated_at"]) for r in rows]
    finally:
        conn.close()


def get_project(project_id: str) -> ProjectMetadata | None:
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            return None
        return ProjectMetadata(id=row["id"], name=row["name"], description=row["description"],
                               created_at=row["created_at"], updated_at=row["updated_at"])
    finally:
        conn.close()


def update_project(project_id: str, name: str = None, description: str = None) -> ProjectMetadata | None:
    proj = get_project(project_id)
    if proj is None:
        return None

    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    updates.append("updated_at = ?")
    now = _now_iso()
    params.append(now)
    params.append(project_id)

    conn = get_db()
    try:
        conn.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
    finally:
        conn.close()

    return get_project(project_id)


def delete_project(project_id: str) -> bool:
    conn = get_db()
    try:
        cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
    finally:
        conn.close()

    pdir = _project_dir(project_id)
    if os.path.isdir(pdir):
        shutil.rmtree(pdir)

    return deleted


def save_artifact(project_id: str, artifact_type: str, name: str, data: dict, metadata: dict = None) -> ProjectArtifact:
    pdir = _project_dir(project_id)
    os.makedirs(pdir, exist_ok=True)

    aid = _short_uuid()
    filename = f"{artifact_type}_{aid}.json"
    filepath = os.path.join(pdir, filename)

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)

    now = _now_iso()
    meta_json = json.dumps(metadata or {})

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO artifacts (id, project_id, artifact_type, name, filename, created_at, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (aid, project_id, artifact_type, name, filename, now, meta_json),
        )
        conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
        conn.commit()
    finally:
        conn.close()

    return ProjectArtifact(id=aid, project_id=project_id, artifact_type=artifact_type,
                           name=name, filename=filename, created_at=now, metadata=metadata or {})


def save_dataframe_artifact(project_id: str, artifact_type: str, name: str, df, metadata: dict = None) -> ProjectArtifact:
    pdir = _project_dir(project_id)
    os.makedirs(pdir, exist_ok=True)

    aid = _short_uuid()
    filename = f"{artifact_type}_{aid}.csv"
    filepath = os.path.join(pdir, filename)

    df.to_csv(filepath, index=False)

    now = _now_iso()
    meta_json = json.dumps(metadata or {})

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO artifacts (id, project_id, artifact_type, name, filename, created_at, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (aid, project_id, artifact_type, name, filename, now, meta_json),
        )
        conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
        conn.commit()
    finally:
        conn.close()

    return ProjectArtifact(id=aid, project_id=project_id, artifact_type=artifact_type,
                           name=name, filename=filename, created_at=now, metadata=metadata or {})


def load_artifacts(project_id: str) -> list[ProjectArtifact]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM artifacts WHERE project_id = ? ORDER BY created_at DESC", (project_id,)
        ).fetchall()
        return [ProjectArtifact(
            id=r["id"], project_id=r["project_id"], artifact_type=r["artifact_type"],
            name=r["name"], filename=r["filename"], created_at=r["created_at"],
            metadata=json.loads(r["metadata_json"] or "{}"),
        ) for r in rows]
    finally:
        conn.close()


def load_artifact_data(project_id: str, artifact: ProjectArtifact):
    filepath = os.path.join(_project_dir(project_id), artifact.filename)
    if not os.path.isfile(filepath):
        return None
    if artifact.filename.endswith(".csv"):
        import pandas as pd
        return pd.read_csv(filepath)
    else:
        with open(filepath) as f:
            return json.load(f)


def get_project_stats(project_id: str) -> dict:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT artifact_type, COUNT(*) as count FROM artifacts WHERE project_id = ? GROUP BY artifact_type",
            (project_id,),
        ).fetchall()
        artifact_types = {r["artifact_type"]: r["count"] for r in rows}
        return {"artifact_count": sum(artifact_types.values()), "artifact_types": artifact_types}
    finally:
        conn.close()


def get_recent_projects(limit: int = 3) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT p.*, COUNT(a.id) as artifact_count
            FROM projects p
            LEFT JOIN artifacts a ON p.id = a.project_id
            GROUP BY p.id
            ORDER BY p.updated_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Initialize database on import
init_db()
