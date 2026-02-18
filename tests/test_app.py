"""Tests for the Mergington High School API endpoints"""
import pytest
from fastapi import status


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) == 9  # All 9 activities
        
        # Verify some expected activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Soccer Team" in data
    
    def test_activities_have_required_fields(self, client):
        """Test that all activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)
    
    def test_chess_club_initial_participants(self, client):
        """Test Chess Club has correct initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        chess_club = data["Chess Club"]
        assert len(chess_club["participants"]) == 2
        assert "michael@mergington.edu" in chess_club["participants"]
        assert "daniel@mergington.edu" in chess_club["participants"]


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant_success(self, client):
        """Test successful signup of a new participant"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Chess Club"
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_already_registered_participant(self, client):
        """Test signup fails when participant is already registered"""
        # Try to sign up a participant who is already registered
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        data = response.json()
        assert data["detail"] == "Student is already signed up for this activity"
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup fails for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_with_url_encoded_activity_name(self, client):
        """Test signup works with URL-encoded activity names"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=newcoder@mergington.edu"
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newcoder@mergington.edu" in activities_data["Programming Class"]["participants"]
    
    def test_signup_multiple_activities_same_user(self, client):
        """Test that same user can sign up for multiple activities"""
        email = "multisport@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Sign up for Soccer Team
        response2 = client.post(f"/activities/Soccer Team/signup?email={email}")
        assert response2.status_code == status.HTTP_200_OK
        
        # Verify user is in both activities
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data["Chess Club"]["participants"]
        assert email in activities_data["Soccer Team"]["participants"]


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant_success(self, client):
        """Test successful unregistration of an existing participant"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["message"] == "Unregistered michael@mergington.edu from Chess Club"
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]
        # But daniel should still be there
        assert "daniel@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_unregister_not_registered_participant(self, client):
        """Test unregister fails when participant is not registered"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        data = response.json()
        assert data["detail"] == "Student is not signed up for this activity"
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister fails for non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_with_url_encoded_activity_name(self, client):
        """Test unregister works with URL-encoded activity names"""
        response = client.delete(
            "/activities/Programming%20Class/unregister?email=emma@mergington.edu"
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "emma@mergington.edu" not in activities_data["Programming Class"]["participants"]


class TestSignupAndUnregisterFlow:
    """Integration tests for signup and unregister workflows"""
    
    def test_complete_signup_unregister_flow(self, client):
        """Test complete flow: signup -> verify -> unregister -> verify"""
        email = "flowtest@mergington.edu"
        activity = "Chess Club"
        
        # Initial state - participant not in activity
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == status.HTTP_200_OK
        
        # Verify signup
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == status.HTTP_200_OK
        
        # Verify unregister
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
    
    def test_cannot_signup_twice(self, client):
        """Test that signing up twice for same activity fails"""
        email = "duplicate@mergington.edu"
        activity = "Soccer Team"
        
        # First signup succeeds
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Second signup fails
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already signed up" in response2.json()["detail"]
    
    def test_cannot_unregister_twice(self, client):
        """Test that unregistering twice fails"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # First unregister succeeds
        response1 = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Second unregister fails
        response2 = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "not signed up" in response2.json()["detail"]
    
    def test_signup_after_unregister(self, client):
        """Test that a user can sign up again after unregistering"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Unregister (michael is initially registered)
        response1 = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response1.status_code == status.HTTP_200_OK
        
        # Sign up again
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == status.HTTP_200_OK
        
        # Verify user is registered
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity]["participants"]
