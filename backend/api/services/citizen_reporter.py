from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import os
import aiofiles
from geopy.distance import geodesic
import uuid
import json
import logging

# Adjust this import to match your project layout
from backend.api.models.database import HazardReport, AuthorityAlerts, IST, SessionLocal
from backend.api.models.schemas import ReportSubmission, AuthorityAlertCreate, AuthorityAlertResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class HazardReportManager:
    def __init__(self):
        self.media_storage_path = os.path.join(os.getcwd(), "uploads", "hazard_media")
        os.makedirs(self.media_storage_path, exist_ok=True)

        self.hazard_weights = {
            'tsunami': 5.0,
            'storm_surge': 4.5,
            'cyclone': 4.5,
            'coastal_flooding': 3.5,
            'high_waves': 3.0,
            'rip_current': 3.0,
            'coastal_erosion': 2.0,
            'other': 1.0
        }

    def calculate_priority_score(self, report: ReportSubmission, nearby_reports: List) -> float:
        base_score = self.hazard_weights.get(report.hazard_type, 1.0)
        severity_multiplier = (report.severity or 1) / 5.0
        cluster_bonus = min(len(nearby_reports) * 0.2, 2.0)  # Max 2x bonus for clustering
        time_factor = 1.0
        priority_score = base_score * severity_multiplier * (1 + cluster_bonus) * time_factor
        return round(priority_score, 2)

    def find_nearby_reports(self, db: Session, lat: float, lon: float, radius_km: float = 5.0) -> List:
        cutoff = datetime.now(IST) - timedelta(hours=24)
        all_reports = db.query(HazardReport).filter(HazardReport.timestamp >= cutoff).all()

        nearby = []
        current_location = (lat, lon)
        for report in all_reports:
            try:
                report_location = (report.latitude, report.longitude)
                distance = geodesic(current_location, report_location).kilometers
            except Exception as e:
                logger.debug("geodesic calc failed for report %s: %s", getattr(report, "id", None), e)
                continue

            if distance <= radius_km:
                nearby.append({
                    'id': report.id,
                    'distance_km': round(distance, 2),
                    'hazard_type': report.hazard_type,
                    'severity': report.severity
                })

        return nearby

    async def save_media_bytes(self, content: bytes, orig_filename: str) -> str:
        file_extension = orig_filename.split('.')[-1] if '.' in orig_filename else ''
        unique_filename = f"{uuid.uuid4()}.{file_extension}" if file_extension else str(uuid.uuid4())
        file_path = os.path.join(self.media_storage_path, unique_filename)

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # Return relative URL path – make sure to mount StaticFiles("/media/hazard")
        return f"/media/hazard/{unique_filename}"

    def validate_report_location(self, lat: float, lon: float) -> bool:
        # Slightly widened coastal bounds to include southern tip
        indian_coastal_bounds = {
            'min_lat': 6.5,   # southern tip approx
            'max_lat': 24.5,  # includes northern coastal margin
            'min_lon': 68.0,  # west
            'max_lon': 97.5   # east
        }
        return (indian_coastal_bounds['min_lat'] <= lat <= indian_coastal_bounds['max_lat'] and
                indian_coastal_bounds['min_lon'] <= lon <= indian_coastal_bounds['max_lon'])


