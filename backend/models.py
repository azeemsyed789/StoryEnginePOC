from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    uploaded_assets = relationship("UploadedAsset", back_populates="user")
    designs = relationship("StoryDesign", back_populates="user")


class UploadedAsset(Base):
    __tablename__ = "uploaded_assets"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    type = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="uploaded_assets")


class StoryDesign(Base):
    __tablename__ = "story_designs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_face_filename = Column(String, nullable=False)
    pages_json = Column(Text, nullable=False)
    status = Column(String, default="pending_admin")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="designs")
