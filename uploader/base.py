from abc import ABC, abstractmethod

class BaseUploader(ABC):
    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def upload_file(self, file_path, parent_folder_id):
        pass

    @abstractmethod
    def create_folder(self, name, parent_folder_id=None):
        pass

    @abstractmethod
    def upload_session(self, session_dir, meeting_name):
        pass
