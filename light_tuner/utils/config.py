class Config:
    MAX_WORKERS = 4
    TIMEOUT = 3600  # 秒
    BACKEND_URL = "http://localhost:8080/api"
    LOG_LEVEL = "INFO"
    CACHE_FILE = "results_cache.json"