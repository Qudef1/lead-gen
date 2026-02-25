import requests
import sys
import time
import json
from datetime import datetime

class LeadAnalyzerAPITester:
    def __init__(self, base_url="https://lead-catch-up.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_base}/{endpoint}" if endpoint else f"{self.api_base}/"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:500]}")
                except:
                    print(f"   Response: {response.text[:200]}")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:500]}")

            self.test_results.append({
                'test': name,
                'success': success,
                'expected_status': expected_status,
                'actual_status': response.status_code,
                'response_preview': response.text[:200]
            })

            return success, response.json() if success and response.content else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                'test': name,
                'success': False,
                'error': str(e)
            })
            return False, {}

    def test_health_endpoint(self):
        """Test GET /api/ health check"""
        success, response = self.run_test(
            "Health Check (GET /api/)",
            "GET",
            "",
            200
        )
        return success and 'message' in response

    def test_start_analysis(self):
        """Test POST /api/run-analysis"""
        success, response = self.run_test(
            "Start Analysis (POST /api/run-analysis)",
            "POST", 
            "run-analysis",
            200
        )
        if success and 'job_id' in response:
            return response['job_id']
        return None

    def test_job_status(self, job_id):
        """Test GET /api/status/{job_id}"""
        success, response = self.run_test(
            f"Job Status (GET /api/status/{job_id})",
            "GET",
            f"status/{job_id}",
            200
        )
        if success:
            required_fields = ['job_id', 'step', 'status_text', 'total_conversations', 'total_leads', 'processed', 'completed']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing required fields: {missing_fields}")
                return False
            return True
        return False

    def test_nonexistent_status(self):
        """Test GET /api/status/nonexistent returns 404"""
        success, response = self.run_test(
            "Non-existent Job Status (GET /api/status/nonexistent)",
            "GET",
            "status/nonexistent-job-id",
            404
        )
        return success

    def test_job_results(self, job_id):
        """Test GET /api/results/{job_id}"""
        success, response = self.run_test(
            f"Job Results (GET /api/results/{job_id})",
            "GET",
            f"results/{job_id}",
            200
        )
        if success:
            required_fields = ['job_id', 'completed', 'total_leads', 'results']
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"⚠️  Missing required fields: {missing_fields}")
                return False
            return True
        return False

    def wait_for_job_completion(self, job_id, max_wait_seconds=60):
        """Wait for job to complete or timeout"""
        print(f"\n⏳ Waiting for job {job_id} to complete (max {max_wait_seconds}s)...")
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            try:
                response = requests.get(f"{self.api_base}/status/{job_id}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Status: {data.get('step', 'unknown')} - {data.get('status_text', 'no status')}")
                    
                    if data.get('completed', False):
                        print(f"✅ Job completed in {time.time() - start_time:.1f}s")
                        return True
                    
                    if data.get('step') == 'error':
                        print(f"❌ Job failed: {data.get('error', 'Unknown error')}")
                        return False
                        
                time.sleep(3)
            except Exception as e:
                print(f"   Error checking status: {e}")
                time.sleep(5)
                
        print(f"⏰ Job did not complete within {max_wait_seconds}s")
        return False

def main():
    print("🚀 Starting Interexy Lead Analyzer API Tests")
    print("="*60)
    
    tester = LeadAnalyzerAPITester()
    
    # Test 1: Health check
    if not tester.test_health_endpoint():
        print("❌ Health check failed, stopping tests")
        return 1

    # Test 2: Non-existent job status (404 test)
    tester.test_nonexistent_status()

    # Test 3: Start analysis
    job_id = tester.test_start_analysis()
    if not job_id:
        print("❌ Failed to start analysis, stopping tests")
        return 1

    # Test 4: Check initial job status
    if not tester.test_job_status(job_id):
        print("❌ Job status check failed")

    # Test 5: Check job results endpoint (should work even if job is running)
    if not tester.test_job_results(job_id):
        print("❌ Job results check failed")

    # Optional: Wait for job completion to see full flow
    print(f"\n📝 Note: Job {job_id} is running with real HeyReach/OpenAI APIs")
    print("This may take several minutes to complete.")
    print("Testing the API surface - not waiting for full completion.")

    # Print summary
    print(f"\n📊 Test Results Summary")
    print("="*40)
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        failed_tests = [r for r in tester.test_results if not r['success']]
        print(f"❌ {len(failed_tests)} test(s) failed:")
        for test in failed_tests:
            print(f"   - {test['test']}: {test.get('error', f'Status {test.get(\"actual_status\")} != {test.get(\"expected_status\")}')}")
        return 1

if __name__ == "__main__":
    sys.exit(main())