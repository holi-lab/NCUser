# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from apis.apis import attraction_retrieve, accomodation_retrieve, accomodation_book, accomodation_book_cancel, restaurant_retrieve, restaurant_book  # 함수들 import
from apis.apis import train_retrieve,train_book,taxi_book

app = FastAPI()

## Attraction
class AttractionInput(BaseModel):
    area: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    class Config:
        extra = "forbid"

@app.post("/attraction/retrieve")
def retrieve_attraction(data: AttractionInput):
    return attraction_retrieve(data.area, data.name, data.type)

## Accomodation
class AccomodationRetrieveInput(BaseModel):
    area: Optional[str] = None
    internet: Optional[bool] = None
    name: Optional[str] = None
    parking: Optional[bool] = None
    pricerange: Optional[str] = None
    stars: Optional[int] = None
    type: Optional[str] = None
    class Config:
        extra = "forbid"

@app.post("/accomodation/retrieve")
def retrieve_accomodation(data: AccomodationRetrieveInput):
    return accomodation_retrieve(**data.dict())

class AccomodationBookInput(BaseModel):
    id: int
    day: str
    people: int
    stay: int
    class Config:
        extra = "forbid"

@app.post("/accomodation/book")
def book_accomodation(data: AccomodationBookInput):
    return accomodation_book(**data.dict())

class AccomodationCancelInput(BaseModel):
    reservation_id: int
    class Config:
        extra = "forbid"

@app.post("/accomodation/book/cancel")
def cancel_booking(data: AccomodationCancelInput):
    return accomodation_book_cancel(data.reservation_id)


### Restaurant, restaurant
class RestaurantRetrieveInput(BaseModel):
    area: Optional[str] = None
    name: Optional[str] = None
    pricerange: Optional[str] = None
    food: Optional[str] = None
    class Config:
        extra = "forbid"

@app.post("/restaurant/retrieve")
def retrieve_restaurant(data: RestaurantRetrieveInput):
    return restaurant_retrieve(**data.dict())

class RestaurantBookInput(BaseModel):
    id: int
    day: str
    people: int
    time: str
    class Config:
        extra = "forbid"

@app.post("/restaurant/book")
def book_restaurant(data: RestaurantBookInput):
    return restaurant_book(**data.dict())

### Train, train
class TrainRetrieveInput(BaseModel):
    train_schedule_id: Optional[int] = None
    arriveBy: Optional[str] = None
    leaveAt: Optional[str] = None
    departure: Optional[str] = None
    destination: Optional[str] = None
    day: Optional[str] = None
    class Config:
        extra = "forbid"

@app.post("/train/retrieve")
def retrieve_train(data: TrainRetrieveInput):
    return train_retrieve(**data.dict())

class TrainBookInput(BaseModel):
    train_schedule_id: int
    people: int
    class Config:
        extra = "forbid"

@app.post("/train/book")
def book_train(data: TrainBookInput):
    return train_book(**data.dict())

## Taxi, taxi
class TaxiBookInput(BaseModel):
    leaveAt: Optional[str] = None
    arriveBy: Optional[str] = None
    destination: str
    departure: str
    class Config:
        extra = "forbid"
    
@app.post("/taxi/book")
def book_train(data: TaxiBookInput):
    return taxi_book(**data.dict())
