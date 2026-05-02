"""Product CRUD API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from app.db.database import get_db
from app.models.product import Product
from app.models.schemas import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("/", response_model=dict)
async def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all products with optional filtering and pagination."""
    query = select(Product).where(Product.is_active == True)

    if category:
        query = query.where(Product.category.ilike(f"%{category}%"))
    if search:
        query = query.where(
            Product.name.ilike(f"%{search}%") | Product.description.ilike(f"%{search}%")
        )
    if min_price is not None:
        query = query.where(Product.price >= min_price)
    if max_price is not None:
        query = query.where(Product.price <= max_price)
    if in_stock is not None:
        if in_stock:
            query = query.where(Product.stock > 0)
        else:
            query = query.where(Product.stock == 0)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    products = result.scalars().all()

    return {
        "products": [p.to_dict() for p in products],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@router.get("/categories", response_model=List[str])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Get all unique product categories."""
    result = await db.execute(
        select(Product.category).where(Product.is_active == True).distinct()
    )
    return [row[0] for row in result.fetchall()]


@router.get("/{product_id}", response_model=dict)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single product by ID."""
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.is_active == True)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product.to_dict()


@router.post("/", response_model=dict, status_code=201)
async def create_product(product_data: ProductCreate, db: AsyncSession = Depends(get_db)):
    """Create a new product."""
    product = Product(**product_data.model_dump())
    db.add(product)
    await db.flush()
    return {"message": "Product created", "product": product.to_dict()}


@router.put("/{product_id}", response_model=dict)
async def update_product(
    product_id: int,
    update_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.flush()
    return {"message": "Product updated", "product": product.to_dict()}


@router.delete("/{product_id}", response_model=dict)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """Soft-delete a product (set is_active=False)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    await db.flush()
    return {"message": "Product deleted successfully"}
