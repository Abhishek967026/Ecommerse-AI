"""RAG retrieval chain for product Q&A."""
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate
from langsmith import traceable
from app.config import settings
from app.rag.vector_store import similarity_search


def format_docs(docs: List[Document]) -> str:
    """Format retrieved documents into a single string."""
    if not docs:
        return "No relevant products found."
    return "\n\n---\n\n".join([doc.page_content for doc in docs])


PRODUCT_QA_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful e-commerce assistant for our store. 
You help customers find products, understand pricing, compare items, and make purchase decisions.

Use the following product information to answer the customer's question:

{context}

Guidelines:
- Be friendly, helpful, and concise
- Always mention the exact price when discussing products
- If a product is out of stock, mention alternatives
- If you don't know something, say so honestly
- If the customer wants to buy, tell them to use the purchase button or say "I want to buy [product name]"
- For cancellations, say "cancel order [order ID]"
"""),
    ("human", "{question}"),
])


@traceable(name="product_rag_chain", tags=["rag", "ecommerce"])
def run_rag_chain(query: str, k: int = 4) -> Dict[str, Any]:
    """Run the RAG chain for a product query."""
    # Retrieve relevant documents
    docs = similarity_search(query, k=k)

    # Build LLM
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.3,
        openai_api_key=settings.openai_api_key,
    )

    # Build RAG chain
    chain = (
        {"context": lambda _: format_docs(docs), "question": RunnablePassthrough()}
        | PRODUCT_QA_PROMPT
        | llm
        | StrOutputParser()
    )

    response = chain.invoke(query)

    # Extract product metadata from docs
    products = []
    for doc in docs:
        meta = doc.metadata
        if meta.get("product_id"):
            products.append({
                "id": meta.get("product_id"),
                "name": meta.get("name"),
                "price": meta.get("price"),
                "category": meta.get("category"),
                "in_stock": meta.get("stock", 0) > 0,
            })

    return {
        "response": response,
        "source_documents": docs,
        "products_found": products,
    }


@traceable(name="product_summary", tags=["rag", "summary"])
def get_product_summary(products: List[dict]) -> str:
    """Generate a summary of the product catalog using LLM."""
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.5,
        openai_api_key=settings.openai_api_key,
    )

    products_text = "\n".join([
        f"- {p['name']} ({p['category']}) - ${p['price']:.2f} | Stock: {p['stock']}"
        for p in products[:20]  # limit
    ])

    prompt = f"""Provide a brief, engaging summary of our product catalog:

{products_text}

Give a 2-3 sentence overview highlighting categories, price ranges, and best sellers. 
Be enthusiastic but concise."""

    return llm.invoke(prompt).content
