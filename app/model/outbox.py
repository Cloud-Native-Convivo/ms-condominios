from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Identity,
    Index,
    Integer,
    String,
    Text,
    false,
    text,
)

from app.config.database import Base


class Outbox(Base):
    __tablename__ = "outbox"
    # El relay filtra pendientes por processed y los recorre por id
    __table_args__ = (Index("ix_outbox_processed_id", "processed", "id"),)

    id = Column(Integer, Identity(), primary_key=True)
    aggregate_type = Column(String(255), nullable=False)
    aggregate_id = Column(String(255), nullable=False)
    type = Column(String(255), nullable=False)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text("SYS_EXTRACT_UTC(SYSTIMESTAMP)"))
    processed = Column(Boolean, nullable=False, default=False, server_default=false())
