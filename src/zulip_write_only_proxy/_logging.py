import logging


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Exclude health check requests from the logs
        return record.getMessage().find("/health") == -1
