import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    ACCESS_KEY_ID = os.environ.get("ACCESS_KEY_ID")
    SECRET_ACCESS_KEY = os.environ.get("SECRET_ACCESS_KEY")
    REGION = os.environ.get("REGION")
    S3_BUCKET = os.environ.get("S3_BUCKET")

    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT")
    PINECONE_INDEX = os.environ.get("PINECONE_INDEX")
    CLAIMS_KB_ID = "claim"
    ESTIMATES_KB_ID = "estimate"
    SYSTEM_MESSAGE_KB_ID = "system_message"

    HMW_URL = os.environ.get("HMW_URL")
    HMW_TOKEN = os.environ.get("HMW_TOKEN")
    HMW_ENVIRONMENT = os.environ.get("HMW_ENVIRONMENT")

    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = 1
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")

    BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
    ELEVENLABS_WEBHOOK_SECRET = os.environ.get("ELEVENLABS_WEBHOOK_SECRET")

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    FLASK_CONFIG = "DEV"
    TESTING = True
    DEBUG = True


class TestingConfig(Config):
    FLASK_CONFIG = "TEST"
    TESTING = True
    DEBUG = True


class StagingConfig(Config):
    FLASK_CONFIG = "STAGING"
    TESTING = False
    DEBUG = False


class ProductionConfig(Config):
    FLASK_CONFIG = "PROD"
    TESTING = False
    DEBUG = False


config = {
    "DEV": DevelopmentConfig,
    "TEST": TestingConfig,
    "STAGING": StagingConfig,
    "PROD": ProductionConfig,
    "default": DevelopmentConfig,
}
