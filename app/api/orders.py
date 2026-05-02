"""Order management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.db.database import get_db
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.schemas import OrderCreate, OrderResponse, OrderCancelRequest

router = APIRouter(prefix="/api/orders", tags=["Orders"])


@router.post("/", response_model=dict, status_code=201)
async def create_order(order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    """Place a new order."""
    # Verify product exists and has stock
    result = await db.execute(
        select(Product).where(Product.id == order_data.product_id, Product.is_active == True)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.stock < order_data.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Only {product.stock} units available."
        )

    # Create order
    total_price = product.price * order_data.quantity
    order = Order(
        product_id=order_data.product_id,
        customer_name=order_data.customer_name,
        customer_email=order_data.customer_email,
        quantity=order_data.quantity,
        total_price=total_price,
        status=OrderStatus.CONFIRMED,
        shipping_address=order_data.shipping_address,
        notes=order_data.notes,
    )
    db.add(order)

    # Deduct stock
    product.stock -= order_data.quantity
    await db.flush()

    return {
        "message": "Order placed successfully",
        "order": order.to_dict(),
    }


@router.get("/", response_model=dict)
async def list_orders(
    email: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List orders, optionally filtered by email or status."""
    query = select(Order)

    if email:
        query = query.where(Order.customer_email == email)
    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.where(Order.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(Order.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    orders = result.scalars().all()

    return {
        "orders": [o.to_dict() for o in orders],
        "page": page,
        "limit": limit,
    }


@router.get("/{order_id}", response_model=dict)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single order by ID."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.to_dict()


@router.post("/{order_id}/cancel", response_model=dict)
async def cancel_order(
    order_id: int,
    cancel_data: OrderCancelRequest,
    email: str = Query(..., description="Customer email for verification"),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order by ID."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_email.lower() != email.lower():
        raise HTTPException(status_code=403, detail="Email verification failed")
    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel order with status: {order.status.value}"
        )

    # Cancel and restore stock
    order.status = OrderStatus.CANCELLED
    order.notes = f"Cancelled: {cancel_data.reason}"

    prod_result = await db.execute(select(Product).where(Product.id == order.product_id))
    product = prod_result.scalar_one_or_none()
    if product:
        product.stock += order.quantity

    await db.flush()
    return {"message": "Order cancelled successfully", "order": order.to_dict()}


@router.put("/{order_id}/status", response_model=dict)
async def update_order_status(
    order_id: int,
    status: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Update order status (admin use)."""
    try:
        new_status = OrderStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = new_status
    await db.flush()
    return {"message": f"Order status updated to {status}", "order": order.to_dict()}
