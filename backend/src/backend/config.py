from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ZeroMQ addresses
    zmq_status_addr: str = "tcp://localhost:5555"
    zmq_command_addr: str = "tcp://localhost:5556"
    zmq_goto_addr: str = "tcp://localhost:5557"
    zmq_servo_addr: str = "tcp://localhost:5558"
    zmq_arducam_addr: str = "tcp://localhost:6000"
    zmq_d435if_addr: str = "tcp://localhost:6001"
    zmq_d405_addr: str = "tcp://localhost:6002"

    # Camera config
    arducam_compressed: bool = False
    d435if_compressed: bool = False
    d405_compressed: bool = False

    # Arducam resolution (for numpy reshape)
    arducam_width: int = 1280
    arducam_height: int = 720

    # D435i and D405 resolution
    realsense_width: int = 640
    realsense_height: int = 480

    # Recording
    recordings_dir: str = "./recordings"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