report_manager = HazardReportManager()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/api/reports/submit", status_code=status.HTTP_201_CREATED)
async def submit_hazard_report(
    user_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    location_name: Optional[str] = Form(None),
    hazard_type: str = Form(...),
    severity: int = Form(...),
    description: str = Form(...),
    weather_conditions: Optional[str] = Form(None),
    media_files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    # Validate location
    if not report_manager.validate_report_location(latitude, longitude):
        raise HTTPException(status_code=400, detail="Location must be near Indian coastline")

    weather_data = None
    if weather_conditions:
        try:
            weather_data = json.loads(weather_conditions)
        except Exception:
            weather_data = None

    # Create lightweight submission object (dataclass or simple container)
    report = ReportSubmission(
        user_id=user_id,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        hazard_type=hazard_type,
        severity=severity,
        description=description,
        weather_conditions=weather_data
    )

    nearby_reports = report_manager.find_nearby_reports(db, latitude, longitude)
    priority_score = report_manager.calculate_priority_score(report, nearby_reports)

    media_urls = []
    if media_files:
        for file in media_files:
            content = await file.read()
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds 10MB limit")
            media_url = await report_manager.save_media_bytes(content, file.filename)
            media_urls.append(media_url)

    db_report = HazardReport(
        id=str(uuid.uuid4()),
        user_id=report.user_id,
        latitude=report.latitude,
        longitude=report.longitude,
        location_name=report.location_name,
        hazard_type=report.hazard_type,
        severity=report.severity,
        description=report.description,
        media_urls=media_urls,
        priority_score=priority_score,
        nearby_reports=nearby_reports,
        weather_conditions=report.weather_conditions,
        timestamp=datetime.now(IST)
    )

    try:
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
    except Exception as e:
        db.rollback()
        logger.exception("DB error while saving report")
        raise HTTPException(status_code=500, detail="Internal server error saving report")

    return {
        "status": "success",
        "report_id": db_report.id,
        "priority_score": priority_score,
        "nearby_reports_count": len(nearby_reports),
        "message": "Report submitted successfully. Authorities have been notified."
    }


@router.get("/api/reports/hotspots")
async def get_hazard_hotspots_endpoint(
    time_range: int = 24,  # hours
    min_reports: int = 3,
    db: Session = Depends(get_db)
):
    # Reuse manager logic to create clusters (same implementation you had)
    cutoff_time = datetime.now(IST) - timedelta(hours=time_range)
    recent_reports = db.query(HazardReport).filter(HazardReport.timestamp >= cutoff_time).all()

    grid_size = 0.1  # ~11km grid cells
    clusters = {}

    for report in recent_reports:
        grid_key = (
            round(report.latitude / grid_size) * grid_size,
            round(report.longitude / grid_size) * grid_size
        )

        if grid_key not in clusters:
            clusters[grid_key] = {
                'center_lat': grid_key[0],
                'center_lon': grid_key[1],
                'reports': [],
                'total_severity': 0,
                'hazard_types': set()
            }

        clusters[grid_key]['reports'].append(report.id)
        clusters[grid_key]['total_severity'] += getattr(report, 'severity', 0)
        clusters[grid_key]['hazard_types'].add(getattr(report, 'hazard_type', 'unknown'))

    hotspots = []
    for grid_key, cluster in clusters.items():
        if len(cluster['reports']) >= min_reports:
            avg_severity = cluster['total_severity'] / len(cluster['reports']) if cluster['reports'] else 0
            hotspots.append({
                'latitude': cluster['center_lat'],
                'longitude': cluster['center_lon'],
                'report_count': len(cluster['reports']),
                'average_severity': round(avg_severity, 2),
                'hazard_types': list(cluster['hazard_types']),
                'threat_level': 'high' if avg_severity >= 3.5 else 'medium'
            })

    hotspots.sort(key=lambda x: x['report_count'] * x['average_severity'], reverse=True)

    return {"hotspots": hotspots, "total_reports": len(recent_reports), "time_range_hours": time_range}


@router.get("/api/weather")
async def get_weather_data(lat: float, lon: float):
    """Get current weather data for a location (mock)"""
    try:
        return {
            "temperature": 28,
            "wind_speed": 15,
            "wind_direction": "NE",
            "humidity": 75,
            "pressure": 1010,
            "weather_description": "Partly Cloudy",
            "precipitation": 0,
            "wave_height": 1.5,
            "timestamp": datetime.now(IST).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/reports/{report_id}/verify")
async def verify_report(
    report_id: str,
    status: str,
    verifier_id: str,
    db: Session = Depends(get_db)
):
    if status not in ['verified', 'rejected']:
        raise HTTPException(status_code=400, detail="Status must be 'verified' or 'rejected'")

    report = db.query(HazardReport).filter(HazardReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.verification_status = status
    report.verifier_id = verifier_id
    report.verification_timestamp = datetime.now(IST)
    try:
        db.commit()
        db.refresh(report)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update verification status")

    return {
        "status": "success",
        "report_id": report_id,
        "new_status": status,
        "verified_by": verifier_id,
        "verification_timestamp": report.verification_timestamp.isoformat()
    }

@router.get("/api/reports/active")
async def get_active_reports(hours: int = 48, db: Session = Depends(get_db)):
    cutoff = datetime.now(IST) - timedelta(hours=hours)
    reports = db.query(HazardReport).filter(HazardReport.timestamp >= cutoff).all()

    return {
        "reports": [
            {
                "id": r.id,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "hazard_type": r.hazard_type,
                "severity": r.severity,
                "description": r.description,
                "location_name": r.location_name,
                "timestamp": r.timestamp.isoformat(),
                "verification_status": r.verification_status,
                "priority_score": r.priority_score
            }
            for r in reports
        ]
    }


@router.get("/api/reports/{report_id}")
async def get_report_details(report_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific report"""
    report = db.query(HazardReport).filter(HazardReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return {
        "id": report.id,
        "user_id": report.user_id,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "location_name": report.location_name,
        "hazard_type": report.hazard_type,
        "severity": report.severity,
        "description": report.description,
        "media_urls": report.media_urls or [],
        "verification_status": report.verification_status,
        "priority_score": report.priority_score,
        "nearby_reports": report.nearby_reports or [],
        "weather_conditions": report.weather_conditions,
        "timestamp": report.timestamp.isoformat() if report.timestamp else None,
        "created_at": report.timestamp.isoformat() if report.timestamp else None
    }




@router.get("/api/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    total_reports = db.query(func.count(HazardReport.id)).scalar() or 0
    active_reports = db.query(func.count(HazardReport.id)).filter(
        HazardReport.timestamp >= datetime.now(IST) - timedelta(hours=48)
    ).scalar() or 0
    resolved_reports = db.query(func.count(HazardReport.id)).filter(
        HazardReport.verification_status == "verified"
    ).scalar() or 0

    return {
        "total_reports": total_reports,
        "active_reports": active_reports,
        "resolved_reports": resolved_reports,
    }


@router.get("/api/dashboard/reports")
async def get_dashboard_reports(db: Session = Depends(get_db)):
    recent = db.query(HazardReport).order_by(HazardReport.timestamp.desc()).limit(50).all()
    return {"reports": [
        {
            "id": r.id,
            "hazard_type": r.hazard_type,
            "location_name": r.location_name,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "severity": r.severity,
            "timestamp": r.timestamp.isoformat(),
            "verification_status": r.verification_status,
            "created_at": r.timestamp.isoformat()
        } for r in recent
    ]}


@router.get("/api/dashboard/trends")
async def get_dashboard_trends(db: Session = Depends(get_db)):
    """Mock trending hazards data - replace with real social media analysis"""
    return {
        "trending": [
            {
                "hazard_type": "coastal_flooding",
                "trend_score": 0.85,
                "post_count": 127,
                "affected_regions": ["Chennai", "Puducherry"]
            },
            {
                "hazard_type": "cyclone",
                "trend_score": 0.72,
                "post_count": 89,
                "affected_regions": ["Odisha", "Andhra Pradesh"]
            }
        ]
    }


# FIXED: Authority Alerts endpoints with proper /api prefix
@router.post("/api/alerts", response_model=AuthorityAlertResponse)
async def create_authority_alert(alert: AuthorityAlertCreate, db: Session = Depends(get_db)):
    """Create a new authority alert for a hazard report"""
    # Verify the report exists
    report = db.query(HazardReport).filter(HazardReport.id == alert.report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    new_alert = AuthorityAlerts(
        id=str(uuid.uuid4()),
        report_id=alert.report_id,
        authority_type=alert.authority_type,
        message=alert.message,
        status=alert.status,
        timestamp=datetime.now(IST)
    )
    try:
        db.add(new_alert)
        db.commit()
        db.refresh(new_alert)
        
        logger.info(f"Authority alert created: {new_alert.id} for report {alert.report_id}")
        
        return AuthorityAlertResponse(
            id=new_alert.id,
            report_id=new_alert.report_id,
            authority_type=new_alert.authority_type,
            message=new_alert.message,
            status=new_alert.status,
            timestamp=new_alert.timestamp
        )
    except Exception as e:
        db.rollback()
        logger.exception("DB error while saving authority alert")
        raise HTTPException(status_code=500, detail="Internal server error saving authority alert")


@router.get("/api/alerts", response_model=List[AuthorityAlertResponse])
async def get_authority_alerts(
    limit: int = 50,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all authority alerts, optionally filtered by status"""
    query = db.query(AuthorityAlerts)
    
    if status_filter:
        query = query.filter(AuthorityAlerts.status == status_filter)
    
    alerts = query.order_by(AuthorityAlerts.timestamp.desc()).limit(limit).all()
    
    return [
        AuthorityAlertResponse(
            id=alert.id,
            report_id=alert.report_id,
            authority_type=alert.authority_type,
            message=alert.message,
            status=alert.status,
            timestamp=alert.timestamp
        )
        for alert in alerts
    ]


@router.get("/api/alerts/{alert_id}", response_model=AuthorityAlertResponse)
async def get_authority_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific authority alert by ID"""
    alert = db.query(AuthorityAlerts).filter(AuthorityAlerts.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Authority alert not found")
    
    return AuthorityAlertResponse(
        id=alert.id,
        report_id=alert.report_id,
        authority_type=alert.authority_type,
        message=alert.message,
        status=alert.status,
        timestamp=alert.timestamp
    )


@router.put("/alerts/{alert_id}/status")
async def update_alert_status(
    alert_id: str,
    new_status: str,
    db: Session = Depends(get_db)
):
    """Update the status of an authority alert"""
    valid_statuses = ['urgent', 'high_priority', 'standard', 'informational', 'resolved', 'cancelled']
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    alert = db.query(AuthorityAlerts).filter(AuthorityAlerts.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Authority alert not found")
    
    old_status = alert.status
    alert.status = new_status
    
    try:
        db.commit()
        db.refresh(alert)
        logger.info(f"Alert {alert_id} status updated from {old_status} to {new_status}")
        
        return {
            "status": "success",
            "alert_id": alert_id,
            "old_status": old_status,
            "new_status": new_status,
            "updated_at": datetime.now(IST).isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.exception("DB error while updating alert status")
        raise HTTPException(status_code=500, detail="Internal server error updating alert status")


# Add missing social media analysis endpoint
@router.post("/analyze/social-media")
async def analyze_social_media(posts_data: dict):
    """Mock social media analysis - replace with real implementation"""
    posts = posts_data.get('posts', [])
    
    # Mock analysis response
    return {
        "total_posts_analyzed": len(posts),
        "alerts_generated": 2,
        "high_priority_alerts": [
            {
                "alert": {
                    "hazard_type": "tsunami",
                    "confidence": 0.85,
                    "location_mentions": ["Chennai", "Marina Beach"]
                }
            },
            {
                "alert": {
                    "hazard_type": "cyclone",
                    "confidence": 0.92,
                    "location_mentions": ["Puri", "Bhubaneswar"]
                }
            }
        ]
    }