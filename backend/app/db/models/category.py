from sqlalchemy import Column, String
from app.db.base import Base

class Category(Base):
    __tablename__ = "categories"
    name = Column(String, primary_key=True, unique=True, nullable=False)