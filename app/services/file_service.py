from app.models.user_model import Users
from sqlalchemy.ext.asyncio import AsyncSession as Session
from fastapi.responses import StreamingResponse
from fastapi import HTTPException, UploadFile, Request
from app.models.audit_model import AuditLogs
from dotenv import load_dotenv
import os
import logging
from typing import List, Optional
import aioboto3
from app.core.utils_functions import generate_image_id
from contextlib import asynccontextmanager
load_dotenv()
logger = logging.getLogger(__name__)


S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY")
class FileUploadService:

    def __init__(self, id: str):
        self.id = id
        self.session = aioboto3.Session()

    @asynccontextmanager
    async def _get_s3_client(self):
        """Yields an async S3 client using explicit credentials."""
        async with self.session.client(
            "s3", 
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID,      
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY   
        ) as client:
            yield client

    def _generate_s3_key(self, folder_name: str, filename: str) -> str:
        """Helper to generate standard S3 structural keys instead of local paths."""
        return f"uploads/{self.id}/{folder_name}/{filename}".replace("//", "/")

    def create_folder(self, folder_name: str) -> str:
        """
        In S3, folders don't physically exist until a file is inside.
        We return the virtual prefix path for consistency with your architecture.
        """
        virtual_path = f"uploads/{self.id}/{folder_name}/"
        logger.info(f"FileUploadService: S3 virtual prefix defined: {virtual_path}")
        return virtual_path

    async def delete_file(self, file_url_or_key: str) -> bool:
        """
        Deletes a single object from S3 using either its full URL or S3 key.
        Returns True if deleted or if it didn't exist.
        """
        try:
            # Extract key from URL if absolute URL is passed
            s3_key = file_url_or_key
            if "amazonaws.com/" in file_url_or_key:
                s3_key = file_url_or_key.split("amazonaws.com/")[-1]

            async with self._get_s3_client() as s3:
                await s3.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                logger.info(f"FileUploadService: S3 object {s3_key} deleted successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to delete S3 object: {file_url_or_key}. Error: {e}")
            return False
    
    async def delete_folder(self, folder_prefix: str) -> bool:
        """
        Deletes a virtual folder (prefix) and all contents inside it from S3.
        """
        try:
            # Extract key from URL if absolute URL is passed
            if "amazonaws.com/" in folder_prefix:
                folder_prefix = folder_prefix.split("amazonaws.com/")[-1]
            
            # Ensure it ends with a slash to avoid deleting sibling folders
            if not folder_prefix.endswith("/"):
                folder_prefix += "/"

            async with self._get_s3_client() as s3:
                # Paginate and find all items under the prefix
                paginator = s3.get_paginator("list_objects_v2")
                async for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=folder_prefix):
                    if "Contents" in page:
                        objects_to_delete = [{"Key": obj["Key"]} for obj in page["Contents"]]
                        if objects_to_delete:
                            await s3.delete_objects(
                                Bucket=S3_BUCKET_NAME,
                                Delete={"Objects": objects_to_delete}
                            )
                
                logger.info(f"FileUploadService: S3 virtual folder {folder_prefix} deleted successfully.")
                return True
        except Exception as e:
            logger.error(f"Failed to delete S3 folder prefix: {folder_prefix}. Error: {e}")
            return False

    async def upload_file(self, file: UploadFile, folder: str) -> dict:
        """
        Uploads a single file to S3 asynchronously.
        """
        ext = file.filename.split(".")[-1] if "." in file.filename else ""
        unique_name = f"{generate_image_id()}.{ext}" if ext else generate_image_id()
        
        s3_key = self._generate_s3_key(folder, unique_name)
        
        # Read file contents
        content = await file.read()
        
        async with self._get_s3_client() as s3:
            # You can add ExtraArgs if you want them to be public or have specific ContentTypes
            await s3.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type
            )

        logger.info("FileUploadService: File uploaded to S3 successfully.")
        return {
            "filepath": s3_key,
            "folder_path": f"uploads/{self.id}/{folder}/"
        }

    @staticmethod
    def convert_to_public_url(request: Request, s3_key: Optional[str]) -> Optional[str]:
        """
        Converts an S3 key into its standard AWS S3 public URL format.
        (If your bucket is private, you would generate presigned URLs here instead)
        """
        if not s3_key:
            return None
        # Standard S3 URL formulation
        return f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

    @staticmethod
    async def upload_profile_image(db, file, logged_user_id, user_id, name, request):
        user_data = await Users.get_by_id(db, user_id)
        if not user_data:
            raise ValueError("User not found")
            
        service = FileUploadService(user_id)

        if file:
            resp = await service.upload_file(file, f"{user_id}")
            if not resp:
                logger.error("FileUploadService: S3 file upload failed")
                raise HTTPException(500, "File upload failed")

            # Generate public S3 URL
            file_url = FileUploadService.convert_to_public_url(request, resp["filepath"])
            user_data.profile_image = file_url

            await db.commit()
            await db.refresh(user_data)

            return {
                "message": "Profile image uploaded successfully",
                "profile_image": file_url,
            }



    @staticmethod
    async def get_folder_public_links(request: Request, folder_prefix: str) -> List[str]:
        """
        Queries S3 via aioboto3 to list items under a prefix and returns public URLs.
        """
        if not folder_prefix:
            return []

        if "amazonaws.com/" in folder_prefix:
            folder_prefix = folder_prefix.split("amazonaws.com/")[-1]

        public_urls = []
        session = aioboto3.Session()
        
        async with session.client("s3", region_name=AWS_REGION) as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=folder_prefix):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        # Exclude any directory placeholders if they exist
                        if not obj["Key"].endswith("/"):
                            public_urls.append(FileUploadService.convert_to_public_url(request, obj["Key"]))
                            
        logger.info("FileUploadService: Generated public S3 object links dynamically via prefix scanner.")
        return public_urls


    async def get_profile_image_buffer(db, request, user_id):
        user = await Users.get_by_id(db, user_id)
        if not user:
            raise HTTPException(404, "User not found so we can't fetch image.")
        return FileUploadService.convert_to_public_url(request, user.profile_image)

        


