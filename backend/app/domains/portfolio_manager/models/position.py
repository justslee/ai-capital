from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Position(Base):
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    quantity = Column(Numeric(15, 4), nullable=False)
    average_cost_basis = Column(Numeric(15, 4), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    portfolio = relationship("Portfolio", back_populates="positions")