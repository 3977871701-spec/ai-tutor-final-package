import os
import uuid
import platform
from pathlib import Path
from typing import List, Dict, Any, Optional

# Set HuggingFace to offline mode FIRST to use local cache
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import yaml

# Load config
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

chroma_settings = Settings(
    persist_directory=config["chroma"]["persist_directory"],
    anonymized_telemetry=False
)


def _get_model_cache_path() -> Path:
    """Get HuggingFace model cache path cross-platform"""
    system = platform.system().lower()
    
    # Try TRANSFORMERS_CACHE env var first
    cache_dir = os.environ.get("TRANSFORMERS_CACHE") or os.environ.get("HF_HOME")
    if cache_dir:
        return Path(cache_dir)
    
    # Platform-specific default paths
    if system == "windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "huggingface" / "hub"
    elif system == "darwin":  # macOS
        return Path.home() / ".cache" / "huggingface" / "hub"
    else:  # Linux and others
        return Path.home() / ".cache" / "huggingface" / "hub"


class KnowledgeBase:
    def __init__(self):
        self.persist_dir = config["chroma"]["persist_directory"]
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.Client(chroma_settings)
        self.collection_name = "school_knowledge"
        self.collection = self._get_or_create_collection()
        
        # Load embedding model - try multiple possible cache locations
        self.embedding_model = self._load_embedding_model()

    def _load_embedding_model(self) -> SentenceTransformer:
        """Load embedding model from cache, handle cross-platform paths"""
        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        
        # Try common cache locations
        possible_paths = [
            # Linux/Mac
            Path.home() / ".cache" / "huggingface" / "hub",
            # Windows
            Path(os.environ.get("LOCALAPPDATA", "")) / "huggingface" / "hub",
            # Environment variables
            Path(os.environ.get("TRANSFORMERS_CACHE", "")),
            Path(os.environ.get("HF_HOME", "")),
            # Current directory
            Path(__file__).parent.parent.parent / "models",
        ]
        
        # Find model snapshot
        for base_path in possible_paths:
            if not base_path or not base_path.exists():
                continue
            
            model_path = base_path / f"models--{model_name.replace('/', '--')}"
            if not model_path.exists():
                continue
            
            snapshots = model_path / "snapshots"
            if not snapshots.exists():
                continue
            
            # Find the snapshot folder
            for snap_dir in snapshots.iterdir():
                if snap_dir.is_dir():
                    # Try to load from this path
                    try:
                        return SentenceTransformer(str(snap_dir))
                    except:
                        continue
        
        # Fallback: try to load directly (will download if not cached)
        try:
            return SentenceTransformer(model_name)
        except Exception as e:
            raise RuntimeError(
                f"无法加载嵌入模型，请确保已下载模型缓存或设置正确的缓存路径。\n"
                f"提示: 设置环境变量 TRANSFORMERS_CACHE 指向模型缓存目录"
            )

    def _get_or_create_collection(self):
        try:
            return self.client.get_collection(name=self.collection_name)
        except:
            return self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "School knowledge base for AI tutor"}
            )

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()

    def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        doc_id = str(uuid.uuid4())
        embedding = self._embed_texts([content])[0]
        self.collection.add(
            ids=[doc_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata]
        )
        return doc_id

    def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        contents = [doc["content"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        ids = [str(uuid.uuid4()) for _ in documents]
        embeddings = self._embed_texts(contents)

        self.collection.add(
            ids=ids,
            documents=contents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        return ids

    def search(self, query: str, top_k: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict]:
        query_embedding = self._embed_texts([query])[0]
        
        if filter_metadata:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )
        else:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

        docs = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                docs.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] and results["metadatas"][0] else {},
                    "distance": results["distances"][0][i] if results["distances"] and results["distances"][0] else 0
                })
        return docs

    def delete_document(self, doc_id: str) -> bool:
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except:
            return False

    def clear_all(self) -> bool:
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self._get_or_create_collection()
            return True
        except:
            return False

    def get_collection_info(self) -> Dict[str, Any]:
        return {
            "name": self.collection_name,
            "count": self.collection.count()
        }

# Singleton instance
_kb_instance: Optional[KnowledgeBase] = None

def get_knowledge_base() -> KnowledgeBase:
    global _kb_instance
    if _kb_instance is None:
        _kb_instance = KnowledgeBase()
    return _kb_instance
