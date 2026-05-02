"""
Seed script - Populates PostgreSQL with sample products and indexes them in vector store.
Run: python scripts/seed_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import settings
from app.db.database import Base
from app.models.product import Product
from app.models.order import Order


SAMPLE_PRODUCTS = [
    # Electronics
    {"name": "Sony WH-1000XM5 Headphones", "category": "Electronics", "brand": "Sony",
     "price": 399.99, "stock": 50, "rating": 4.8, "review_count": 2340,
     "description": "Industry-leading noise canceling headphones with 30-hour battery life, crystal clear hands-free calling, and Alexa built-in. Premium sound quality with LDAC."},
    {"name": "Apple MacBook Air M2", "category": "Electronics", "brand": "Apple",
     "price": 1299.00, "stock": 25, "rating": 4.9, "review_count": 1820,
     "description": "Supercharged by M2 chip. Up to 18 hours battery. 13.6-inch Liquid Retina display. 8GB RAM, 256GB SSD. Thin and light design."},
    {"name": "Samsung 65\" QLED 4K TV", "category": "Electronics", "brand": "Samsung",
     "price": 1499.99, "stock": 15, "rating": 4.7, "review_count": 987,
     "description": "Quantum Dot technology with 4K resolution, HDR10+, and 120Hz refresh rate. Alexa and Google Assistant built-in. HDMI 2.1 ports."},
    {"name": "iPad Air 5th Generation", "category": "Electronics", "brand": "Apple",
     "price": 749.00, "stock": 40, "rating": 4.8, "review_count": 1560,
     "description": "Powerful M1 chip, 10.9-inch Liquid Retina display, 5G capable, USB-C connectivity, and Apple Pencil support."},
    {"name": "Logitech MX Master 3 Mouse", "category": "Electronics", "brand": "Logitech",
     "price": 99.99, "stock": 120, "rating": 4.7, "review_count": 4521,
     "description": "Advanced wireless mouse for professionals. Ergonomic design, 8K DPI tracking, 70-day battery, multi-device and OS support."},
    {"name": "Samsung Galaxy S24 Ultra", "category": "Electronics", "brand": "Samsung",
     "price": 1199.99, "stock": 30, "rating": 4.6, "review_count": 892,
     "description": "200MP camera, built-in S Pen, Snapdragon 8 Gen 3, 12GB RAM, 5000mAh battery. AI-powered photography."},

    # Home & Kitchen
    {"name": "Instant Pot Duo 7-in-1", "category": "Home & Kitchen", "brand": "Instant Pot",
     "price": 89.99, "stock": 200, "rating": 4.7, "review_count": 8923,
     "description": "Electric Pressure Cooker, Slow Cooker, Rice Cooker, Steamer, Sauté, Yogurt Maker, Warmer. 6-quart capacity."},
    {"name": "Dyson V15 Detect Vacuum", "category": "Home & Kitchen", "brand": "Dyson",
     "price": 749.99, "stock": 35, "rating": 4.8, "review_count": 1234,
     "description": "Laser detects microscopic dust. 60-minute runtime. HEPA filtration. LCD screen shows performance. Intelligent suction."},
    {"name": "Nespresso Vertuo Next Coffee Maker", "category": "Home & Kitchen", "brand": "Nespresso",
     "price": 179.99, "stock": 60, "rating": 4.6, "review_count": 3421,
     "description": "Brews 5 cup sizes with one touch. Centrifusion technology. WiFi connected. Recyclable aluminum capsules. 54 oz water tank."},
    {"name": "KitchenAid Stand Mixer 5Qt", "category": "Home & Kitchen", "brand": "KitchenAid",
     "price": 449.99, "stock": 20, "rating": 4.9, "review_count": 5678,
     "description": "10 speeds, 5-quart stainless steel bowl, 59 touchpoints around the bowl. Includes flat beater, dough hook, and wire whip."},

    # Clothing
    {"name": "Nike Air Max 270", "category": "Clothing & Shoes", "brand": "Nike",
     "price": 150.00, "stock": 85, "rating": 4.5, "review_count": 2876,
     "description": "Max Air unit in the heel for all-day comfort. Mesh upper for breathability. Foam midsole for lightweight cushioning. Available in multiple colors."},
    {"name": "Levi's 501 Original Jeans", "category": "Clothing & Shoes", "brand": "Levi's",
     "price": 69.99, "stock": 150, "rating": 4.4, "review_count": 7234,
     "description": "The original straight leg jeans since 1873. 100% cotton denim. Button fly. Sits at waist. Straight through hip, thigh, and leg."},
    {"name": "Patagonia Nano Puff Jacket", "category": "Clothing & Shoes", "brand": "Patagonia",
     "price": 279.00, "stock": 45, "rating": 4.7, "review_count": 1567,
     "description": "PrimaLoft Gold Insulation Eco. Wind and water resistant. Stuffs into its own chest pocket. Recycled polyester shell and lining."},
    {"name": "Champion Reverse Weave Hoodie", "category": "Clothing & Shoes", "brand": "Champion",
     "price": 65.00, "stock": 200, "rating": 4.5, "review_count": 3456,
     "description": "Heavyweight fleece, ribbed side panels, and kangaroo pocket. Reverse weave construction resists shrinkage. Available in many colors."},

    # Books
    {"name": "Atomic Habits by James Clear", "category": "Books", "brand": "Penguin",
     "price": 18.99, "stock": 500, "rating": 4.9, "review_count": 45678,
     "description": "An Easy & Proven Way to Build Good Habits & Break Bad Ones. #1 New York Times bestseller. Practical strategies for forming good habits."},
    {"name": "The Psychology of Money", "category": "Books", "brand": "Harriman House",
     "price": 16.99, "stock": 300, "rating": 4.8, "review_count": 23456,
     "description": "Timeless lessons on wealth, greed, and happiness by Morgan Housel. 19 short stories exploring the strange ways people think about money."},

    # Sports & Fitness
    {"name": "Peloton Bike+ Stationary Bike", "category": "Sports & Fitness", "brand": "Peloton",
     "price": 2495.00, "stock": 10, "rating": 4.7, "review_count": 4321,
     "description": "24\" HD touchscreen rotates for off-bike workouts. Auto-resistance. Immersive classes. Built-in camera and microphone."},
    {"name": "Bowflex SelectTech 552 Dumbbells", "category": "Sports & Fitness", "brand": "Bowflex",
     "price": 429.00, "stock": 25, "rating": 4.7, "review_count": 8901,
     "description": "Adjusts from 5 to 52.5 lbs. Replaces 15 sets of weights. Easy dial system. Durable molding around metal plates."},
    {"name": "Garmin Forerunner 265 GPS Watch", "category": "Sports & Fitness", "brand": "Garmin",
     "price": 449.99, "stock": 40, "rating": 4.6, "review_count": 1234,
     "description": "AMOLED display, training readiness, race predictor, heart rate monitoring, 13-day battery life, multi-sport tracking."},

    # Beauty
    {"name": "Dyson Airwrap Multi-Styler", "category": "Beauty", "brand": "Dyson",
     "price": 599.99, "stock": 30, "rating": 4.5, "review_count": 3456,
     "description": "Styles, waves, curls, and dries with no extreme heat. Coanda effect to attract and wrap hair. Multiple attachments included."},
    {"name": "CeraVe Moisturizing Cream 16oz", "category": "Beauty", "brand": "CeraVe",
     "price": 19.99, "stock": 400, "rating": 4.8, "review_count": 89012,
     "description": "For normal to dry skin. 3 essential ceramides and hyaluronic acid. Non-comedogenic, fragrance-free. Gentle enough for sensitive skin."},
]


async def seed_database():
    """Create tables and seed with sample data."""
    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSession_ = async_sessionmaker(engine, expire_on_commit=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Tables created")

    async with AsyncSession_() as session:
        # Check if already seeded
        from sqlalchemy import select, func
        count_result = await session.execute(select(func.count()).select_from(Product))
        count = count_result.scalar()

        if count > 0:
            print(f"ℹ️  Database already has {count} products. Skipping seed.")
            return

        # Add products
        products = []
        for data in SAMPLE_PRODUCTS:
            product = Product(**data)
            session.add(product)
            products.append(product)

        await session.commit()
        print(f"✅ Added {len(products)} products to database")

        # Re-fetch to get IDs
        result = await session.execute(select(Product))
        db_products = result.scalars().all()

    await engine.dispose()

    # Index into vector store
    print("🔄 Indexing products into vector store...")
    try:
        from app.rag.vector_store import index_products
        products_data = [p.to_dict() for p in db_products]
        count = index_products(products_data)
        print(f"✅ Indexed {count} products into vector store (ChromaDB)")
    except Exception as e:
        print(f"⚠️  Vector store indexing failed: {e}")
        print("   Run /api/admin/reindex after starting the app to index products.")

    print("\n🎉 Database seeded successfully!")
    print(f"   Total products: {len(SAMPLE_PRODUCTS)}")
    print("   Categories: Electronics, Home & Kitchen, Clothing, Books, Sports, Beauty")
    print("\nNext steps:")
    print("  1. Start the app: uvicorn app.main:app --reload")
    print("  2. Open http://localhost:8000")
    print("  3. Try the AI chat assistant!")


if __name__ == "__main__":
    asyncio.run(seed_database())
