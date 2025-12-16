from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    uploaded_assets = relationship("UploadedAsset", back_populates="user")


class UploadedAsset(Base):
    __tablename__ = "uploaded_assets"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    type = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="uploaded_assets")
