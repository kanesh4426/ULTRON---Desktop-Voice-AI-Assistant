import unittest

from app.tools.registry import SystemToolRegistry


class TestAppAccessToolRegistry(unittest.TestCase):
    def test_app_access_tool_is_registered(self) -> None:
        registry = SystemToolRegistry(workspace_root='.')
        tools = registry.available_tools()

        self.assertIn('app_access_tool', tools)
        actions = tools['app_access_tool']
        self.assertIn('process_command', actions)
        self.assertIn('open_application', actions)
        self.assertIn('close_application', actions)


if __name__ == '__main__':
    unittest.main()
