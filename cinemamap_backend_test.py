import requests
import sys
from datetime import datetime

class CinemaMapAPITester:
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
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)

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

    def test_branding_update(self):
        """Test that API branding has been updated to CinemaMap"""
        success, response = self.run_test("CinemaMap Branding Check", "GET", "", 200)
        
        if success and response:
            message = response.get('message', '')
            if 'CinemaMap' in message:
                print(f"✅ Branding updated correctly: {message}")
                return True
            else:
                print(f"❌ Branding not updated. Message: {message}")
                return False
        return False

    def test_rio_movie_search(self):
        """Test searching for Rio (2011) movie specifically"""
        success, response = self.run_test(
            "Search Rio (2011) Movie", 
            "GET", 
            "movies/search", 
            200, 
            params={"query": "Rio 2011"}
        )
        
        rio_movie_id = None
        if success and response:
            results = response.get('results', [])
            print(f"   Found {len(results)} movies for 'Rio 2011'")
            
            # Look for Rio (2011) specifically
            for movie in results:
                title = movie.get('title', '')
                release_date = movie.get('release_date', '')
                if 'Rio' in title and '2011' in release_date:
                    rio_movie_id = movie.get('id')
                    print(f"   Found Rio (2011): ID {rio_movie_id}, Title: {title}")
                    break
            
            if not rio_movie_id:
                print(f"   ❌ Rio (2011) not found in search results")
                # Try alternative search
                success2, response2 = self.run_test(
                    "Search Rio Movie (alternative)", 
                    "GET", 
                    "movies/search", 
                    200, 
                    params={"query": "Rio"}
                )
                if success2 and response2:
                    results2 = response2.get('results', [])
                    for movie in results2:
                        title = movie.get('title', '')
                        release_date = movie.get('release_date', '')
                        if title == 'Rio' and release_date and '2011' in release_date:
                            rio_movie_id = movie.get('id')
                            print(f"   Found Rio (2011) in alternative search: ID {rio_movie_id}")
                            break
        
        return success, rio_movie_id

    def test_enhanced_algorithm_with_rio(self, rio_movie_id):
        """Test the enhanced recommendation algorithm specifically with Rio movie"""
        if not rio_movie_id:
            print(f"❌ Cannot test enhanced algorithm - Rio movie ID not found")
            return False
            
        success, response = self.run_test(
            f"Enhanced Algorithm - Rio Network (ID: {rio_movie_id})", 
            "GET", 
            f"movies/{rio_movie_id}/network", 
            200
        )
        
        if success and response:
            central_movie = response.get('central_movie', {})
            related_movies = response.get('related_movies', [])
            
            print(f"   Central Movie: {central_movie.get('title')}")
            print(f"   Director: {central_movie.get('director', 'N/A')}")
            print(f"   Genres: {[g.get('name') for g in central_movie.get('genres', [])]}")
            print(f"   Related Movies: {len(related_movies)} found")
            
            # Check for similarity scores
            high_similarity_count = 0
            rio_2_found = False
            
            for i, movie in enumerate(related_movies[:5]):  # Check top 5
                title = movie.get('title', '')
                similarity_score = movie.get('similarity_score', 0)
                director = movie.get('director', 'N/A')
                
                print(f"   {i+1}. {title} - Similarity: {similarity_score:.3f} - Director: {director}")
                
                if similarity_score > 0.7:
                    high_similarity_count += 1
                
                if 'Rio 2' in title:
                    rio_2_found = True
                    print(f"   ✅ Rio 2 found with similarity score: {similarity_score:.3f}")
            
            # Verify enhanced algorithm features
            algorithm_success = True
            if not rio_2_found:
                print(f"   ⚠️  Rio 2 not found in top recommendations")
                algorithm_success = False
            
            if high_similarity_count == 0:
                print(f"   ⚠️  No high similarity scores (>0.7) found")
                algorithm_success = False
            else:
                print(f"   ✅ Found {high_similarity_count} movies with high similarity scores")
            
            return algorithm_success
        
        return False

    def test_similarity_score_calculation(self):
        """Test that similarity scores are being calculated and included"""
        # Test with a popular movie that should have good recommendations
        inception_id = 27205
        success, response = self.run_test(
            f"Similarity Score Test - Inception (ID: {inception_id})", 
            "GET", 
            f"movies/{inception_id}/network", 
            200
        )
        
        if success and response:
            related_movies = response.get('related_movies', [])
            
            scores_present = 0
            valid_scores = 0
            
            for movie in related_movies:
                similarity_score = movie.get('similarity_score')
                if similarity_score is not None:
                    scores_present += 1
                    if 0 <= similarity_score <= 1:
                        valid_scores += 1
                    print(f"   {movie.get('title')}: {similarity_score:.3f}")
            
            print(f"   Movies with similarity scores: {scores_present}/{len(related_movies)}")
            print(f"   Valid scores (0-1 range): {valid_scores}/{scores_present}")
            
            return scores_present > 0 and valid_scores == scores_present
        
        return False

    def test_enhanced_movie_details(self):
        """Test that movie details include enhanced information (director, cast, genres)"""
        inception_id = 27205
        success, response = self.run_test(
            f"Enhanced Movie Details Test (ID: {inception_id})", 
            "GET", 
            f"movies/{inception_id}/network", 
            200
        )
        
        if success and response:
            central_movie = response.get('central_movie', {})
            
            # Check for enhanced fields
            has_director = bool(central_movie.get('director'))
            has_genres = bool(central_movie.get('genres'))
            has_cast = bool(central_movie.get('cast'))
            
            print(f"   Director present: {has_director} - {central_movie.get('director', 'N/A')}")
            print(f"   Genres present: {has_genres} - {len(central_movie.get('genres', []))} genres")
            print(f"   Cast present: {has_cast} - {len(central_movie.get('cast', []))} cast members")
            
            if has_cast:
                cast = central_movie.get('cast', [])
                for actor in cast[:3]:
                    print(f"     - {actor.get('name')} as {actor.get('character')}")
            
            return has_director and has_genres and has_cast
        
        return False

    def test_algorithm_performance(self):
        """Test that the enhanced algorithm doesn't significantly slow down responses"""
        import time
        
        test_movie_ids = [27205, 19995, 550]  # Inception, Avatar, Fight Club
        response_times = []
        
        for movie_id in test_movie_ids:
            start_time = time.time()
            success, response = self.run_test(
                f"Performance Test - Movie {movie_id}", 
                "GET", 
                f"movies/{movie_id}/network", 
                200
            )
            end_time = time.time()
            
            if success:
                response_time = end_time - start_time
                response_times.append(response_time)
                print(f"   Response time: {response_time:.2f}s")
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            print(f"   Average response time: {avg_time:.2f}s")
            
            # Consider acceptable if under 10 seconds
            return avg_time < 10.0
        
        return False

