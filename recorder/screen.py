import logging
import os
import shutil
import subprocess
import sys

from exceptions import RecordingError

logger = logging.getLogger(__name__)


class ScreenRecorder:
    def __init__(self, output_dir, mic_device, segment_duration=1800):
        self._output_dir = output_dir
        self._mic_device = mic_device
        self._segment_duration = segment_duration
        self._video_process = None
        self._audio_process = None

    @property
    def is_recording(self):
        if self._video_process is None:
            return False
        if self._video_process.poll() is not None:
            self._video_process = None
            return False
        return True

    def _build_video_command(self):
        video_path = os.path.join(self._output_dir, "recording.mp4")
        if sys.platform == "darwin":
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-framerate", "10",
                "-i", f"1:{self._mic_device}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-c:a", "aac",
                video_path,
            ]
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
        if sys.platform == "darwin":
            return [
                "ffmpeg", "-y",
                "-f", "avfoundation",
                "-i", f"none:{self._mic_device}",
                "-ac", "1",
                "-ar", "16000",
                "-f", "segment",
                "-segment_time", str(self._segment_duration),
                "-reset_timestamps", "1",
                audio_pattern,
            ]
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
        if not shutil.which("ffmpeg"):
            raise RecordingError(
                "FFmpegが見つかりません。インストールしてください。"
            )
        logger.info("Starting screen recording")
        try:
            self._video_process = subprocess.Popen(
                self._build_video_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise RecordingError(f"FFmpeg起動失敗: {e}") from e

        try:
            self._audio_process = subprocess.Popen(
                self._build_audio_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except Exception as e:
            logger.error("Audio process failed to start, killing video process")
            self._video_process.kill()
            self._video_process.wait()
            self._video_process = None
            raise RecordingError(f"音声プロセス起動失敗: {e}") from e

    def stop(self):
        if self._video_process is None:
            return
        import signal

        for name, proc in [("video", self._video_process), ("audio", self._audio_process)]:
            if proc is None:
                continue
            try:
                if sys.platform == "darwin":
                    proc.send_signal(signal.SIGINT)
                    proc.wait(timeout=10)
                else:
                    proc.communicate(input=b"q", timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("%s process did not stop, terminating", name)
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            except Exception as e:
                logger.error("Error stopping %s: %s", name, e)
                proc.kill()
                proc.wait()

        self._video_process = None
        self._audio_process = None
