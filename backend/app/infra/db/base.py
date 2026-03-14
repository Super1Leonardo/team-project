from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)


class CreatedAtMixin:
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)


class UpdatedAtMixin:
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