def main():
    print("🎬 CinemaMap Enhanced API Testing Suite")
    print("=" * 60)
    
    # Setup
    tester = CinemaMapAPITester()
    
    # Run all tests
    print(f"\n📡 Testing API at: {tester.api_url}")
    
    # Test 1: Branding update
    branding_success = tester.test_branding_update()
    
    # Test 2: Rio movie search and enhanced algorithm
    rio_search_success, rio_movie_id = tester.test_rio_movie_search()
    rio_algorithm_success = False
    if rio_movie_id:
        rio_algorithm_success = tester.test_enhanced_algorithm_with_rio(rio_movie_id)
    
    # Test 3: Similarity score calculation
    similarity_success = tester.test_similarity_score_calculation()
    
    # Test 4: Enhanced movie details
    details_success = tester.test_enhanced_movie_details()
    
    # Test 5: Algorithm performance
    performance_success = tester.test_algorithm_performance()
    
    # Print final results
    print(f"\n" + "=" * 60)
    print(f"📊 CINEMAMAP ENHANCED FEATURES TEST RESULTS")
    print(f"=" * 60)
    print(f"Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print(f"Success rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    # Detailed breakdown
    test_results = {
        "CinemaMap Branding": branding_success,
        "Rio Movie Search": rio_search_success,
        "Rio Enhanced Algorithm": rio_algorithm_success,
        "Similarity Score Calculation": similarity_success,
        "Enhanced Movie Details": details_success,
        "Algorithm Performance": performance_success
    }
    
    print(f"\n📋 Enhanced Features Test Breakdown:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    # Specific findings
    print(f"\n🔍 Key Findings:")
    if branding_success:
        print(f"   ✅ API successfully rebranded to CinemaMap")
    else:
        print(f"   ❌ API branding still shows old name")
    
    if rio_algorithm_success:
        print(f"   ✅ Enhanced algorithm working well with Rio movie")
    else:
        print(f"   ❌ Enhanced algorithm needs improvement for Rio recommendations")
    
    if similarity_success:
        print(f"   ✅ Similarity scores are being calculated and included")
    else:
        print(f"   ❌ Similarity scores missing or invalid")
    
    # Return appropriate exit code
    return 0 if all(test_results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())