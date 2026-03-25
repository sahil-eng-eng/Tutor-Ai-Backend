from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.user import User
from app.models.material import UserMaterial, MaterialType
from app.schemas.curriculum import MaterialUploadResponse
from app.schemas.response import success_response
from app.utils.file_handler import save_upload, validate_file_extension, validate_file_size
from app.services.document_processor import extract_text_from_file

router = APIRouter()


@router.post("/upload", status_code=201)
async def upload_material(
    file: UploadFile = File(...),
    session_id: Optional[UUID] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise BadRequestException("File name is required")
    if not validate_file_extension(file.filename):
        raise BadRequestException("Unsupported file type")

    content = await file.read()
    if not validate_file_size(len(content)):
        raise BadRequestException(f"File too large (max {50}MB)")

    file_path = await save_upload(content, file.filename, f"materials/{user.id}")

    # Determine type
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    type_map = {
        "pdf": MaterialType.PDF,
        "png": MaterialType.IMAGE,
        "jpg": MaterialType.IMAGE,
        "jpeg": MaterialType.IMAGE,
        "txt": MaterialType.TEXT,
        "doc": MaterialType.DOCUMENT,
        "docx": MaterialType.DOCUMENT,
    }
    file_type = type_map.get(ext, MaterialType.DOCUMENT)

    # Auto-extract text content from the uploaded file
    extracted = await extract_text_from_file(file_path, file_type.value)

    material = UserMaterial(
        user_id=user.id,
        session_id=session_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file_type,
        file_size=len(content),
        extracted_content=extracted if extracted else None,
        processed=bool(extracted and not extracted.startswith("[")),
    )
    db.add(material)
    await db.flush()

    result = MaterialUploadResponse.model_validate(material)
    return success_response(data=result, message="Material uploaded and processed")


@router.get("")
async def list_materials(
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count_q = select(func.count()).select_from(UserMaterial).where(UserMaterial.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        select(UserMaterial)
        .where(UserMaterial.user_id == user.id)
        .order_by(UserMaterial.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    materials = result.scalars().all()
    data = [MaterialUploadResponse.model_validate(m) for m in materials]
    return success_response(
        data={"materials": data, "total": total, "page": page, "page_size": page_size},
        message="Materials retrieved",
    )


@router.delete("/{material_id}", status_code=200)
async def delete_material(
    material_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserMaterial).where(
            UserMaterial.id == material_id,
            UserMaterial.user_id == user.id,
        )
    )
    material = result.scalar_one_or_none()
    if not material:
        raise NotFoundException("Material not found")
    await db.delete(material)
    await db.flush()
    return success_response(data={"id": str(material_id)}, message="Material deleted")
