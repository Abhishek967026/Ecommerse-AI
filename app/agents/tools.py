"""Tools available to AI agents for e-commerce operations."""
from typing import Optional, List
from langchain.tools import tool
from langsmith import traceable


# ---- Tool implementations (called by both LangGraph and CrewAI) ----

async def _search_products_impl(query: str, db_session=None) -> str:
    """Search products in DB and vector store."""
    from app.rag.vector_store import similarity_search
    docs = similarity_search(query, k=5)
    if not docs:
        return "No products found matching your query."
    results = []
    for doc in docs:
        meta = doc.metadata
        results.append(
            f"ID:{meta.get('product_id')} | {meta.get('name')} | "
            f"${meta.get('price', 0):.2f} | "
            f"{'In Stock' if meta.get('stock', 0) > 0 else 'Out of Stock'}"
        )
    return "Found products:\n" + "\n".join(results)


async def _get_product_details_impl(product_id: int, db_session=None) -> str:
    """Get full product details from DB."""
    from sqlalchemy import select
    from app.models.product import Product
    if db_session is None:
        return "Database session not available."
    try:
        result = await db_session.execute(
            select(Product).where(Product.id == product_id, Product.is_active == True)
        )
        product = result.scalar_one_or_none()
        if not product:
            return f"Product with ID {product_id} not found."
        return product.to_text()
    except Exception as e:
        return f"Error fetching product: {e}"


async def _create_order_impl(
    product_id: int,
    customer_name: str,
    customer_email: str,
    quantity: int = 1,
    shipping_address: str = "",
    db_session=None,
) -> str:
    """Create a new order in the database."""
    from sqlalchemy import select
    from app.models.product import Product
    from app.models.order import Order, OrderStatus
    if db_session is None:
        return "Database session not available."
    try:
        # Check product exists and has stock
        result = await db_session.execute(
            select(Product).where(Product.id == product_id, Product.is_active == True)
        )
        product = result.scalar_one_or_none()
        if not product:
            return f"Product ID {product_id} not found."
        if product.stock < quantity:
            return f"Insufficient stock. Only {product.stock} units available."

        total_price = product.price * quantity

        # Create order
        order = Order(
            product_id=product_id,
            customer_name=customer_name,
            customer_email=customer_email,
            quantity=quantity,
            total_price=total_price,
            status=OrderStatus.CONFIRMED,
            shipping_address=shipping_address,
        )
        db_session.add(order)

        # Reduce stock
        product.stock -= quantity
        await db_session.flush()

        return (
            f"✅ Order created successfully!\n"
            f"Order ID: {order.id}\n"
            f"Product: {product.name}\n"
            f"Quantity: {quantity}\n"
            f"Total: ${total_price:.2f}\n"
            f"Status: Confirmed\n"
            f"You'll receive confirmation at {customer_email}"
        )
    except Exception as e:
        return f"Error creating order: {e}"


async def _cancel_order_impl(
    order_id: int,
    customer_email: str,
    reason: str = "Customer request",
    db_session=None,
) -> str:
    """Cancel an existing order."""
    from sqlalchemy import select
    from app.models.order import Order, OrderStatus
    from app.models.product import Product
    if db_session is None:
        return "Database session not available."
    try:
        result = await db_session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            return f"Order ID {order_id} not found."
        if order.customer_email.lower() != customer_email.lower():
            return "Email does not match the order. Cancellation denied."
        if order.status.value in ["delivered", "cancelled"]:
            return f"Cannot cancel order with status: {order.status.value}"

        # Cancel order and restore stock
        order.status = OrderStatus.CANCELLED
        order.notes = f"Cancelled: {reason}"

        prod_result = await db_session.execute(
            select(Product).where(Product.id == order.product_id)
        )
        product = prod_result.scalar_one_or_none()
        if product:
            product.stock += order.quantity

        await db_session.flush()
        return (
            f"✅ Order #{order_id} cancelled successfully.\n"
            f"Reason: {reason}\n"
            f"Stock has been restored."
        )
    except Exception as e:
        return f"Error cancelling order: {e}"


async def _list_orders_impl(customer_email: str, db_session=None) -> str:
    """List all orders for a customer."""
    from sqlalchemy import select
    from app.models.order import Order
    if db_session is None:
        return "Database session not available."
    try:
        result = await db_session.execute(
            select(Order).where(Order.customer_email == customer_email)
        )
        orders = result.scalars().all()
        if not orders:
            return f"No orders found for {customer_email}"
        lines = [f"Orders for {customer_email}:"]
        for o in orders:
            lines.append(
                f"  Order #{o.id} | Status: {o.status.value} | "
                f"Total: ${o.total_price:.2f} | Date: {str(o.created_at)[:10]}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching orders: {e}"
