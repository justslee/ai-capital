from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    transaction_type = Column(String, nullable=False)
    quantity = Column(Numeric(15, 4), nullable=False)
    price_per_share = Column(Numeric(15, 4), nullable=False)
    total_value = Column(Numeric(15, 2), nullable=False)
    fees = Column(Numeric(15, 2), default=0)
    transaction_date = Column(DateTime, nullable=False)
    notes = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    
    portfolio = relationship("Portfolio", back_populates="transactions")