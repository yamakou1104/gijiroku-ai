import os
import subprocess


class ScreenRecorder:
    def __init__(self, output_dir, mic_device, segment_duration=1800):
        self._output_dir = output_dir
        self._mic_device = mic_device
        self._segment_duration = segment_duration
        self._video_process = None
        self._audio_process = None

    @property
    def is_recording(self):
        return self._video_process is not None

    def _build_video_command(self):
        video_path = os.path.join(self._output_dir, "recording.mp4")
        return [
            "ffmpeg", "-y",
            "-f", "gdigrab",
            "-framerate", "10",
            "-i", "desktop",
            "-f", "dshow",
            "-i", f"audio={self._mic_device}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-c:a", "aac",
            video_path,
        ]

    def _build_audio_command(self):
        audio_pattern = os.path.join(self._output_dir, "recording_%03d.wav")
        return [
            "ffmpeg", "-y",
            "-f", "dshow",
            "-i", f"audio={self._mic_device}",
            "-ac", "1",
            "-ar", "16000",
            "-f", "segment",
            "-segment_time", str(self._segment_duration),
            "-reset_timestamps", "1",
            audio_pattern,
        ]

    def start(self):
        if self._video_process is not None:
            return
        self._video_process = subprocess.Popen(
            self._build_video_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._audio_process = subprocess.Popen(
            self._build_audio_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self):
        if self._video_process is None:
            return
        self._video_process.communicate(input=b"q")
        self._audio_process.communicate(input=b"q")
        self._video_process = None
        self._audio_process = None
