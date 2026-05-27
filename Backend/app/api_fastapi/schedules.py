from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..permission_middleware import require_permission
from datetime import date
from typing import List, Optional

from ..database import get_db
from ..models import User, Schedule, User
from ..schemas_fastapi import ScheduleOut, ScheduleCreate, ScheduleUpdate
from ..services.auth_helper import get_username_from_request
from ..services.general_diary import create_general_diary_entry
from ..logger import log_error

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/", response_model=List[ScheduleOut])
def list_schedules(db: Session = Depends(get_db),
    _: User = Depends(require_permission('schedules.view'))):
    """Lấy danh sách tất cả lịch làm việc"""
    schedules = db.query(Schedule).all()
    result = []
    for s in schedules:
        employee = db.query(User).filter(User.id == s.employee_id).first()
        schedule_dict = {
            "id": s.id,
            "employee_id": s.employee_id,
            "work_date": s.work_date,
            "shift_type": s.shift_type,
            "notes": s.notes,
            "employee_name": employee.name if employee else None
        }
        result.append(ScheduleOut(**schedule_dict))
    return result


@router.get("/{schedule_id}", response_model=ScheduleOut)
def get_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin một lịch làm việc"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch làm việc")
    
    employee = db.query(User).filter(User.id == schedule.employee_id).first()
    schedule_dict = ScheduleOut.model_validate(schedule).model_dump()
    schedule_dict['employee_name'] = employee.name if employee else None
    return schedule_dict


@router.post("/", response_model=ScheduleOut)
def create_schedule(payload: ScheduleCreate, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('schedules.create'))):
    """Tạo lịch làm việc mới"""
    # Kiểm tra nhân viên có tồn tại không
    employee = db.query(User).filter(User.id == payload.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")
    
    # Tạo lịch làm việc
    schedule = Schedule(
        employee_id=payload.employee_id,
        work_date=payload.work_date,
        shift_type=payload.shift_type,
        notes=payload.notes
    )
    db.add(schedule)
    db.flush()
    
    username = get_username_from_request(request)
    try:
        description_text = f"Tạo lịch làm việc: {employee.name or employee.username} - Ngày {payload.work_date} - {payload.shift_type}"
        create_general_diary_entry(
            db=db,
            source="Schedule",
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        log_error("CREATE_SCHEDULE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()
    
    db.refresh(schedule)
    
    schedule_dict = {
        "id": schedule.id,
        "employee_id": schedule.employee_id,
        "work_date": schedule.work_date,
        "shift_type": schedule.shift_type,
        "notes": schedule.notes,
        "employee_name": employee.name if employee else None
    }
    return ScheduleOut(**schedule_dict)


@router.put("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: int, payload: ScheduleUpdate, request: Request, db: Session = Depends(get_db)):
    """Cập nhật lịch làm việc"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch làm việc")
    
    employee = db.query(User).filter(User.id == schedule.employee_id).first()
    employee_name = employee.name if employee else "N/A"
    
    # Cập nhật các trường
    if payload.employee_id is not None:
        new_employee = db.query(User).filter(User.id == payload.employee_id).first()
        if not new_employee:
            raise HTTPException(status_code=404, detail="Không tìm thấy nhân viên")
        schedule.employee_id = payload.employee_id
        employee = new_employee
        employee_name = employee.name if employee else "N/A"
    
    if payload.work_date is not None:
        schedule.work_date = payload.work_date
    
    if payload.shift_type is not None:
        schedule.shift_type = payload.shift_type
    
    if payload.notes is not None:
        schedule.notes = payload.notes
    
    db.flush()
    
    username = get_username_from_request(request)
    try:
        description_text = f"Sửa lịch làm việc: {employee_name} - Ngày {schedule.work_date} - {schedule.shift_type}"
        create_general_diary_entry(
            db=db,
            source="Schedule",
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        log_error("UPDATE_SCHEDULE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()
    
    db.refresh(schedule)
    
    schedule_dict = {
        "id": schedule.id,
        "employee_id": schedule.employee_id,
        "work_date": schedule.work_date,
        "shift_type": schedule.shift_type,
        "notes": schedule.notes,
        "employee_name": employee.name if employee else None
    }
    return ScheduleOut(**schedule_dict)


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, request: Request, db: Session = Depends(get_db),
    _: User = Depends(require_permission('schedules.delete'))):
    """Xóa lịch làm việc"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch làm việc")
    
    employee = db.query(User).filter(User.id == schedule.employee_id).first()
    employee_name = employee.name if employee else "N/A"
    schedule_info = f"{employee_name} - Ngày {schedule.work_date} - {schedule.shift_type}"
    
    db.delete(schedule)
    db.flush()
    
    username = get_username_from_request(request)
    try:
        description_text = f"Xóa lịch làm việc: {schedule_info}"
        create_general_diary_entry(
            db=db,
            source="Schedule",
            description=description_text[:255],
            username=username
        )
        db.commit()
    except Exception as diary_error:
        log_error("DELETE_SCHEDULE_DIARY", f"Lỗi khi ghi vào General Diary: {str(diary_error)}", error=diary_error)
        db.commit()
    
    return {"success": True, "message": "Xóa lịch làm việc thành công"}