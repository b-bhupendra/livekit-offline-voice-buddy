import os
import json
import sqlite3
import urllib.request
import urllib.error
import numpy as np
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "memory.db")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embeddings")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

class EmbeddingServiceUnavailable(Exception):
    """Raised when the local Ollama embedding service is unreachable or down."""
    pass

class RAGStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH, embed_model: str = EMBEDDING_MODEL):
        self.db_path = db_path
        self.embed_model = embed_model
        self.embed_url = OLLAMA_EMBED_URL
        self.is_embedding_available: bool = True
        self.last_embedding_error: Optional[str] = None
        self.embedding_status: str = "operational"
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    id TEXT PRIMARY KEY,
                    source_type TEXT,
                    source_title TEXT,
                    chapter_idx INTEGER,
                    section_title TEXT,
                    text_content TEXT,
                    embedding BLOB,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(
                    chunk_id,
                    source_type,
                    source_title,
                    section_title,
                    text_content
                )
            """)
            conn.commit()

    def get_embedding_status(self) -> Dict[str, Any]:
        """Provides a distinct diagnostic snapshot of the embedding microservice health."""
        return {
            "status": self.embedding_status,
            "is_available": self.is_embedding_available,
            "model": self.embed_model,
            "endpoint": self.embed_url,
            "last_error": self.last_embedding_error
        }

    def get_embedding(self, text: str, raise_on_error: bool = False) -> Optional[np.ndarray]:
        """
        Fetch 768-dim normalized embedding from local Ollama nomic-embed-text.
        Provides distinct return paths:
        - Returns np.ndarray on successful normalization.
        - Returns None for empty / whitespace input without error.
        - Sets self.is_embedding_available = False and records self.last_embedding_error on service downtime.
        - Raises EmbeddingServiceUnavailable if raise_on_error=True.
        """
        stripped = text.strip() if text else ""
        if not stripped:
            return None

        payload = json.dumps({"model": self.embed_model, "prompt": stripped}).encode("utf-8")
        req = urllib.request.Request(
            self.embed_url,
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                raw_emb = data.get("embedding", [])
                if raw_emb:
                    arr = np.array(raw_emb, dtype=np.float32)
                    norm = np.linalg.norm(arr)
                    if norm > 0:
                        arr = arr / norm
                    self.is_embedding_available = True
                    self.last_embedding_error = None
                    self.embedding_status = "operational"
                    return arr
        except Exception as e:
            self.is_embedding_available = False
            self.last_embedding_error = str(e)
            self.embedding_status = "unreachable"
            print(f"[RAGStore] Warning: Embedding service unreachable ({e}). Dense search degraded, falling back to BM25/FTS.")
            if raise_on_error:
                raise EmbeddingServiceUnavailable(
                    f"Local embedding service at {OLLAMA_EMBED_URL} is down: {e}"
                ) from e
            return None
        return None

    def insert_chunk(
        self,
        chunk_id: str,
        source_type: str,
        source_title: str,
        text_content: str,
        chapter_idx: Optional[int] = None,
        section_title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[np.ndarray] = None
    ) -> bool:
        """Insert or replace a knowledge chunk with its vector embedding and FTS index."""
        if embedding is None:
            embedding = self.get_embedding(text_content)

        emb_bytes = embedding.tobytes() if embedding is not None else None
        meta_str = json.dumps(metadata or {})

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO rag_chunks (
                    id, source_type, source_title, chapter_idx, section_title, text_content, embedding, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (chunk_id, source_type, source_title, chapter_idx, section_title, text_content, emb_bytes, meta_str))
            
            # Update FTS index
            cursor.execute("DELETE FROM rag_fts WHERE chunk_id = ?", (chunk_id,))
            cursor.execute("""
                INSERT INTO rag_fts (chunk_id, source_type, source_title, section_title, text_content)
                VALUES (?, ?, ?, ?, ?)
            """, (chunk_id, source_type, source_title, section_title, text_content))
            conn.commit()
        return True

    def insert_batch(self, chunks: List[Dict[str, Any]]) -> int:
        """Batch insert chunks for faster indexing."""
        inserted = 0
        for item in chunks:
            self.insert_chunk(
                chunk_id=item["id"],
                source_type=item.get("source_type", "reference"),
                source_title=item.get("source_title", ""),
                text_content=item["text"],
                chapter_idx=item.get("chapter_idx"),
                section_title=item.get("section_title", ""),
                metadata=item.get("metadata", {}),
                embedding=item.get("embedding")
            )
            inserted += 1
        return inserted

    def search_vector(
        self,
        query: str,
        top_k: int = 5,
        chapter_filter: Optional[int] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Dense semantic search using cosine similarity."""
        query_emb = self.get_embedding(query)
        if query_emb is None:
            return []

        with self._get_connection() as conn:
            cursor = conn.cursor()
            query_sql = "SELECT id, source_type, source_title, chapter_idx, section_title, text_content, embedding, metadata_json FROM rag_chunks WHERE embedding IS NOT NULL"
            params = []
            if chapter_filter is not None:
                query_sql += " AND chapter_idx = ?"
                params.append(chapter_filter)
            if source_filter is not None:
                query_sql += " AND source_type = ?"
                params.append(source_filter)

            cursor.execute(query_sql, params)
            rows = cursor.fetchall()

        if not rows:
            return []

        results = []
        for row in rows:
            emb_blob = row["embedding"]
            if not emb_blob:
                continue
            chunk_emb = np.frombuffer(emb_blob, dtype=np.float32)
            similarity = float(np.dot(query_emb, chunk_emb))
            results.append({
                "chunk_id": row["id"],
                "source_type": row["source_type"],
                "source_title": row["source_title"],
                "chapter_idx": row["chapter_idx"],
                "section_title": row["section_title"],
                "text": row["text_content"],
                "similarity": similarity,
                "metadata": json.loads(row["metadata_json"] or "{}")
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def search_fts(
        self,
        query: str,
        top_k: int = 5,
        chapter_filter: Optional[int] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Sparse BM25 full-text search via SQLite FTS5."""
        # Sanitize query for FTS5 syntax
        clean_words = [w for w in query.replace('"', '').replace("'", "").split() if w.isalnum()]
        if not clean_words:
            return []
        fts_query = " OR ".join(clean_words)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            sql = """
                SELECT c.id, c.source_type, c.source_title, c.chapter_idx, c.section_title, c.text_content, c.metadata_json, rank
                FROM rag_fts f
                JOIN rag_chunks c ON f.chunk_id = c.id
                WHERE rag_fts MATCH ?
            """
            params = [fts_query]
            if chapter_filter is not None:
                sql += " AND c.chapter_idx = ?"
                params.append(chapter_filter)
            if source_filter is not None:
                sql += " AND c.source_type = ?"
                params.append(source_filter)
            sql += " ORDER BY rank LIMIT ?"
            params.append(top_k)

            try:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            except sqlite3.OperationalError:
                return []

        results = []
        for row in rows:
            results.append({
                "chunk_id": row["id"],
                "source_type": row["source_type"],
                "source_title": row["source_title"],
                "chapter_idx": row["chapter_idx"],
                "section_title": row["section_title"],
                "text": row["text_content"],
                "bm25_rank": row["rank"],
                "metadata": json.loads(row["metadata_json"] or "{}")
            })
        return results

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        chapter_filter: Optional[int] = None,
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense vector similarity and sparse FTS BM25 ranking
        using Reciprocal Rank Fusion (RRF).
        """
        vector_results = self.search_vector(query, top_k=top_k * 2, chapter_filter=chapter_filter, source_filter=source_filter)
        fts_results = self.search_fts(query, top_k=top_k * 2, chapter_filter=chapter_filter, source_filter=source_filter)

        rrf_scores = {}
        item_map = {}

        # 60 is the standard constant in RRF
        k_const = 60.0

        for rank, item in enumerate(vector_results):
            cid = item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k_const + rank + 1))
            item_map[cid] = item

        for rank, item in enumerate(fts_results):
            cid = item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (k_const + rank + 1))
            if cid not in item_map:
                item_map[cid] = item

        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)
        final_results = []
        for cid in sorted_cids[:top_k]:
            res = dict(item_map[cid])
            res["rrf_score"] = rrf_scores[cid]
            final_results.append(res)

        return final_results

    def count_chunks(self) -> Dict[str, int]:
        """Return counts of chunks grouped by source_type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT source_type, count(*) as cnt FROM rag_chunks GROUP BY source_type")
            rows = cursor.fetchall()
            return {r["source_type"]: r["cnt"] for r in rows}
