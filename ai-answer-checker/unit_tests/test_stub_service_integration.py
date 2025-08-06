"""Integration tests for StubService to verify HTTP functionality."""

import time
import unittest
import httpx
from pathlib import Path

from ai_answer_checker.services.stub_service import StubService
from ai_answer_checker.models import TestCase


class TestStubServiceIntegration(unittest.TestCase):
    """Integration tests that actually start the StubService and make HTTP requests."""

    def setUp(self):
        """Set up test environment before each test."""
        self.test_port = 9876
        self.stub_service = StubService(port=self.test_port)
        self.base_url = f"http://localhost:{self.test_port}"

    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'stub_service') and self.stub_service:
            self.stub_service.stop()

    def test_stub_service_starts_and_responds_to_health_check(self):
        """Test that StubService starts successfully and responds to health check."""
        # Start the service
        started = self.stub_service.start()
        self.assertTrue(started, "StubService should start successfully")
        
        # Give it a moment to fully start
        time.sleep(0.1)
        
        # Make a health check request
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/health")
            self.assertEqual(response.status_code, 200)
            
            response_data = response.json()
            self.assertIn("status", response_data)
            self.assertEqual(response_data["status"], "healthy")

    def test_stub_service_with_tool_stubs(self):
        """Test that StubService can serve tool stub endpoints."""
        # Create a test case with tool stubs
        test_yaml_content = """
user_input: "Test question"
expected_answer: "Test answer"
tool_stubs:
  paySlips:
    - request:
        employeeId: "123"
      response_file: "paySlips/123.json"
"""
        
        # Create temporary test file
        with open("temp_test.yaml", "w") as f:
            f.write(test_yaml_content)
        
        try:
            # Load test case
            test_case = TestCase.from_yaml_file("temp_test.yaml")
            
            # Create stubs directory structure
            stubs_dir = Path("temp_stubs")
            stubs_dir.mkdir(exist_ok=True)
            payslips_dir = stubs_dir / "paySlips"
            payslips_dir.mkdir(exist_ok=True)
            
            # Create stub response file
            stub_file = payslips_dir / "123.json"
            stub_file.write_text('{"paySlips": [{"amount": 1000, "date": "2025-03-01"}]}')
            
            # Load stubs into service
            self.stub_service.load_test_stubs(test_case, stubs_dir)
            
            # Start the service
            started = self.stub_service.start()
            self.assertTrue(started, "StubService should start successfully")
            
            # Give it a moment to fully start
            time.sleep(0.1)
            
            # Test GET request to tool endpoint
            with httpx.Client() as client:
                response = client.get(f"{self.base_url}/paySlips", params={"employeeId": "123"})
                self.assertEqual(response.status_code, 200)
                
                response_data = response.json()
                self.assertIn("paySlips", response_data)
                self.assertEqual(len(response_data["paySlips"]), 1)
                self.assertEqual(response_data["paySlips"][0]["amount"], 1000)
                
                # Test POST request to tool endpoint
                response = client.post(f"{self.base_url}/paySlips", json={"employeeId": "123"})
                self.assertEqual(response.status_code, 200)
                
                response_data = response.json()
                self.assertIn("paySlips", response_data)
                self.assertEqual(len(response_data["paySlips"]), 1)
                self.assertEqual(response_data["paySlips"][0]["amount"], 1000)
            
        finally:
            # Cleanup temporary files
            if Path("temp_test.yaml").exists():
                Path("temp_test.yaml").unlink()
            if Path("temp_stubs").exists():
                import shutil
                shutil.rmtree("temp_stubs")

    def test_stub_service_handles_missing_stub_gracefully(self):
        """Test that StubService handles requests for non-existent stubs gracefully."""
        # Start the service without any stubs
        started = self.stub_service.start()
        self.assertTrue(started, "StubService should start successfully")
        
        # Give it a moment to fully start
        time.sleep(0.1)
        
        # Test request to non-existent endpoint
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/nonexistent", params={"test": "value"})
            # Should return 404 for non-existent endpoints
            self.assertEqual(response.status_code, 404)

    def test_stub_service_can_stop_and_restart(self):
        """Test that StubService can be stopped and restarted."""
        # Start the service
        started = self.stub_service.start()
        self.assertTrue(started, "StubService should start successfully")
        
        # Give it a moment to fully start
        time.sleep(0.1)
        
        # Verify it's running with a health check
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/health")
            self.assertEqual(response.status_code, 200)
        
        # Stop the service
        self.stub_service.stop()
        
        # Give it a moment to stop
        time.sleep(0.1)
        
        # Verify it's stopped (connection should fail)
        with httpx.Client() as client:
            try:
                response = client.get(f"{self.base_url}/health", timeout=1.0)
                # If we get here, the service didn't stop properly
                self.fail("Service should be stopped and not respond")
            except httpx.ConnectError:
                # This is expected - service should be unreachable
                pass
        
        # Restart the service
        started = self.stub_service.start()
        self.assertTrue(started, "StubService should restart successfully")
        
        # Give it a moment to start
        time.sleep(0.1)
        
        # Verify it's running again
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/health")
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()