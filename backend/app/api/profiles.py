from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from app.api.auth import get_current_user
from app.services.sanitizer import sanitize_name, sanitize_grade
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

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
):
    clean_name = sanitize_name(req.child_name)
    if not clean_name:
        raise HTTPException(status_code=400, detail="Invalid child name")

    clean_grade = sanitize_grade(req.grade) if req.grade else None

    existing = supabase.table("child_profiles").select("id").eq(
        "user_id", current_user["user_id"]
    ).execute()

    if current_user["role"] == "teacher" and len(existing.data) >= 30:
        raise HTTPException(status_code=400, detail="Teacher accounts support up to 30 student profiles")

    user = supabase.table("users").select("client_id").eq(
        "id", current_user["user_id"]
    ).execute()
    client_id = user.data[0]["client_id"] if user.data else None

    result = supabase.table("child_profiles").insert({
        "user_id": current_user["user_id"],
        "child_name": clean_name,
        "age": req.age,
        "grade": clean_grade,
        "client_id": client_id,
    }).execute()

    return {"profile": result.data[0], "message": f"Profile created for {clean_name} 🐦"}


@router.get("/")
async def get_profiles(current_user: dict = Depends(get_current_user)):
    result = supabase.table("child_profiles").select("*").eq(
        "user_id", current_user["user_id"]
    ).execute()
    return {"profiles": result.data, "count": len(result.data)}


@router.get("/{profile_id}")
async def get_profile(
    profile_id: str,
    current_user: dict = Depends(get_current_user),
):
    result = supabase.table("child_profiles").select("*").eq(
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
):
    existing = supabase.table("child_profiles").select("id").eq(
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

    result = supabase.table("child_profiles").update(updates).eq(
        "id", profile_id
    ).execute()

    return {"profile": result.data[0], "message": "Profile updated ✅"}


@router.delete("/{profile_id}")
async def delete_profile(
    profile_id: str,
    current_user: dict = Depends(get_current_user),
):
    existing = supabase.table("child_profiles").select("id").eq(
        "id", profile_id
    ).eq("user_id", current_user["user_id"]).execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    supabase.table("child_profiles").delete().eq("id", profile_id).execute()
    return {"message": "Profile deleted ✅"}
