import pytest
import asyncio
from mitchell.core.notify_gateway import set_remote_confirm_handler, confirm

@pytest.mark.asyncio
async def test_remote_confirm_handler():
    async def mock_handler(draft, context):
        return True
    
    set_remote_confirm_handler(mock_handler)
    try:
        result = await confirm("test draft", {"action": "test"})
        assert result is True
    finally:
        set_remote_confirm_handler(None)
