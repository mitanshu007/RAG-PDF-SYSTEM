from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
EMBED_MODEL = "all-MiniLM-L6-v2"
EMBED_DIM = 384
embedding_model = SentenceTransformer(EMBED_MODEL)

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=0)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    return embedding_model.encode(texts, convert_to_numpy=True).tolist()
