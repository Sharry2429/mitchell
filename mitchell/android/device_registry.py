import logging
import subprocess
import time

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

logger = logging.getLogger(__name__)


class AdbServiceListener(ServiceListener):
    def __init__(self):
        self.devices: dict[str, str] = {}  # mapping of service name to address

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.info(f"Service {name} removed")
        if name in self.devices:
            del self.devices[name]

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            # Get the first IPv4 address
            address = ".".join(map(str, info.addresses[0]))
            port = info.port
            target = f"{address}:{port}"
            logger.info(f"Found ADB service {name} at {target}")
            self.devices[name] = target
            self.connect_to_device(target)

    def connect_to_device(self, target: str):
        try:
            logger.info(f"Connecting to {target}...")
            result = subprocess.run(
                ["adb", "connect", target], capture_output=True, text=True, check=True
            )
            logger.info(f"Connection result: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to connect to {target}: {e.stderr}")


def start_registry():
    logging.basicConfig(level=logging.INFO)
    zeroconf = Zeroconf()
    listener = AdbServiceListener()
    # ADB over TLS mDNS service type
    SERVICE_TYPE = "_adb-tls-connect._tcp.local."

    ServiceBrowser(zeroconf, SERVICE_TYPE, listener)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping registry...")
    finally:
        zeroconf.close()


if __name__ == "__main__":
    start_registry()
