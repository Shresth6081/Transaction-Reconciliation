import os
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    RAW_DATA_DIR: Path = PROJECT_ROOT / "data" / "raw"
    OUTPUT_DATA_DIR: Path = PROJECT_ROOT / "data" / "output"
    
    DATE_TOLERANCE_DAYS: int = 3
    AMOUNT_TOLERANCE: float = 0.00
    
    DB_TYPE: str = "sqlite"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB: str = "reconciliation_db"
    SQLITE_PATH: Path = PROJECT_ROOT / "data" / "reconciliation_audit.db"
    
    CHUNK_SIZE: int = 50000
    LOG_LEVEL: str = "INFO"

    @property
    def database_url(self) -> str:
        if self.DB_TYPE.lower() == "mysql":
            return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
        return f"sqlite:///{self.SQLITE_PATH}"

settings = Settings()

settings.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
