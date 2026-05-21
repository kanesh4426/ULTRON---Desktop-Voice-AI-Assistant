import os
import shutil
import unittest
from pathlib import Path
from local_file_access.manager import FileManager, FileManagerConfig
from local_file_access.tools import FileToolExecutor
from local_file_access.router import AIFileCommandRouter

class TestLocalStorageManipulator(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_workspace").resolve()
        self.test_dir.mkdir(exist_ok=True)
        self.config = FileManagerConfig(
            workspace_root=str(self.test_dir),
            require_delete_confirmation=False
        )
        self.manager = FileManager(self.config)
        self.executor = FileToolExecutor(self.manager)
        self.router = AIFileCommandRouter(self.executor)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_file_basic_operations(self):
        # Create
        res = self.manager.create_file("hello.txt", "Hello World")
        self.assertTrue(res["success"])
        self.assertTrue((self.test_dir / "hello.txt").exists())

        # Read
        res = self.manager.read_file("hello.txt")
        self.assertTrue(res["success"])
        self.assertEqual(res["content"], "Hello World")

        # Write (Overwrite)
        res = self.manager.write_file("hello.txt", "New Content")
        self.assertTrue(res["success"])
        res = self.manager.read_file("hello.txt")
        self.assertEqual(res["content"], "New Content")

        # Append
        res = self.manager.append_file("hello.txt", "\\nAppended")
        self.assertTrue(res["success"])
        res = self.manager.read_file("hello.txt")
        self.assertEqual(res["content"], "New Content\\nAppended")

    def test_folder_operations(self):
        # Create Folder
        res = self.manager.create_folder("my_folder")
        self.assertTrue(res["success"])
        self.assertTrue((self.test_dir / "my_folder").is_dir())

        # List Directory
        self.manager.create_file("my_folder/inner.txt", "Inner")
        res = self.manager.list_directory("my_folder")
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["items"][0]["name"], "inner.txt")

    def test_search_features(self):
        self.manager.create_file("search_me.txt", "Found this keyword")
        self.manager.create_file("ignore.me", "Nothing here")
        
        # Search Files (filename)
        res = self.manager.search_files("search")
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["matches"][0]["name"], "search_me.txt")

        # Search Content (New Feature)
        res = self.manager.search_content("keyword")
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["matches"][0]["name"], "search_me.txt")
        self.assertIn("keyword", res["matches"][0]["content"])

    def test_rename_path(self):
        # Rename File
        self.manager.create_file("old_file.txt", "content")
        res = self.manager.rename_path("old_file.txt", "new_file.txt")
        self.assertTrue(res["success"])
        self.assertTrue((self.test_dir / "new_file.txt").exists())
        self.assertFalse((self.test_dir / "old_file.txt").exists())

        # Rename Folder
        self.manager.create_folder("old_folder")
        res = self.manager.rename_path("old_folder", "new_folder")
        self.assertTrue(res["success"])
        self.assertTrue((self.test_dir / "new_folder").is_dir())
        self.assertFalse((self.test_dir / "old_folder").exists())

    def test_move_copy(self):
        self.manager.create_file("source.txt", "move me")
        self.manager.create_folder("dest_dir")
        
        # Move
        res = self.manager.move_file("source.txt", "dest_dir/moved.txt")
        self.assertTrue(res["success"])
        self.assertTrue((self.test_dir / "dest_dir/moved.txt").exists())
        self.assertFalse((self.test_dir / "source.txt").exists())

        # Copy
        res = self.manager.copy_file("dest_dir/moved.txt", "copied.txt")
        self.assertTrue(res["success"])
        self.assertTrue((self.test_dir / "copied.txt").exists())
        self.assertTrue((self.test_dir / "dest_dir/moved.txt").exists())

    def test_metadata(self):
        self.manager.create_file("meta.txt", "some data")
        res = self.manager.get_file_metadata("meta.txt")
        self.assertTrue(res["success"])
        self.assertEqual(res["metadata"]["name"], "meta.txt")
        self.assertEqual(res["metadata"]["size"], 9)
        self.assertTrue(res["metadata"]["is_file"])

    def test_security(self):
        # Attempt to access outside workspace
        res = self.manager.read_file("../../some_external_file.txt")
        self.assertFalse(res["success"])
        self.assertIn("outside workspace", res["error"])

    def test_router(self):
        # Test routing for new features
        res = self.router.route("search content keyword")
        self.assertTrue(res["success"])
        
        res = self.router.route("rename folder old to new")
        # Since 'old' doesn't exist, it should fail but indicate routing worked
        self.assertFalse(res["success"])
        self.assertIn("does not exist", res["error"].lower())

    def test_delete_operations(self):
        # Delete File
        self.manager.create_file("delete_me.txt", "content")
        res = self.manager.delete_file("delete_me.txt", confirm=True)
        self.assertTrue(res["success"])
        self.assertFalse((self.test_dir / "delete_me.txt").exists())

        # Delete Folder (empty)
        self.manager.create_folder("empty_folder")
        res = self.manager.delete_folder("empty_folder", confirm=True)
        self.assertTrue(res["success"])
        self.assertFalse((self.test_dir / "empty_folder").exists())

        # Delete Folder (recursive)
        self.manager.create_folder("full_folder")
        self.manager.create_file("full_folder/nested.txt", "nested content")
        res = self.manager.delete_folder("full_folder", recursive=True, confirm=True)
        self.assertTrue(res["success"])
        self.assertFalse((self.test_dir / "full_folder").exists())

        # Test delete confirmation
        self.config.require_delete_confirmation = True
        self.manager.create_file("no_confirm.txt", "content")
        res = self.manager.delete_file("no_confirm.txt", confirm=False)
        self.assertFalse(res["success"])
        self.assertIn("requires confirmation", res["error"])
        self.config.require_delete_confirmation = False # Reset for other tests

    def test_utility_functions(self):
        self.manager.create_file("utility.txt", "utility content")
        self.manager.create_folder("utility_folder")

        # file_exists
        res = self.manager.file_exists("utility.txt")
        self.assertTrue(res["success"])
        self.assertTrue(res["exists"])
        res = self.manager.file_exists("non_existent.txt")
        self.assertTrue(res["success"])
        self.assertFalse(res["exists"])

        # is_file
        res = self.manager.is_file("utility.txt")
        self.assertTrue(res["success"])
        self.assertTrue(res["is_file"])
        res = self.manager.is_file("utility_folder")
        self.assertTrue(res["success"])
        self.assertFalse(res["is_file"])

        # is_dir
        res = self.manager.is_dir("utility_folder")
        self.assertTrue(res["success"])
        self.assertTrue(res["is_dir"])
        res = self.manager.is_dir("utility.txt")
        self.assertTrue(res["success"])
        self.assertFalse(res["is_dir"])
        
        # get_file_size
        res = self.manager.get_file_size("utility.txt")
        self.assertTrue(res["success"])
        self.assertEqual(res["size"], len("utility content"))

    def test_history_and_importance(self):
        # Perform some operations to build history
        self.manager.create_file("history_file_1.txt", "content A")
        self.manager.read_file("history_file_1.txt")
        self.manager.write_file("history_file_2.py", "print('hello')")

        # Get Operation History
        res = self.manager.get_operation_history()
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["count"], 3) # At least 3 operations above
        # Check if the last operation is correct (ordering can vary slightly depending on exact timing)
        self.assertIn("history_file_2.py", res["history"][-1]["path"])
        
        # Analyze File Importance
        res = self.manager.analyze_file_importance("history_file_2.py")
        self.assertTrue(res["success"])
        self.assertIn("importance_score", res)
        self.assertIn("importance_level", res)
        # Python files should have higher critical score
        self.assertTrue(res["breakdown"]["critical_extension"])

    def test_edge_cases(self):
        # Read non-existent file
        res = self.manager.read_file("non_existent.txt")
        self.assertFalse(res["success"])
        self.assertIn("does not exist", res["error"].lower())

        # Write to non-existent directory (should create it)
        res = self.manager.write_file("new_folder/new_file.txt", "content")
        self.assertTrue(res["success"])
        self.assertTrue((self.test_dir / "new_folder/new_file.txt").exists())

        # List directory with recursive and hidden
        self.manager.create_folder("hidden_test")
        (self.test_dir / "hidden_test" / ".hidden_file.txt").write_text("hidden")
        self.manager.create_file("hidden_test/visible.txt", "visible")
        
        res = self.manager.list_directory("hidden_test", recursive=True, show_hidden=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 2) # .hidden_file.txt and visible.txt

        res = self.manager.list_directory("hidden_test", recursive=True, show_hidden=False)
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 1) # Only visible.txt

        # Search files/content with no matches
        res = self.manager.search_files("no_match_file.txt")
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 0)

        res = self.manager.search_content("no_match_content")
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 0)

if __name__ == "__main__":
    unittest.main()
