# main.py
import os
import sys
from config import Config
from ui.app import App
from recorder.audio import AudioRecorder
from recorder.screen import ScreenRecorder
from transcriber.gemini import GeminiTranscriber
from generator.minutes import MinutesGenerator
from uploader.google_drive import GoogleDriveUploader
from uploader.onedrive import OneDriveUploader
from utils.file_manager import FileManager

def create_app_with_config(config):
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
        provider = config.get("storage_provider")
        if provider == "google_drive":
            creds_path = config.get("google_drive_credentials")
            uploader = GoogleDriveUploader(credentials_path=creds_path)
        else:
            client_id = config.get("onedrive_credentials")
            uploader = OneDriveUploader(client_id=client_id)
        uploader.authenticate()
        return uploader

    app = App(
        config=config,
        recorder_factory=recorder_factory,
        uploader_factory=uploader_factory,
        transcriber=transcriber,
        generator=generator,
    )
    return app

def create_app():
    config = Config()
    return create_app_with_config(config)

def _launch_app(config):
    app = create_app_with_config(config)
    app.run()

def main():
    config = Config()

    if not config.get("setup_complete"):
        from ui.setup import SetupWizard
        wizard = SetupWizard(config, on_complete=lambda: _launch_app(config))
        wizard.run()
    else:
        _launch_app(config)

if __name__ == "__main__":
    main()
