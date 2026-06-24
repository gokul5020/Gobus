from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, List, Annotated
from datetime import datetime

# Custom validator to handle MongoDB ObjectId as strings
PyObjectId = Annotated[str, BeforeValidator(str)]

# DB Models (for type hinting and serialization)
class BusStopDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    lat: float
    lng: float
    address: Optional[str] = ""
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class BusRouteDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    routeNumber: str
    busName: str
    stops: List[PyObjectId] = []
    description: Optional[str] = ""
    isActive: bool = True
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

class PassengerDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    mobile: str
    otpCode: Optional[str] = None
    otpExpiry: Optional[datetime] = None
    isVerified: bool = False
    name: Optional[str] = ""
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True

class RequestDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    passenger: PyObjectId
    route: PyObjectId
    stop: PyObjectId
    status: str = "pending"  # pending, sent, completed
    sentAt: Optional[datetime] = None
    notes: Optional[str] = ""
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True

class AdminDB(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    username: str
    password: str
    role: str = "depot"  # admin, depot
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True

# Request Body validation schemas
class PassengerLoginRequest(BaseModel):
    mobile: str

class VerifyOtpRequest(BaseModel):
    mobile: str
    otp: str

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class BusRequestCreate(BaseModel):
    routeId: str
    stopId: str

class DispatchBusRequest(BaseModel):
    stopId: str
    routeId: str
