from fastapi import HTTPException, Depends, Request
from datetime import datetime, date, timedelta, time
from app.models.audit_model import AuditLogs
from app.config.database import get_db
from sqlalchemy import select, func, update, and_, distinct, delete, desc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError


class AuditService:

    @staticmethod
    async def get_all_logs_by_date_range(
        db, 
        admin_id: str,
        start_date: datetime = None, 
        end_date: datetime = None,
        assistant_id: str = None,
        skip: int = 0, 
        limit: int = 10, 
    ):
        stmt = select(AuditLogs).order_by(desc(AuditLogs.created_at))
        count_stmt = select(func.count()).select_from(AuditLogs)
        filters = [AuditLogs.admin_id == admin_id]
        if start_date:
            filters.append(AuditLogs.created_at >= start_date)
        if end_date:
            filters.append(AuditLogs.created_at <= end_date)
        if assistant_id:
            filters.append(AuditLogs.added_by == assistant_id)

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        total_res = await db.execute(count_stmt)
        
        return result.scalars().all(), total_res.scalar() or 0
    

    @staticmethod
    async def get_all_unique_audit_types(db):
        try:
            query = select(distinct(AuditLogs.entity_name))
            result = await db.execute(query)
            unique_types = result.scalars().all()
            return unique_types
        except SQLAlchemyError as e:
            raise HTTPException(
                status_code=500,
                detail = "Database error while retrieving unique audit types."
            )


    @staticmethod
    async def delete_audit_records(db, admin_id, parsed_start, parsed_end):
        try: 
            query = delete(AuditLogs).where(AuditLogs.admin_id == admin_id, AuditLogs.created_at <= parsed_end)
            if parsed_start:
                start_datetime = datetime.combine(parsed_start, time.min)
                query = query.where(AuditLogs.created_at >= start_datetime)
            result = await db.execute(query)
            await db.commit()
            deleted_rows = result.rowcount
            return deleted_rows
        except SQLAlchemyError as e:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Database error while executing audit logs cleanup."
            )


    @staticmethod
    async def get_all_logs_by_date_range_and_entiry_type(
        db, 
        admin_id: str,
        assistant_id: str,
        entity_type: str,
        skip: int = 0, 
        limit: int = 10, 
        start_date: datetime = None, 
        end_date: datetime = None
    ):
        stmt = select(AuditLogs).order_by(desc(AuditLogs.created_at))
        count_stmt = select(func.count()).select_from(AuditLogs)
        filters = [AuditLogs.admin_id == admin_id]
        if start_date:
            filters.append(AuditLogs.created_at >= start_date)
        if end_date:
            filters.append(AuditLogs.created_at <= end_date)
        if entity_type:
            filters.append(AuditLogs.entity_name == entity_type)
        if assistant_id:
            filters.append(AuditLogs.added_by == assistant_id)

        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))
        stmt = stmt.offset(skip).limit(limit)

        result = await db.execute(stmt)
        total_res = await db.execute(count_stmt)
        
        return result.scalars().all(), total_res.scalar() or 0



