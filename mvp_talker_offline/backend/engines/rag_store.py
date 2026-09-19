"""
rag_store.py — ChromaDB-backed persistent vector store for Buddy Grammar Coach.

Storage layout:
  data/chroma_db/   — ChromaDB PersistentClient directory (auto-created, gitignored)
  data/memory.db    — SQLite for learner state / quiz audits / syllabus (unchanged)

Embeddings are computed via local Ollama nomic-embed-text and passed as pre-computed
vectors to Chroma so we stay 100% offline.  Chroma provides:
  - ANN index (HNSW) for fast vector similarity — no O(n) cosine loop
  - Built-in BM25/TF-IDF for keyword search (query_texts)
  - Metadata filters for chapter / source scoping
  - Disk persistence — no re-indexing on restart, no JSON snapshot needed
"""

import os
import json
import urllib.request
import urllib.error
import numpy as np
from typing import List, Dict, Any, Optional
from core.structured_logger import rag_logger

try:
    import chromadb
    from chromadb.config import Settings
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False
    rag_logger.warning("chromadb not installed. Run: pip install chromadb>=0.5.0")

from core.config import DATA_DIR, CHROMA_DB_DIR, DB_PATH

DATA_DIR_PATH = str(DATA_DIR)
CHROMA_DIR = str(CHROMA_DB_DIR)
COLLECTION_NAME = "buddy_grammar_rag"

OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embeddings")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


class EmbeddingServiceUnavailable(Exception):
    """Raised when the local Ollama embedding service is unreachable or down."""
    pass


class RAGStore:
    """
    ChromaDB-backed RAG store for Buddy Grammar Coach.

    - Vectors persist to data/chroma_db/ (HNSW index, instant on restart)
    - Embeddings computed via local Ollama nomic-embed-text (fully offline)
    - Hybrid search: vector ANN + BM25 keyword, merged with Reciprocal Rank Fusion
    - Metadata filters: chapter_idx, source_type
    """

    def __init__(self, chroma_dir: str = CHROMA_DIR, embed_model: str = EMBEDDING_MODEL):
        self.chroma_dir = chroma_dir
        self.embed_model = embed_model
        self.embed_url = OLLAMA_EMBED_URL
        self.is_embedding_available: bool = True
        self.last_embedding_error: Optional[str] = None
        self.embedding_status: str = "operational"

        os.makedirs(self.chroma_dir, exist_ok=True)

        if not _CHROMA_AVAILABLE:
            raise RuntimeError("chromadb is not installed. Run: pip install chromadb>=0.5.0")

        self._client = chromadb.PersistentClient(
            path=self.chroma_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        # No embedding function — we supply pre-computed vectors from Ollama
        self._col = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        if self._col.count() == 0 and os.path.exists(str(DB_PATH)):
            self._hydrate_from_sqlite()

        rag_logger.info(
            f"ChromaDB RAGStore ready | dir={self.chroma_dir} | "
            f"collection={COLLECTION_NAME} | chunks={self._col.count()}"
        )

    def _hydrate_from_sqlite(self) -> None:
        """Hydrate ChromaDB collection from memory.db rag_chunks if collection is empty."""
        try:
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, source_type, source_title, chapter_idx, section_title, text_content, embedding, metadata_json
                FROM rag_chunks
            """)
            rows = cursor.fetchall()
            if not rows:
                conn.close()
                return

            rag_logger.info(f"Hydrating ChromaDB with {len(rows)} chunks from SQLite memory.db...")
            batch_size = 200
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                ids = [str(r["id"]) for r in batch]
                docs = [r["text_content"] or "" for r in batch]
                metas = []
                embeddings = []
                for r in batch:
                    meta = {
                        "source_type": str(r["source_type"] or "unknown"),
                        "source_title": str(r["source_title"] or ""),
                        "chapter_idx": int(r["chapter_idx"] or 0),
                        "section_title": str(r["section_title"] or ""),
                    }
                    if r["metadata_json"]:
                        try:
                            extra = json.loads(r["metadata_json"])
                            if isinstance(extra, dict):
                                for k, v in extra.items():
                                    if k not in meta and isinstance(v, (str, int, float, bool)):
                                        meta[k] = v
                        except Exception:
                            pass
                    metas.append(meta)

                    raw_emb = r["embedding"]
                    if raw_emb and isinstance(raw_emb, bytes) and len(raw_emb) == 3072:
                        embeddings.append(np.frombuffer(raw_emb, dtype=np.float32).tolist())
                    else:
                        embeddings.append(None)

                if all(e is not None for e in embeddings):
                    self._col.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
                else:
                    self._col.upsert(ids=ids, documents=docs, metadatas=metas)

            conn.close()
            rag_logger.info(f"ChromaDB hydration complete. Total chunks now: {self._col.count()}")
        except Exception as e:
            rag_logger.warning(f"ChromaDB hydration from SQLite skipped/failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Embedding
    # ─────────────────────────────────────────────────────────────────────────

    def get_embedding_status(self) -> Dict[str, Any]:
        """Diagnostic snapshot of the Ollama embedding microservice health."""
        return {
            "status": self.embedding_status,
            "is_available": self.is_embedding_available,
            "model": self.embed_model,
            "endpoint": self.embed_url,
            "last_error": self.last_embedding_error,
        }

    def get_embedding(self, text: str, raise_on_error: bool = False) -> Optional[np.ndarray]:
        """
        Fetch a normalized embedding from local Ollama nomic-embed-text.
        Returns np.ndarray on success, None on empty input or service outage.
        """
        stripped = (text or "").strip()
        if not stripped:
            return None

        payload = json.dumps({"model": self.embed_model, "prompt": stripped}).encode()
        req = urllib.request.Request(
            self.embed_url, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                raw = data.get("embedding", [])
                if raw:
                    arr = np.array(raw, dtype=np.float32)
                    norm = np.linalg.norm(arr)
                    if norm > 0:
                        arr = arr / norm
                    self.is_embedding_available = True
                    self.last_embedding_error = None
                    self.embedding_status = "operational"
                    return arr
        except Exception as exc:
            self.is_embedding_available = False
            self.last_embedding_error = str(exc)
            self.embedding_status = "unreachable"
            rag_logger.warning(
                f"Embedding service unreachable ({exc}). Dense search degraded — BM25 fallback."
            )
            if raise_on_error:
                raise EmbeddingServiceUnavailable(
                    f"Ollama embedding at {self.embed_url} is down: {exc}"
                ) from exc
        return None

    # ─────────────────────────────────────────────────────────────────────────
    # Insert / Batch
    # ─────────────────────────────────────────────────────────────────────────

    def insert_chunk(
        self,
        chunk_id: str,
        source_type: str,
        source_title: str,
        text_content: str,
        chapter_idx: Optional[int] = None,
        section_title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[np.ndarray] = None,
    ) -> bool:
        """
        Upsert a knowledge chunk into ChromaDB with pre-computed Ollama embedding.
        Falls back gracefully when Ollama is unavailable (BM25-only mode).
        """
        if not text_content or not text_content.strip():
            return False

        if embedding is None:
            embedding = self.get_embedding(text_content)

        meta: Dict[str, Any] = {
            "source_type": source_type,
            "source_title": source_title,
            "section_title": section_title,
            "chapter_idx": chapter_idx if chapter_idx is not None else -1,
            **(metadata or {}),
        }
        # ChromaDB metadata values must be str/int/float/bool
        meta = {
            k: (str(v) if not isinstance(v, (str, int, float, bool)) else v)
            for k, v in meta.items()
        }

        upsert_kwargs: Dict[str, Any] = {
            "ids": [chunk_id],
            "documents": [text_content],
            "metadatas": [meta],
        }
        if embedding is not None:
            upsert_kwargs["embeddings"] = [embedding.tolist()]

        self._col.upsert(**upsert_kwargs)
        return True

    def insert_batch(self, chunks: List[Dict[str, Any]]) -> int:
        """Batch upsert for faster indexing."""
        inserted = 0
        for item in chunks:
            ok = self.insert_chunk(
                chunk_id=item["id"],
                source_type=item.get("source_type", "reference"),
                source_title=item.get("source_title", ""),
                text_content=item.get("text", item.get("text_content", "")),
                chapter_idx=item.get("chapter_idx"),
                section_title=item.get("section_title", ""),
                metadata=item.get("metadata", {}),
                embedding=item.get("embedding"),
            )
            if ok:
                inserted += 1
        return inserted

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_where(
        self,
        chapter_filter: Optional[int],
        source_filter: Optional[str],
    ) -> Optional[Dict]:
        """Build a Chroma metadata `where` clause from optional filters."""
        conditions = []
        if chapter_filter is not None:
            conditions.append({"chapter_idx": {"$eq": chapter_filter}})
        if source_filter is not None:
            conditions.append({"source_type": {"$eq": source_filter}})
        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _row_to_dict(
        self, doc: str, meta: dict, dist: Optional[float] = None
    ) -> Dict[str, Any]:
        """Normalise a Chroma result row into the standard RAGStore result dict."""
        chapter = meta.get("chapter_idx", -1)
        return {
            "chunk_id":     meta.get("chunk_id", ""),
            "source_type":  meta.get("source_type", ""),
            "source_title": meta.get("source_title", ""),
            "chapter_idx":  chapter if chapter != -1 else None,
            "section_title": meta.get("section_title", ""),
            "text":         doc,
            "similarity":   round(1.0 - dist, 4) if dist is not None else None,
            "metadata": {
                k: v for k, v in meta.items()
                if k not in ("source_type", "source_title", "section_title", "chapter_idx")
            },
        }

    def _safe_n_results(self, top_k: int) -> int:
        count = self._col.count()
        return min(top_k, count) if count > 0 else 1

    # ─────────────────────────────────────────────────────────────────────────
    # Public search API  (same signature as before — drop-in replacement)
    # ─────────────────────────────────────────────────────────────────────────

    def search_vector(
        self,
        query: str,
        top_k: int = 5,
        chapter_filter: Optional[int] = None,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Dense ANN semantic search via ChromaDB HNSW index."""
        query_emb = self.get_embedding(query)
        if query_emb is None:
            return []

        where = self._build_where(chapter_filter, source_filter)
        kwargs: Dict[str, Any] = {
            "query_embeddings": [query_emb.tolist()],
            "n_results": self._safe_n_results(top_k),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            result = self._col.query(**kwargs)
        except Exception as exc:
            rag_logger.warning(f"Chroma vector search error: {exc}")
            return []

        return [
            self._row_to_dict(doc, meta, dist)
            for doc, meta, dist in zip(
                result["documents"][0],
                result["metadatas"][0],
                result["distances"][0],
            )
        ]

    def search_fts(
        self,
        query: str,
        top_k: int = 5,
        chapter_filter: Optional[int] = None,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """BM25 keyword search via ChromaDB built-in query_texts."""
        if not query.strip():
            return []

        where = self._build_where(chapter_filter, source_filter)
        kwargs: Dict[str, Any] = {
            "query_texts": [query],
            "n_results": self._safe_n_results(top_k),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            result = self._col.query(**kwargs)
        except Exception as exc:
            rag_logger.warning(f"Chroma BM25 search error: {exc}")
            return []

        out = []
        for doc, meta, dist in zip(
            result["documents"][0],
            result["metadatas"][0],
            result["distances"][0],
        ):
            row = self._row_to_dict(doc, meta, dist)
            row["bm25_rank"] = dist
            out.append(row)
        return out

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        chapter_filter: Optional[int] = None,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: vector ANN + BM25 merged with Reciprocal Rank Fusion (RRF).
        Falls back to BM25-only when Ollama embeddings are unavailable.
        """
        vector_results = self.search_vector(
            query, top_k=top_k * 2,
            chapter_filter=chapter_filter, source_filter=source_filter,
        )
        fts_results = self.search_fts(
            query, top_k=top_k * 2,
            chapter_filter=chapter_filter, source_filter=source_filter,
        )

        rrf_scores: Dict[str, float] = {}
        item_map: Dict[str, Dict]   = {}
        k_const = 60.0

        for rank, item in enumerate(vector_results):
            cid = item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k_const + rank + 1)
            item_map[cid] = item

        for rank, item in enumerate(fts_results):
            cid = item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k_const + rank + 1)
            if cid not in item_map:
                item_map[cid] = item

        sorted_cids = sorted(rrf_scores, key=lambda c: rrf_scores[c], reverse=True)
        results = []
        for cid in sorted_cids[:top_k]:
            res = dict(item_map[cid])
            res["rrf_score"] = round(rrf_scores[cid], 6)
            results.append(res)
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────────────

    def count_chunks(self) -> Dict[str, int]:
        """Return total chunk count and breakdown by source — compatible with all call sites."""
        counts = self.count_by_source()
        counts["total"] = self._col.count()
        return counts

    def count_by_source(self) -> Dict[str, int]:
        """Return chunk counts grouped by source_type."""
        try:
            all_meta = self._col.get(include=["metadatas"])["metadatas"]
            counts: Dict[str, int] = {}
            for m in all_meta:
                stype = m.get("source_type", "unknown")
                counts[stype] = counts.get(stype, 0) + 1
            return counts
        except Exception:
            return {"total": self._col.count()}

    def delete_chunk(self, chunk_id: str) -> None:
        """Remove a single chunk from the ChromaDB collection."""
        self._col.delete(ids=[chunk_id])
