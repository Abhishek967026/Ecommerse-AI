"""LangGraph multi-agent workflow for e-commerce operations."""
import json
import uuid
from typing import TypedDict, Annotated, Sequence, Literal, Optional, Any
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from app.config import settings
from app.agents.tools import (
    _search_products_impl,
    _get_product_details_impl,
    _create_order_impl,
    _cancel_order_impl,
    _list_orders_impl,
)


# ---- State Definition ----

class AgentState(TypedDict):
    messages: list[BaseMessage]
    intent: Optional[str]
    action_result: Optional[str]
    products_found: Optional[list]
    next_agent: Optional[str]
    customer_info: Optional[dict]
    session_id: str
    db_session: Any  # Not serializable, kept in memory


# ---- LLM Setup ----

from langchain_groq import ChatGroq


def get_llm():
    return ChatGroq(model=settings.LLM_MODEL,
                    temperature=0.3,
                    groq_api_key=settings.GROQ_API_KEY)

# def get_llm(temperature: float = 0.3) -> ChatOpenAI:
#     return ChatOpenAI(
#         model=settings.openai_model,
#         temperature=temperature,
#         openai_api_key=settings.openai_api_key,
#     )


# ---- Router Agent ----

ROUTER_PROMPT = """You are a routing agent for an e-commerce store. 
Analyze the user's message and determine which specialist agent should handle it.

Return ONLY one of these labels:
- "search" - user wants to find/browse products, ask about products, prices, features
- "purchase" - user wants to buy a product
- "cancel" - user wants to cancel an order
- "orders" - user wants to check order status/history
- "general" - general questions, greetings, other

User message: {message}
Customer info: {customer_info}

Return only the label, nothing else."""


@traceable(name="router_agent", tags=["langgraph", "router"])
def router_agent(state: AgentState) -> AgentState:
    """Route the user message to the appropriate specialist agent."""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    customer_info = state.get("customer_info", {})

    llm = get_llm(temperature=0)
    prompt = ROUTER_PROMPT.format(
        message=last_message,
        customer_info=json.dumps(customer_info)
    )
    intent = llm.invoke(prompt).content.strip().lower()

    # Validate intent
    valid_intents = {"search", "purchase", "cancel", "orders", "general"}
    if intent not in valid_intents:
        intent = "general"

    return {**state, "intent": intent, "next_agent": intent}


# ---- Search Agent ----

SEARCH_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a product search specialist for our e-commerce store.
Help customers find products using the search results provided.
Be helpful, mention prices clearly, and guide them toward purchase if appropriate.

Search Results:
{search_results}

If no products found, apologize and suggest trying different keywords.
Always be friendly and professional."""),
    ("human", "{message}"),
])


@traceable(name="search_agent", tags=["langgraph", "search"])
async def search_agent(state: AgentState) -> AgentState:
    """Search for products and provide recommendations."""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    db_session = state.get("db_session")

    # Get search results
    search_results = await _search_products_impl(last_message, db_session)

    # Generate response
    llm = get_llm(temperature=0.5)
    chain = SEARCH_AGENT_PROMPT | llm | StrOutputParser()
    response = chain.invoke({
        "message": last_message,
        "search_results": search_results,
    })

    new_messages = list(messages) + [AIMessage(content=response)]
    return {
        **state,
        "messages": new_messages,
        "action_result": response,
    }


# ---- Purchase Agent ----

PURCHASE_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a purchase assistant for our e-commerce store.
Help customers complete their purchase based on the conversation.

Customer Info: {customer_info}
Product Search Results: {search_results}
Action Result: {action_result}

If purchase was successful, confirm with order details.
If there was an error, explain it and offer alternatives.
Be warm, professional, and reassuring."""),
    ("human", "{message}"),
])


@traceable(name="purchase_agent", tags=["langgraph", "purchase"])
async def purchase_agent(state: AgentState) -> AgentState:
    """Handle product purchase."""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    customer_info = state.get("customer_info", {})
    db_session = state.get("db_session")

    action_result = "Unable to process purchase - missing product or customer info."

    # Try to extract product info from message & search
    search_results = await _search_products_impl(last_message, db_session)

    # Parse product ID from message if mentioned
    import re
    product_id_match = re.search(r'(?:product|id|#)\s*:?\s*(\d+)', last_message, re.IGNORECASE)
    product_id = int(product_id_match.group(1)) if product_id_match else None

    # Also check if a specific product was found in search
    if not product_id:
        from app.rag.vector_store import similarity_search
        docs = similarity_search(last_message, k=1)
        if docs and docs[0].metadata.get("product_id"):
            product_id = int(docs[0].metadata["product_id"])

    if product_id and customer_info.get("email") and customer_info.get("name"):
        action_result = await _create_order_impl(
            product_id=product_id,
            customer_name=customer_info["name"],
            customer_email=customer_info["email"],
            quantity=1,
            shipping_address=customer_info.get("address", ""),
            db_session=db_session,
        )
    elif not customer_info.get("email"):
        action_result = (
            "To complete your purchase, please provide your name and email address. "
            "For example: 'My name is John Doe and my email is john@example.com'"
        )
    elif not product_id:
        action_result = f"I found these products:\n{search_results}\n\nPlease specify which product you'd like to buy by mentioning its name or ID."

    llm = get_llm(temperature=0.3)
    chain = PURCHASE_AGENT_PROMPT | llm | StrOutputParser()
    response = chain.invoke({
        "message": last_message,
        "customer_info": json.dumps(customer_info),
        "search_results": search_results,
        "action_result": action_result,
    })

    new_messages = list(messages) + [AIMessage(content=response)]
    return {**state, "messages": new_messages, "action_result": action_result}


