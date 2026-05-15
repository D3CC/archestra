# archestra/models/mixins/soft_delete.py
"""
Soft delete mixin for all models.
Provides a generic way to implement soft deletes across all database models.
"""
from datetime import datetime, timezone
from typing import Optional, Type, TypeVar
from sqlalchemy import Column, DateTime, Boolean, event
from sqlalchemy.orm import Query, Session, declarative_mixin, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

T = TypeVar('T', bound='SoftDeleteMixin')


@declarative_mixin
class SoftDeleteMixin:
    """
    Mixin class that adds soft delete capability to any model.
    
    Usage:
        class User(Base, SoftDeleteMixin):
            __tablename__ = 'users'
            ...
    
    Features:
    - Adds `deleted_at` timestamp column
    - Adds `is_deleted` computed column
    - Automatically filters out deleted records in queries
    - Provides `soft_delete()` and `restore()` methods
    - Supports bulk soft delete operations
    """
    
    @declared_attr
    def deleted_at(cls) -> Column:
        """Timestamp when the record was soft deleted. NULL means not deleted."""
        return Column(DateTime(timezone=True), nullable=True, default=None, index=True)
    
    @declared_attr
    def is_deleted(cls) -> Column:
        """Computed column for efficient querying. True if deleted_at is not NULL."""
        return Column(Boolean, nullable=False, default=False, index=True)
    
    @hybrid_property
    def is_deleted_hybrid(self) -> bool:
        """Hybrid property to check if record is deleted."""
        return self.deleted_at is not None
    
    @is_deleted_hybrid.expression
    def is_deleted_hybrid(cls) -> bool:
        """SQL expression for is_deleted."""
        return cls.deleted_at.isnot(None)
    
    def soft_delete(self, session: Optional[Session] = None) -> None:
        """
        Soft delete this record by setting deleted_at timestamp.
        
        Args:
            session: Optional SQLAlchemy session. If provided, will flush changes.
        """
        self.deleted_at = datetime.now(timezone.utc)
        self.is_deleted = True
        if session:
            session.flush()
    
    def restore(self, session: Optional[Session] = None) -> None:
        """
        Restore a soft deleted record by clearing deleted_at timestamp.
        
        Args:
            session: Optional SQLAlchemy session. If provided, will flush changes.
        """
        self.deleted_at = None
        self.is_deleted = False
        if session:
            session.flush()
    
    @classmethod
    def bulk_soft_delete(cls, session: Session, ids: list) -> int:
        """
        Soft delete multiple records by their primary keys.
        
        Args:
            session: SQLAlchemy session
            ids: List of primary key values to soft delete
            
        Returns:
            Number of records soft deleted
        """
        now = datetime.now(timezone.utc)
        result = session.query(cls).filter(
            cls.id.in_(ids),
            cls.deleted_at.is_(None)
        ).update(
            {'deleted_at': now, 'is_deleted': True},
            synchronize_session='fetch'
        )
        session.flush()
        return result
    
    @classmethod
    def bulk_restore(cls, session: Session, ids: list) -> int:
        """
        Restore multiple soft deleted records by their primary keys.
        
        Args:
            session: SQLAlchemy session
            ids: List of primary key values to restore
            
        Returns:
            Number of records restored
        """
        result = session.query(cls).filter(
            cls.id.in_(ids),
            cls.deleted_at.isnot(None)
        ).update(
            {'deleted_at': None, 'is_deleted': False},
            synchronize_session='fetch'
        )
        session.flush()
        return result


class SoftDeleteQuery(Query):
    """
    Custom query class that automatically filters out soft deleted records.
    Use this as the query_class for models that use SoftDeleteMixin.
    """
    
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        return obj
    
    def __init__(self, entities, session=None):
        super().__init__(entities, session=session)
    
    def __iter__(self):
        return self._apply_soft_delete_filter().__iter__()
    
    def all(self):
        return self._apply_soft_delete_filter().all()
    
    def first(self):
        return self._apply_soft_delete_filter().first()
    
    def one(self):
        return self._apply_soft_delete_filter().one()
    
    def one_or_none(self):
        return self._apply_soft_delete_filter().one_or_none()
    
    def count(self):
        return self._apply_soft_delete_filter().count()
    
    def _apply_soft_delete_filter(self):
        """Apply the soft delete filter to the query."""
        # Check if the primary entity has SoftDeleteMixin
        if self._primary_entity():
            mapper = self._primary_entity().mapper
            if hasattr(mapper.class_, 'deleted_at'):
                # Don't filter if explicitly including deleted
                if not hasattr(self, '_include_deleted') or not self._include_deleted:
                    return self.filter(mapper.class_.deleted_at.is_(None))
        return self
    
    def include_deleted(self):
        """
        Include soft deleted records in the query results.
        Returns a new query that doesn't filter out deleted records.
        """
        q = self._apply_soft_delete_filter()
        q._include_deleted = True
        return q
    
    def only_deleted(self):
        """
        Return only soft deleted records.
        """
        if self._primary_entity():
            mapper = self._primary_entity().mapper
            if hasattr(mapper.class_, 'deleted_at'):
                return self.filter(mapper.class_.deleted_at.isnot(None))
        return self


# Event listeners to automatically update is_deleted when deleted_at changes
@event.listens_for(SoftDeleteMixin.deleted_at, 'set', propagate=True)
def receive_deleted_at_set(target, value, oldvalue, initiator):
    """Update is_deleted when deleted_at is set."""
    target.is_deleted = value is not None


# Helper function to configure a model with soft delete
def configure_soft_delete(model_class: Type[T]) -> Type[T]:
    """
    Configure a model class with soft delete support.
    This sets up the query class and any additional configuration.
    
    Args:
        model_class: The SQLAlchemy model class to configure
        
    Returns:
        The configured model class
    """
    # Set the query class if not already set
    if not hasattr(model_class, 'query_class'):
        model_class.query_class = SoftDeleteQuery
    
    # Add a class method to query with soft delete
    @classmethod
    def query_with_soft_delete(cls, session: Session) -> SoftDeleteQuery:
        """Get a query object with soft delete filtering."""
        return session.query(cls)
    
    model_class.query_with_soft_delete = query_with_soft_delete
    
    return model_class
