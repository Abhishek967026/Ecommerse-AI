"""Vector store setup for product RAG."""
import os
from typing import List, Optional
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from app.config import settings
from langchain_core.documents import Document

# Global vector store instance
_vector_store: Optional[Chroma] = None


def get_embeddings():
    """Get OpenAI embeddings model."""
    return OpenAIEmbeddings(
        openai_api_key=settings.openai_api_key,
        model="text-embedding-3-small",
    )


def get_vector_store() -> Chroma:
    """Get or initialize the Chroma vector store."""
    global _vector_store
    if _vector_store is None:
        os.makedirs(settings.chroma_persist_dir, exist_ok=True)
        _vector_store = Chroma(
            collection_name="products",
            embedding_function=get_embeddings(),
            persist_directory=settings.chroma_persist_dir,
        )
    return _vector_store


def index_products(products: List[dict]) -> int:
    """Index products into the vector store for RAG."""
    store = get_vector_store()

    documents = []
    for product in products:
        text = (
            f"Product: {product['name']}\n"
            f"Category: {product['category']}\n"
            f"Brand: {product.get('brand', 'Unknown')}\n"
            f"Price: ${product['price']:.2f}\n"
            f"Description: {product.get('description', 'No description')}\n"
            f"Rating: {product.get('rating', 0)}/5 ({product.get('review_count', 0)} reviews)\n"
            f"In Stock: {'Yes' if product.get('stock', 0) > 0 else 'No'}"
        )
        doc = Document(
            page_content=text,
            metadata={
                "product_id": str(product["id"]),
                "name": product["name"],
                "price": product["price"],
                "category": product["category"],
                "stock": product.get("stock", 0),
            }
        )
        documents.append(doc)

    if documents:
        # Delete existing and re-add
        try:
            existing_ids = store.get()["ids"]
            if existing_ids:
                store.delete(ids=existing_ids)
        except Exception:
            pass
        store.add_documents(documents)
        print(f"✅ Indexed {len(documents)} products into vector store.")

    return len(documents)


def similarity_search(query: str, k: int = 5) -> List[Document]:
    """Search for relevant products by query."""
    store = get_vector_store()
    try:
        results = store.similarity_search(query, k=k)
        return results
    except Exception as e:
        print(f"Vector search error: {e}")
        return []
