from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.api.auth import get_current_user
from app.api.dependencies import get_tenant_db
from app.db.tenant import TenantSafeQuery
from app.services.sanitizer import sanitize_name, sanitize_grade

router = APIRouter(prefix="/profiles", tags=["profiles"])


class CreateProfileRequest(BaseModel):
    child_name: str
    age: Optional[int] = None
    grade: Optional[str] = None


class UpdateProfileRequest(BaseModel):
    child_name: Optional[str] = None
    age: Optional[int] = None
    grade: Optional[str] = None


@router.post("/")
async def create_profile(
    req: CreateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    clean_name = sanitize_name(req.child_name)
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid child name")

    clean_grade = sanitize_grade(req.grade) if req.grade else None

    existing = db.table("child_profiles").select("id").eq(
        "user_id", current_user["user_id"]
    ).execute()

    if current_user["role"] == "teacher" and len(existing.data) >= 30:
        raise HTTPException(status_code=400, detail="Teacher accounts support up to 30 student profiles")

    result = db.table("child_profiles").insert({
        "user_id": current_user["user_id"],
        "child_name": clean_name,
        "age": req.age,
        "grade": clean_grade,
    }).execute()

    return {"profile": result.data[0], "message": f"Profile created for {clean_name}"}


@router.get("/")
async def get_profiles(
    current_user: dict = Depends(get_current_user),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    result = db.table("child_profiles").select("*").eq(
        "user_id", current_user["user_id"]
    ).execute()
    profiles = result.data or []

    # Attach the class name for any child enrolled in a classroom
    class_ids = list({p["classroom_id"] for p in profiles if p.get("classroom_id")})
    names = {}
    if class_ids:
        rows = db.table("classrooms").select("id, name").in_("id", class_ids).execute()
        names = {r["id"]: r["name"] for r in (rows.data or [])}
    for p in profiles:
        p["classroom_name"] = names.get(p.get("classroom_id"))

    return {"profiles": profiles, "count": len(profiles)}


@router.get("/{profile_id}")
async def get_profile(
    profile_id: str,
    current_user: dict = Depends(get_current_user),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    result = db.table("child_profiles").select("*").eq(
        "id", profile_id
    ).eq("user_id", current_user["user_id"]).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"profile": result.data[0]}


@router.put("/{profile_id}")
async def update_profile(
    profile_id: str,
    req: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    existing = db.table("child_profiles").select("id").eq(
        "id", profile_id
    ).eq("user_id", current_user["user_id"]).execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    updates = {}
    if req.child_name is not None:
        clean_name = sanitize_name(req.child_name)
        if not clean_name:
            raise HTTPException(status_code=400, detail="Invalid child name")
        updates["child_name"] = clean_name
    if req.age is not None:
        updates["age"] = req.age
    if req.grade is not None:
        updates["grade"] = sanitize_grade(req.grade)

    result = db.table("child_profiles").update(updates).eq("id", profile_id).execute()
    return {"profile": result.data[0], "message": "Profile updated"}


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: str,
    current_user: dict = Depends(get_current_user),
    db: TenantSafeQuery = Depends(get_tenant_db),
):
    existing = db.table("child_profiles").select("id").eq(
        "id", profile_id
    ).eq("user_id", current_user["user_id"]).execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    db.table("child_profiles").delete().eq("id", profile_id).execute()
    return {"message": "Profile deleted"}
