from pydantic import BaseModel, field_validator
from typing import Optional ,Dict
from datetime import datetime
class ReportSubmission(BaseModel):
    user_id: str
    latitude: float
    longitude: float
    location_name: Optional[str] = None
    hazard_type: str
    severity: int
    description: str
    weather_conditions: Optional[Dict] = None
    
    @field_validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Invalid latitude')
        return v
    
    @field_validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Invalid longitude')
        return v
    
    @field_validator('hazard_type')
    def validate_hazard_type(cls, v):
        valid_types = ['tsunami', 'storm_surge', 'high_waves', 'coastal_flooding', 
                      'cyclone', 'rip_current', 'coastal_erosion', 'other']
        if v not in valid_types:
            raise ValueError(f'Hazard type must be one of {valid_types}')
        return v
    
    @field_validator('severity')
    def validate_severity(cls, v):
        if not 1 <= v <= 5:
            raise ValueError('Severity must be between 1 and 5')
        return v


class AuthorityAlertCreate(BaseModel):
    report_id: str
    authority_type: str   
    message: str
    status: str           

class AuthorityAlertResponse(AuthorityAlertCreate):
    id: str
    timestamp: datetime

    class Config:
        orm_mode = True