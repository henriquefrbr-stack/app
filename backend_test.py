import requests
import sys
from datetime import datetime

class FilmOrbitAPITester:
    def __init__(self, base_url="https://filmorbit.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, params=None, data=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if response.status_code < 400 else {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test("Root API Endpoint", "GET", "", 200)

    def test_status_endpoints(self):
        """Test status check endpoints"""
        # Test GET status
        success1, _ = self.run_test("Get Status Checks", "GET", "status", 200)
        
        # Test POST status
        test_data = {"client_name": f"test_client_{datetime.now().strftime('%H%M%S')}"}
        success2, response = self.run_test("Create Status Check", "POST", "status", 200, data=test_data)
        
        return success1 and success2

    def test_movie_search(self):
        """Test movie search functionality"""
        # Test with popular movie
        success1, response1 = self.run_test(
            "Search Movies - Inception", 
            "GET", 
            "movies/search", 
            200, 
            params={"query": "Inception"}
        )
        
        if success1 and response1:
            results = response1.get('results', [])
            if len(results) > 0:
                print(f"   Found {len(results)} movies")
                first_movie = results[0]
                print(f"   First result: {first_movie.get('title')} ({first_movie.get('id')})")
            else:
                print(f"   No results found")
        
        # Test with another movie
        success2, response2 = self.run_test(
            "Search Movies - Avatar", 
            "GET", 
            "movies/search", 
            200, 
            params={"query": "Avatar"}
        )
        
        # Test with empty query
        success3, _ = self.run_test(
            "Search Movies - Empty Query", 
            "GET", 
            "movies/search", 
            422,  # Should return validation error
            params={"query": ""}
        )
        
        return success1 and success2

    def test_movie_details(self):
        """Test getting movie details"""
        # Test with known movie ID (Inception)
        inception_id = 27205
        success1, response1 = self.run_test(
            f"Get Movie Details - ID {inception_id}", 
            "GET", 
            f"movies/{inception_id}", 
            200
        )
        
        if success1 and response1:
            print(f"   Movie: {response1.get('title')}")
            print(f"   Rating: {response1.get('vote_average')}")
            print(f"   Poster URL: {response1.get('poster_url', 'N/A')}")
        
        # Test with invalid movie ID
        success2, _ = self.run_test(
            "Get Movie Details - Invalid ID", 
            "GET", 
            "movies/999999999", 
            500  # Should return error
        )
        
        return success1

    def test_movie_network(self):
        """Test movie network endpoint"""
        # Test with known movie ID (Inception)
        inception_id = 27205
        success1, response1 = self.run_test(
            f"Get Movie Network - ID {inception_id}", 
            "GET", 
            f"movies/{inception_id}/network", 
            200
        )
        
        if success1 and response1:
            central_movie = response1.get('central_movie', {})
            related_movies = response1.get('related_movies', [])
            print(f"   Central Movie: {central_movie.get('title')}")
            print(f"   Related Movies: {len(related_movies)} found")
            
            if related_movies:
                print(f"   First related: {related_movies[0].get('title')}")
        
        # Test with another popular movie (Avatar)
        avatar_id = 19995
        success2, response2 = self.run_test(
            f"Get Movie Network - ID {avatar_id}", 
            "GET", 
            f"movies/{avatar_id}/network", 
            200
        )
        
        # Test with invalid movie ID
        success3, _ = self.run_test(
            "Get Movie Network - Invalid ID", 
            "GET", 
            "movies/999999999/network", 
            500  # Should return error
        )
        
        return success1 and success2

    def test_tmdb_integration(self):
        """Test TMDB API integration by checking data quality"""
        print(f"\n🔍 Testing TMDB Integration Quality...")
        
        # Search for a well-known movie
        success, response = self.run_test(
            "TMDB Integration - Data Quality", 
            "GET", 
            "movies/search", 
            200, 
            params={"query": "The Dark Knight"}
        )
        
        if success and response:
            results = response.get('results', [])
            if results:
                movie = results[0]
                
                # Check required fields
                required_fields = ['id', 'title', 'overview', 'vote_average', 'release_date']
                missing_fields = [field for field in required_fields if not movie.get(field)]
                
                if not missing_fields:
                    print(f"✅ All required fields present")
                    print(f"   Title: {movie.get('title')}")
                    print(f"   Year: {movie.get('release_date', 'N/A')[:4]}")
                    print(f"   Rating: {movie.get('vote_average')}")
                    print(f"   Has poster: {'Yes' if movie.get('poster_url') else 'No'}")
                    return True
                else:
                    print(f"❌ Missing fields: {missing_fields}")
                    return False
            else:
                print(f"❌ No search results found")
                return False
        
        return False

def main():
    print("🎬 FilmOrbit API Testing Suite")
    print("=" * 50)
    
    # Setup
    tester = FilmOrbitAPITester()
    
    # Run all tests
    print(f"\n📡 Testing API at: {tester.api_url}")
    
    # Basic connectivity
    root_success = tester.test_root_endpoint()
    
    # Status endpoints
    status_success = tester.test_status_endpoints()
    
    # Movie search
    search_success = tester.test_movie_search()
    
    # Movie details
    details_success = tester.test_movie_details()
    
    # Movie network
    network_success = tester.test_movie_network()
    
    # TMDB integration quality
    tmdb_success = tester.test_tmdb_integration()
    
    # Print final results
    print(f"\n" + "=" * 50)
    print(f"📊 FINAL RESULTS")
    print(f"=" * 50)
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Detailed breakdown
    test_results = {
        "Root Endpoint": root_success,
        "Status Endpoints": status_success,
        "Movie Search": search_success,
        "Movie Details": details_success,
        "Movie Network": network_success,
        "TMDB Integration": tmdb_success
    }
    
    print(f"\n📋 Test Breakdown:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    # Return appropriate exit code
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())