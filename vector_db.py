import os

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)


class QdrantStore:
    def __init__(self, url=None, collection="docs", dim=384):
        qdrant_url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "").strip() or None
        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            timeout=30,
        )
        self.collection = collection
        if not self.client.collection_exists(self.collection):
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
        else:
            collection_info = self.client.get_collection(self.collection)
            current_dim = collection_info.config.params.vectors.size
            if current_dim != dim:
                self.client.recreate_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )

    def upsert(self, ids, vectors, payloads):
        points = [
            PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
            for i in range(len(ids))
        ]
        self.client.upsert(self.collection, points=points)

    def search(self, query_vector, user_id: str, document_id: str, top_k: int = 5):
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                ),
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                )
            ]
        )
        if hasattr(self.client, "query_points"):
            res = self.client.query_points(
                collection_name=self.collection,
                query=query_vector,
                limit=top_k,
                query_filter=query_filter,
            )
            result = res.points
        else:
            result = self.client.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
            )

        content = []
        sources = set()

        for item in result:
            payload = getattr(item, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            if text:
                content.append(text)
            if source:
                sources.add(str(source))

        return {"content": content, "source": sorted(sources)}