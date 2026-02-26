from mongoengine import Document, StringField, EmailField, DateTimeField, FloatField, IntField, ReferenceField, BooleanField, ListField, EmbeddedDocumentField, EmbeddedDocument

import datetime
from mongoengine import Document, StringField
from pydantic import BaseModel

import uuid

class MarketGod(Document):
    name = StringField(required=True, unique=True)
    hindi = StringField()

    open_time = StringField(required=True)
    close_time = StringField(required=True)
    marketType = StringField(required=True)  # Regular / Starline / Jackpot
    
    is_active = BooleanField(default=True)
    status = BooleanField(default=True) 

class BidGod(Document):
    user_id = StringField(required=True)
    market_id = StringField(required=True)

    game_type = StringField(required=True )  # single, jodi, sp, dp, tp, panna, sangam
    session = StringField(required=True) 
    
    open_digit = StringField(required=True)
    close_digit = StringField(required=True)
    points = IntField(required=True)

    created_at = DateTimeField(default=datetime.datetime.utcnow)

class ResultGod(Document):
    market_id = StringField(required=True)
    date = DateTimeField(required=True, default=datetime.datetime.utcnow)
    open_digit = StringField()
    close_digit = StringField()

class RateChartGod(Document):
    meta = {"collection": "rate_chart"}

    # Values for Type 1
    single_digit_1 = IntField(default=10)
    jodi_digit_1 = IntField(default=10)
    single_pana_1 = IntField(default=10)
    double_pana_1 = IntField(default=10)
    tripple_pana_1 = IntField(default=10)
    half_sangam_1 = IntField(default=10)
    full_sangam_1 = IntField(default=10)
    left_digit_1 = IntField(default=10)
    right_digit_1 = IntField(default=10)
    starline_single_digit_1 = IntField(default=10)
    starline_single_pana_1 = IntField(default=10)
    starline_double_pana_1 = IntField(default=10)
    starline_tripple_pana_1 = IntField(default=10)

    # Values for Type 2
    single_digit_2 = IntField(default=100)
    jodi_digit_2 = IntField(default=995)
    single_pana_2 = IntField(default=1500)
    double_pana_2 = IntField(default=3000)
    tripple_pana_2 = IntField(default=7000)
    half_sangam_2 = IntField(default=10000)
    full_sangam_2 = IntField(default=100000)
    left_digit_2 = IntField(default=100)
    right_digit_2 = IntField(default=100)
    starline_single_digit_2 = IntField(default=100)
    starline_single_pana_2 = IntField(default=1500)
    starline_double_pana_2 = IntField(default=3000)
    starline_tripple_pana_2 = IntField(default=7000)