# ---- Cancel Agent ----

@traceable(name="cancel_agent", tags=["langgraph", "cancel"])
async def cancel_agent(state: AgentState) -> AgentState:
    """Handle order cancellation."""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    customer_info = state.get("customer_info", {})
    db_session = state.get("db_session")

    import re
    order_id_match = re.search(r'(?:order|#)\s*:?\s*(\d+)', last_message, re.IGNORECASE)
    order_id = int(order_id_match.group(1)) if order_id_match else None

    if order_id and customer_info.get("email"):
        result = await _cancel_order_impl(
            order_id=order_id,
            customer_email=customer_info["email"],
            reason="Customer requested cancellation via chat",
            db_session=db_session,
        )
    elif not order_id:
        result = "Please provide your order ID to cancel. For example: 'cancel order #123'"
    else:
        result = "Please provide your email address to verify your identity for cancellation."

    llm = get_llm(temperature=0.3)
    response_prompt = f"""You are a customer service agent.
Order cancellation result: {result}
Customer message: {last_message}

Respond to the customer about their cancellation request. Be empathetic and professional."""

    response = llm.invoke(response_prompt).content
    new_messages = list(messages) + [AIMessage(content=response)]
    return {**state, "messages": new_messages, "action_result": result}


# ---- Orders Agent ----

@traceable(name="orders_agent", tags=["langgraph", "orders"])
async def orders_agent(state: AgentState) -> AgentState:
    """Handle order status inquiries."""
    customer_info = state.get("customer_info", {})
    db_session = state.get("db_session")
    messages = state["messages"]

    if customer_info.get("email"):
        orders_result = await _list_orders_impl(
            customer_email=customer_info["email"],
            db_session=db_session,
        )
    else:
        orders_result = "Please provide your email address to look up your orders."

    llm = get_llm(temperature=0.3)
    response = llm.invoke(
        f"Customer asked about their orders. Result: {orders_result}\n"
        f"Provide a friendly response about their orders."
    ).content

    new_messages = list(messages) + [AIMessage(content=response)]
    return {**state, "messages": new_messages, "action_result": orders_result}


# ---- General Agent ----

@traceable(name="general_agent", tags=["langgraph", "general"])
async def general_agent(state: AgentState) -> AgentState:
    """Handle general queries."""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""

    llm = get_llm(temperature=0.7)
    response = llm.invoke([
        SystemMessage(content="""You are a friendly e-commerce assistant. 
Help customers with general questions about our store.
We sell electronics, clothing, home goods, and more.
You can help with: searching products, making purchases, checking/cancelling orders."""),
        HumanMessage(content=last_message),
    ]).content

    new_messages = list(messages) + [AIMessage(content=response)]
    return {**state, "messages": new_messages, "action_result": response}


# ---- Routing Logic ----

def route_by_intent(state: AgentState) -> Literal["search", "purchase", "cancel", "orders", "general"]:
    """Route to appropriate agent based on intent."""
    return state.get("next_agent", "general")


# ---- Build the Graph ----

def build_ecommerce_graph() -> StateGraph:
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("router", router_agent)
    workflow.add_node("search", search_agent)
    workflow.add_node("purchase", purchase_agent)
    workflow.add_node("cancel", cancel_agent)
    workflow.add_node("orders", orders_agent)
    workflow.add_node("general", general_agent)

    # Set entry point
    workflow.set_entry_point("router")

    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        route_by_intent,
        {
            "search": "search",
            "purchase": "purchase",
            "cancel": "cancel",
            "orders": "orders",
            "general": "general",
        }
    )

    # All agents end after responding
    for node in ["search", "purchase", "cancel", "orders", "general"]:
        workflow.add_edge(node, END)

    return workflow.compile(checkpointer=MemorySaver())


# Compiled graph (initialized once)
_graph = None

def get_graph():
    global _graph
    if _graph is None:
        _graph = build_ecommerce_graph()
    return _graph


@traceable(name="langgraph_workflow", tags=["langgraph", "ecommerce"])
async def run_agent_workflow(
    message: str,
    session_id: str = None,
    customer_info: dict = None,
    db_session=None,
) -> dict:
    """Run the complete multi-agent workflow."""
    if session_id is None:
        session_id = str(uuid.uuid4())

    graph = get_graph()

    initial_state = AgentState(
        messages=[HumanMessage(content=message)],
        intent=None,
        action_result=None,
        products_found=None,
        next_agent=None,
        customer_info=customer_info or {},
        session_id=session_id,
        db_session=db_session,
    )

    config = {"configurable": {"thread_id": session_id}}

    final_state = await graph.ainvoke(initial_state, config=config)

    # Extract AI response
    ai_messages = [m for m in final_state["messages"] if isinstance(m, AIMessage)]
    response = ai_messages[-1].content if ai_messages else "I couldn't process your request."

    return {
        "response": response,
        "intent": final_state.get("intent"),
        "action_result": final_state.get("action_result"),
        "session_id": session_id,
    }
