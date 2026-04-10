import os


class DynoConfig:
    _defaults = {
        "region": "sa-east-1",
        "endpoint_url": None,
        "aws_access_key_id": None,
        "aws_secret_access_key": None,
        "profile_name": None,
        "timestamp_format": "numeric",
        "timestamp_timezone": "America/Sao_Paulo",
        "retry_max_attempts": 3,
        "retry_mode": "adaptive",
        "auto_id_table": "dynolayer_sequences",
    }

    _env_map = {
        "region": "AWS_REGION",
        "timestamp_timezone": "TIMESTAMP_TIMEZONE",
    }

    _config = {}

    @classmethod
    def set(cls, **kwargs):
        for key in kwargs:
            if key not in cls._defaults:
                raise ValueError(f"Unknown configuration key: '{key}'")
        cls._config.update(kwargs)

    @classmethod
    def get(cls, key):
        value = cls._config.get(key)
        if value is not None:
            return value

        env_key = cls._env_map.get(key)
        if env_key:
            env_val = os.environ.get(env_key)
            if env_val is not None:
                return env_val

        return cls._defaults.get(key)

    @classmethod
    def reset(cls):
        cls._config.clear()

    @classmethod
    def all(cls):
        return {key: cls.get(key) for key in cls._defaults}