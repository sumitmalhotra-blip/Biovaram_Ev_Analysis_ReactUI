from sqlalchemy import Column, Integer, String, Float, JSON
from services.tem.tem_service import Base   # reuse Base

class WesternBlot(Base):
    __tablename__ = "western_blot"

    id = Column(Integer, primary_key=True, index=True)
    image_name = Column(String)
    image_url = Column(String)
    lane_count = Column(Integer)
    band_count = Column(Integer)
    kda_data = Column(JSON)