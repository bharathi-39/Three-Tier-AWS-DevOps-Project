import os
class Config:
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL','postgresql+psycopg2://bgcv:bgcv@postgres:5432/bgcv_servicehub')
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    JSON_SORT_KEYS=False
    CORS_ORIGINS=os.getenv('CORS_ORIGINS','http://localhost:3000').split(',')
