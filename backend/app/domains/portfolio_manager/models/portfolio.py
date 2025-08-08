from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    cash_balance = Column(Numeric(15, 2), default=0)
    portfolio_type = Column(String, default="taxable")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    owner = relationship("User", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
    transactions = relationship("Transaction", back_populates="portfolio")