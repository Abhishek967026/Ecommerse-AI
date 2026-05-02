"""Product SQLAlchemy model."""
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    brand = Column(String(100), nullable=True)
    stock = Column(Integer, default=0)
    image_url = Column(String(500), nullable=True)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "category": self.category,
            "brand": self.brand,
            "stock": self.stock,
            "image_url": self.image_url,
            "rating": self.rating,
            "review_count": self.review_count,
            "is_active": self.is_active,
        }

    def to_text(self) -> str:
        """Convert to text for vector embedding."""
        return (
            f"Product: {self.name}\n"
            f"Category: {self.category}\n"
            f"Brand: {self.brand or 'Unknown'}\n"
            f"Price: ${self.price:.2f}\n"
            f"Description: {self.description or 'No description'}\n"
            f"Rating: {self.rating}/5 ({self.review_count} reviews)\n"
            f"In Stock: {'Yes' if self.stock > 0 else 'No'} ({self.stock} units)"
        )
