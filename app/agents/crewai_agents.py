"""CrewAI multi-agent system for complex e-commerce tasks."""
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import Field
from typing import Type, Any
from langsmith import traceable
from app.config import settings

from langchain_groq import ChatGroq



def get_llm():
    return ChatGroq(model=settings.LLM_MODEL,
                    temperature=0.3,
                    groq_api_key=settings.GROQ_API_KEY)




# ---- Custom CrewAI Tools ----

class ProductSearchTool(BaseTool):
    name: str = "Product Search"
    description: str = "Search for products by name, category, or description. Input: search query string."

    def _run(self, query: str) -> str:
        from app.rag.vector_store import similarity_search
        docs = similarity_search(query, k=5)
        if not docs:
            return "No products found."
        results = []
        for doc in docs:
            meta = doc.metadata
            results.append(
                f"- {meta.get('name')} | Price: ${meta.get('price', 0):.2f} | "
                f"Category: {meta.get('category')} | "
                f"{'In Stock' if meta.get('stock', 0) > 0 else 'Out of Stock'} | "
                f"ID: {meta.get('product_id')}"
            )
        return "Products found:\n" + "\n".join(results)


class PriceAnalysisTool(BaseTool):
    name: str = "Price Analysis"
    description: str = "Analyze and compare prices across product categories. Input: category or 'all'."

    def _run(self, category: str = "all") -> str:
        from app.rag.vector_store import similarity_search
        query = f"products in {category}" if category != "all" else "all products price"
        docs = similarity_search(query, k=10)
        if not docs:
            return "No price data available."
        prices = []
        for doc in docs:
            meta = doc.metadata
            if meta.get("price"):
                prices.append({
                    "name": meta.get("name"),
                    "price": meta.get("price"),
                    "category": meta.get("category"),
                })
        if not prices:
            return "No price data found."
        avg_price = sum(p["price"] for p in prices) / len(prices)
        min_price = min(prices, key=lambda x: x["price"])
        max_price = max(prices, key=lambda x: x["price"])
        return (
            f"Price Analysis:\n"
            f"- Average price: ${avg_price:.2f}\n"
            f"- Cheapest: {min_price['name']} at ${min_price['price']:.2f}\n"
            f"- Most expensive: {max_price['name']} at ${max_price['price']:.2f}\n"
            f"- Total products analyzed: {len(prices)}"
        )


class ProductRecommendationTool(BaseTool):
    name: str = "Product Recommendation"
    description: str = "Get personalized product recommendations based on preferences. Input: customer preferences or budget."

    def _run(self, preferences: str) -> str:
        from app.rag.vector_store import similarity_search
        docs = similarity_search(preferences, k=3)
        if not docs:
            return "No recommendations available."
        recs = []
        for i, doc in enumerate(docs, 1):
            meta = doc.metadata
            recs.append(
                f"{i}. {meta.get('name')} - ${meta.get('price', 0):.2f}\n"
                f"   Category: {meta.get('category')}\n"
                f"   {'✅ In Stock' if meta.get('stock', 0) > 0 else '❌ Out of Stock'}"
            )
        return "Recommended products:\n" + "\n".join(recs)


# ---- CrewAI Agents ----

def create_product_specialist() -> Agent:
    """Agent specialized in product knowledge."""
    return Agent(
        role="Product Specialist",
        goal="Provide comprehensive product information, comparisons, and expert advice to help customers make informed decisions",
        backstory="""You are an expert product specialist with deep knowledge of all products 
        in our e-commerce store. You excel at finding the right products for customers, 
        explaining features, comparing options, and providing honest recommendations.""",
        tools=[ProductSearchTool(), ProductRecommendationTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=True,
    )


def create_pricing_analyst() -> Agent:
    """Agent specialized in pricing and deals."""
    return Agent(
        role="Pricing Analyst",
        goal="Analyze pricing, find best deals, and help customers get the most value for their money",
        backstory="""You are a pricing expert who understands market trends and value analysis.
        You help customers understand if they're getting good deals, compare prices across 
        categories, and identify the best value products.""",
        tools=[PriceAnalysisTool(), ProductSearchTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )


def create_customer_service_agent() -> Agent:
    """Agent specialized in customer service."""
    return Agent(
        role="Customer Service Manager",
        goal="Ensure customer satisfaction by synthesizing information from specialist agents and providing clear, actionable responses",
        backstory="""You are an experienced customer service manager who coordinates between 
        product specialists and pricing analysts to deliver exceptional customer experiences.
        You synthesize complex information into clear, friendly responses.""",
        tools=[ProductSearchTool()],
        llm=get_llm(),
        verbose=True,
        allow_delegation=True,
    )


# ---- CrewAI Tasks ----

def create_product_research_task(agent: Agent, query: str) -> Task:
    return Task(
        description=f"""Research and analyze products related to this customer query: "{query}"
        
        Find relevant products, gather information about:
        1. Available products matching the query
        2. Key features and specifications
        3. Stock availability
        4. Price range
        
        Provide comprehensive product information.""",
        agent=agent,
        expected_output="A detailed list of relevant products with features, prices, and availability.",
    )


def create_price_analysis_task(agent: Agent, query: str) -> Task:
    return Task(
        description=f"""Analyze pricing for the customer query: "{query}"
        
        Provide:
        1. Price comparison across similar products
        2. Best value options
        3. Budget recommendations
        4. Any notable deals or value propositions""",
        agent=agent,
        expected_output="A price analysis with comparisons and value recommendations.",
    )


def create_recommendation_task(agent: Agent, query: str, context: str = "") -> Task:
    return Task(
        description=f"""Based on the customer query: "{query}"
        And the research context: "{context}"
        
        Provide a final, comprehensive response that:
        1. Directly addresses the customer's needs
        2. Recommends the best products for their situation
        3. Explains pricing and value
        4. Guides next steps (how to purchase, what to consider)
        
        Make the response friendly, clear, and actionable.""",
        agent=agent,
        expected_output="A clear, customer-friendly response with product recommendations and next steps.",
    )


# ---- Main CrewAI Runner ----

@traceable(name="crewai_workflow", tags=["crewai", "ecommerce"])
def run_crew_analysis(query: str) -> str:
    """Run CrewAI multi-agent analysis for complex product queries."""
    try:
        product_specialist = create_product_specialist()
        pricing_analyst = create_pricing_analyst()
        service_manager = create_customer_service_agent()

        tasks = [
            create_product_research_task(product_specialist, query),
            create_price_analysis_task(pricing_analyst, query),
            create_recommendation_task(service_manager, query),
        ]

        crew = Crew(
            agents=[product_specialist, pricing_analyst, service_manager],
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()
        return str(result)
    except Exception as e:
        return f"CrewAI analysis encountered an issue: {str(e)}. Falling back to standard search."
