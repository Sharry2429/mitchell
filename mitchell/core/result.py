class MCPResult:
    def __init__(self, is_success: bool, data=None, error=None):
        self.is_success = is_success
        self.data = data
        self.error = error

    @classmethod
    def success(cls, data):
        return cls(is_success=True, data=data)

    @classmethod
    def fail(cls, error):
        return cls(is_success=False, error=error)

    @classmethod
    def error(cls, error):
        return cls(is_success=False, error=error)
        
    def __str__(self):
        if self.is_success:
            return str(self.data)
        return f"Error: {self.error}"
