class GijirokuError(Exception):
    pass


class ConfigurationError(GijirokuError):
    pass


class RecordingError(GijirokuError):
    pass


class TranscriptionError(GijirokuError):
    pass


class GenerationError(GijirokuError):
    pass


class UploadError(GijirokuError):
    pass


class AuthenticationError(UploadError):
    pass


class NetworkError(UploadError):
    pass


class PipelineError(GijirokuError):
    pass
