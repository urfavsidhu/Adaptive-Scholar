import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY          = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    DATABASE_PATH       = os.getenv("DATABASE_PATH", "data/study_planner.db")
    DEBUG               = os.getenv("DEBUG", "True") == "True"
    SESSION_COOKIE_NAME = "study_planner_session"