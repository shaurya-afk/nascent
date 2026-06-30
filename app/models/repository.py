from app.models.base import Base

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

class Repository(Base):
    __tablename__="repository"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    github_url: Mapped[String] = mapped_column(
        String,
        nullable=False,
        unique=True
    )

    files = relationship(
        "RepositoryFile",
        back_populates="repository",
        cascade="all, delete-orphan"
    )