import os
import re
import subprocess


class AudioRecorder:
    def __init__(self, output_dir, mic_device, segment_duration=1800):
        self._output_dir = output_dir
        self._mic_device = mic_device
        self._segment_duration = segment_duration
        self._process = None

    @property
    def is_recording(self):
        return self._process is not None

    def _build_command(self):
        output_pattern = os.path.join(self._output_dir, "recording_%03d.wav")
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
        cmd = self._build_command()
        self._process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self):
        if self._process is None:
            return
        self._process.communicate(input=b"q")
        self._process = None

    @staticmethod
    def list_devices():
        result = subprocess.run(
            ["ffmpeg", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            capture_output=True,
            text=True,
        )
        devices = []
        for line in result.stderr.splitlines():
            match = re.search(r'"(.+?)"\s+\(audio\)', line)
            if match:
                devices.append(match.group(1))
        return devices
