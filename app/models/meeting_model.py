from sqlalchemy.orm import relationship
from app.config.database import Base
from sqlalchemy import Column, Integer, Boolean, String, DateTime, ForeignKey, select, delete
from datetime import datetime
from app.core.utils_functions import generate_id
from fastapi import HTTPException
import logging
logger = logging.getLogger(__name__)

class MeetingData(Base):
    __tablename__ = "meeting_data"

    id = Column(String, primary_key=True, index=True)
    lead_id = Column(String, ForeignKey("lead_responses.id"))
    meeting_id = Column(String, nullable = False)
    public_join_url = Column(String, nullable = False)
    host_start_url = Column(String, nullable = False)
    duration = Column(Integer, nullable = False)
    topic = Column(String, nullable = False)
    start_time = Column(DateTime, nullable = False)
    created_at = Column(DateTime, default = datetime.utcnow)
    added_by = Column(String, nullable = False)



    @staticmethod
    async def get_by_lead_id(db, lead_id):
        stmt = (
            select(MeetingData)
            .where(MeetingData.lead_id == lead_id)
            .order_by(MeetingData.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().first()
    

    @staticmethod
    async def delete_meeting_details(db, meeting_id):
        stmt = delete(MeetingData).where(MeetingData.meeting_id == meeting_id)
        await db.execute(stmt)
        await db.commit()
        return {
            "message":"meeting data deletion completed successfully."
        }


    async def save_meeting_detials(db, assistant_id, lead_id, data):
        new_meeting = MeetingData(
            id = generate_id(lead_id),
            lead_id = lead_id,
            meeting_id = data["id"],
            public_join_url= data["join_url"],
            host_start_url = data["start_url"],
            duration = data["duration"],
            topic = data["topic"],
            start_time = data["start_time"],
            added_by = assistant_id
        )

        db.add(new_meeting)
        await db.commit()
        await db.refresh(new_meeting)
        logger.info("MeetingData: new meeting data saved successfully.")
        return new_meeting

    
    async def update_meeting_detials(db, assistant_id, lead_id, data):
        meet = await MeetingData.get_by_lead_id(db, lead_id)
        if not meet:
            logger.info("MeetingData: no any meeting found, so you can'y able to updata that.")
            raise HTTPException(404, "no any meeting found, so you can't able to update.")
        meet.meeting_id = data["id"]
        meet.public_join_url= data["join_url"]
        meet.host_start_url = data["start_url"]
        meet.duration = data["duration"]
        meet.topic = data["topic"]
        meet.start_time = data["start_time"]
        meet.added_by = assistant_id
        await db.commit()
        await db.refresh(meet)
        logger.info("MeetingData: meeting data updated successfully.")
        return meet


    def to_dict(self, exclude=None):
        if exclude is None:
            exclude = ["password"]  # Protect sensitive fields
            
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
                
            value = getattr(self, column.name)
            
            # Convert datetime objects to string format
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
                
        return result