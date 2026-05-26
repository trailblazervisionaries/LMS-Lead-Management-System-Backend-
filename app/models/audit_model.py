from sqlalchemy import Column, String, Boolean, JSON, ForeignKey, DateTime, func, select, or_, and_, false
from sqlalchemy.orm import relationship, selectinload, joinedload
from app.config.database import Base
from datetime import datetime, time


class AuditLogs(Base):
    __tablename__ = "auditlogs"
    id = Column(String, primary_key = True)
    entity_name = Column(String, nullable = False)
    entity_id = Column(String, nullable = False)
    log_type = Column(String, nullable = False)
    prev_data = Column(JSON, nullable = True)
    new_data = Column(JSON, nullable = True)
    added_by = Column(String, nullable = False, index= True)
    admin_id = Column(String, nullable = False, index = True)
    created_at = Column( DateTime, default = datetime.utcnow)



    @staticmethod
    def _apply_date_filter(query, from_date, to_date):
        if from_date:
            query = query.where(AuditLogs.created_at >= datetime.combine(from_date, time.min))
        if to_date:
            query = query.where(AuditLogs.created_at <= datetime.combine(to_date, time.max))
        return query


    @staticmethod
    def _apply_filters(query, filters: dict):
        conditions = []

        for field, value in filters.items():
            if value is not None:
                conditions.append(getattr(AuditLogs, field) == value)

        if conditions:
            query = query.where(and_(*conditions))

        return query


    @classmethod
    async def _fetch_logs(
        cls,
        db,
        filters: dict = None,
        from_date=None,
        to_date=None,
        page: int = 1,
        page_size: int = 10,
    ):
        query = select(cls)

        # Apply dynamic filters
        if filters:
            query = cls._apply_filters(query, filters)

        # Apply date filter
        query = cls._apply_date_filter(query, from_date, to_date)

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        return result.scalars().all()



    @classmethod
    async def get_by_admin(
        cls, db, admin_id, from_date=None, to_date=None, page=1, page_size=10
    ):
        return await cls._fetch_logs(
            db,
            filters={"admin_id": admin_id},
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )



    @classmethod
    async def get_by_added_by(
        cls, db, added_by, from_date=None, to_date=None, page=1, page_size=10
    ):
        return await cls._fetch_logs(
            db,
            filters={"added_by": added_by},
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )



    @classmethod
    async def get_by_admin_with_filters(
        cls,
        db,
        admin_id,
        entity_name=None,
        log_type=None,
        from_date=None,
        to_date=None,
        page=1,
        page_size=10,
    ):
        return await cls._fetch_logs(
            db,
            filters={
                "admin_id": admin_id,
                "entity_name": entity_name,
                "log_type": log_type,
            },
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )



    @classmethod
    async def get_by_added_by_with_filters(
        cls,
        db,
        added_by,
        entity_name=None,
        log_type=None,
        from_date=None,
        to_date=None,
        page=1,
        page_size=10,
    ):
        return await cls._fetch_logs(
            db,
            filters={
                "added_by": added_by,
                "entity_name": entity_name,
                "log_type": log_type,
            },
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )


