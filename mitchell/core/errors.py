class SystemMCPError(Exception):
    pass

class DeviceOffline(SystemMCPError):
    pass

class PermissionDenied(SystemMCPError):
    pass

class DeviceNotFound(SystemMCPError):
    pass

class AdbError(SystemMCPError):
    pass

class TimeoutError(SystemMCPError):
    pass

