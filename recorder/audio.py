import atexit
import logging
import os
import re
import shutil
import subprocess
import sys

from exceptions import RecordingError

logger = logging.getLogger(__name__)


class AudioRecorder:
    def __init__(self, output_dir, mic_device, segment_duration=1800):
        self._output_dir = output_dir
        self._mic_device = mic_device
        self._segment_duration = segment_duration
        self._process = None

    @property
    def is_recording(self):
        if self._process is None:
            return False
        if self._process.poll() is not None:
            self._process = None
            return False
        return True

    def _build_command(self):
        output_pattern = os.path.join(self._output_dir, "recording_%03d.wav")
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
                output_pattern,
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
            output_pattern,
        ]

    def start(self):
        if self._process is not None:
            return
        if not shutil.which("ffmpeg"):
            raise RecordingError(
                "FFmpegが見つかりません。インストールしてください。"
            )
        cmd = self._build_command()
        logger.info("Starting audio recording: %s", " ".join(cmd))
        try:
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise RecordingError(f"FFmpeg起動失敗: {e}") from e
        atexit.register(self._cleanup)

    def _cleanup(self):
        if self._process and self._process.poll() is None:
            logger.warning("Cleaning up FFmpeg process on exit")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except Exception:
                self._process.kill()

    def stop(self):
        if self._process is None:
            return
        import signal

        try:
            if sys.platform == "darwin":
                self._process.send_signal(signal.SIGINT)
                self._process.wait(timeout=10)
            else:
                self._process.communicate(input=b"q", timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg did not stop gracefully, terminating")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("FFmpeg did not terminate, killing")
                self._process.kill()
                self._process.wait()
        except Exception as e:
            logger.error("Error stopping recorder: %s", e)
            self._process.kill()
            self._process.wait()
        finally:
            if self._process and self._process.returncode is not None:
                logger.info("FFmpeg exited with code %d", self._process.returncode)
            try:
                atexit.unregister(self._cleanup)
            except Exception:
                pass
            self._process = None

    @staticmethod
    def list_devices():
        if not shutil.which("ffmpeg"):
            return []
        try:
            if sys.platform == "darwin":
                result = subprocess.run(
                    ["ffmpeg", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                devices = []
                in_audio_section = False
                for line in result.stderr.splitlines():
                    if "audio devices" in line.lower():
                        in_audio_section = True
                        continue
                    if "video devices" in line.lower():
                        in_audio_section = False
                        continue
                    if in_audio_section:
                        match = re.search(r"\[(\d+)\]\s+(.+)$", line)
                        if match:
                            devices.append((match.group(1), match.group(2).strip()))
                return devices
            else:
                result = subprocess.run(
                    ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                devices = []
                for line in result.stderr.splitlines():
                    match = re.search(r'"(.+?)"\s+\(audio\)', line)
                    if match:
                        devices.append(match.group(1))
                return devices
        except Exception as e:
            logger.error("Failed to list audio devices: %s", e)
            return []
