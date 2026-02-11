"""Domain errors — pipeline exception hierarchy."""


class PipelineError(Exception):
    """Base error for all pipeline operations.

    Use ``raise PipelineError("msg") from cause`` for exception chaining.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(PipelineError):
    """Invalid configuration, missing environment variables, or bad settings."""


class ValidationError(PipelineError):
    """Schema or input validation failure."""


class AgentExecutionError(PipelineError):
    """Agent subprocess failure, timeout, or unexpected exit."""


class QAError(PipelineError):
    """QA gate failure — parse error, invalid response, or unrecoverable rejection."""


class UnknownLayoutError(PipelineError):
    """Unrecognized camera layout requiring user escalation."""
