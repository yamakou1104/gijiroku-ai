import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from config import Config
from recorder.audio import AudioRecorder
from recorder.screen import ScreenRecorder
from transcriber.gemini import GeminiTranscriber
from generator.minutes import MinutesGenerator
from uploader.google_drive import GoogleDriveUploader
from uploader.onedrive import OneDriveUploader
from utils.file_manager import FileManager
from pipeline import Pipeline

logger = logging.getLogger(__name__)


def _setup_logging():
    log_dir = os.path.expanduser("~/.gijiroku-ai")
    os.makedirs(log_dir, exist_ok=True)
    handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )


def _build_components(config):
    output_base = config.get("output_dir")
    if not output_base:
        output_base = os.path.join(os.path.expanduser("~"), "gijiroku-ai-data")
        config.set("output_dir", output_base)
    os.makedirs(output_base, exist_ok=True)

    fm = FileManager(output_base)

    api_key = config.get("gemini_api_key")
    transcriber = GeminiTranscriber(api_key=api_key) if api_key else None
    generator = MinutesGenerator(api_key=api_key) if api_key else None

    def recorder_factory(mode):
        mic = config.get("mic_device")
        segment_duration = config.get("segment_duration")
        session_dir = fm.create_session("会議")
        if mode == "face_to_face":
            recorder = AudioRecorder(
                output_dir=session_dir,
                mic_device=mic,
                segment_duration=segment_duration,
            )
        else:
            recorder = ScreenRecorder(
                output_dir=session_dir,
                mic_device=mic,
                segment_duration=segment_duration,
            )
        return recorder, session_dir

    def uploader_factory():
        from utils.resource_path import get_credentials_dir

        provider = config.get("storage_provider")
        if provider == "google_drive":
            creds_path = config.get("google_drive_credentials")
            if not creds_path:
                creds_path = os.path.join(
                    get_credentials_dir(), "google_client_secrets.json"
                )
            uploader = GoogleDriveUploader(credentials_path=creds_path)
        else:
            client_id = config.get("onedrive_credentials")
            if not client_id:
                import json

                od_config_path = os.path.join(
                    get_credentials_dir(), "onedrive_config.json"
                )
                with open(od_config_path) as f:
                    client_id = json.load(f)["client_id"]
            uploader = OneDriveUploader(client_id=client_id)
        uploader.authenticate()
        return uploader

    pipeline = Pipeline(
        config=config,
        transcriber=transcriber,
        generator=generator,
        uploader_factory=uploader_factory,
    )

    return recorder_factory, pipeline


def _launch_tray(config):
    from tray.app import TrayApp

    recorder_factory, pipeline = _build_components(config)
    app = TrayApp(
        config=config,
        recorder_factory=recorder_factory,
        pipeline=pipeline,
    )
    app.run()


def _launch_gui(config):
    from ui.app import App

    recorder_factory, pipeline = _build_components(config)
    app = App(
        config=config,
        recorder_factory=recorder_factory,
        pipeline=pipeline,
    )
    app.run()


def main():
    _setup_logging()
    logger.info("議事録AI starting")

    config = Config()
    use_gui = "--gui" in sys.argv

    if not config.get("setup_complete"):
        from ui.setup import SetupWizard

        if use_gui:
            wizard = SetupWizard(config, on_complete=lambda: _launch_gui(config))
        else:
            wizard = SetupWizard(config, on_complete=lambda: _launch_tray(config))
        wizard.run()
    else:
        if use_gui:
            _launch_gui(config)
        else:
            _launch_tray(config)


if __name__ == "__main__":
    main()
