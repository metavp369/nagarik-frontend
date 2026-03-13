"""
Admin Panel API Tests — Phase 1
Tests: User Management, Facility Management, System Health, RBAC enforcement
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "nischint4parents@gmail.com"
ADMIN_PASSWORD = "secret123"
OPERATOR_EMAIL = "operator@nischint.com"  
OPERATOR_PASSWORD = "operator123"


class TestAdminPanelRBAC:
    """RBAC enforcement: Admin endpoints should return 403 for non-admin users"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin user (has admin + guardian roles)"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        assert resp.status_code == 200, f"Admin login failed: {resp.text}"
        return resp.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def operator_token(self):
        """Login as operator user (non-admin)"""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": OPERATOR_EMAIL, "password": OPERATOR_PASSWORD
        })
        assert resp.status_code == 200, f"Operator login failed: {resp.text}"
        return resp.json()["access_token"]
    
    def test_admin_system_health_allowed(self, admin_token):
        """Admin can access system health"""
        resp = requests.get(f"{BASE_URL}/api/admin/system-health", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "users" in data
        assert "facilities" in data
        assert "services" in data
    
    def test_operator_system_health_denied(self, operator_token):
        """Operator (non-admin) should get 403 on admin endpoints"""
        resp = requests.get(f"{BASE_URL}/api/admin/system-health", headers={
            "Authorization": f"Bearer {operator_token}"
        })
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    
    def test_operator_stats_denied(self, operator_token):
        """Operator should get 403 on /admin/stats"""
        resp = requests.get(f"{BASE_URL}/api/admin/stats", headers={
            "Authorization": f"Bearer {operator_token}"
        })
        assert resp.status_code == 403
    
    def test_operator_users_list_denied(self, operator_token):
        """Operator should get 403 on /admin/users"""
        resp = requests.get(f"{BASE_URL}/api/admin/users", headers={
            "Authorization": f"Bearer {operator_token}"
        })
        assert resp.status_code == 403
    
    def test_operator_facilities_list_denied(self, operator_token):
        """Operator should get 403 on /admin/facilities"""
        resp = requests.get(f"{BASE_URL}/api/admin/facilities", headers={
            "Authorization": f"Bearer {operator_token}"
        })
        assert resp.status_code == 403
    
    def test_unauthorized_no_token(self):
        """Requests without token should get 401"""
        resp = requests.get(f"{BASE_URL}/api/admin/system-health")
        assert resp.status_code == 401


class TestSystemHealthEndpoint:
    """GET /api/admin/system-health"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return resp.json()["access_token"]
    
    def test_system_health_returns_status(self, admin_token):
        """System health should return healthy status"""
        resp = requests.get(f"{BASE_URL}/api/admin/system-health", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        # Status banner
        assert data["status"] in ["healthy", "degraded"]
        assert "timestamp" in data
        
        # Users breakdown
        users = data["users"]
        assert "total" in users
        assert "by_role" in users
        assert isinstance(users["by_role"], dict)
        for role in ["admin", "guardian", "operator", "caregiver", "user"]:
            assert role in users["by_role"]
        assert "cognito_linked" in users
        assert "assigned_to_facility" in users
        
        # Facilities
        facilities = data["facilities"]
        assert "total" in facilities
        assert "active" in facilities
        
        # Services
        services = data["services"]
        assert services["database"] in ["connected", "error"]
        assert services["cognito"] in ["enabled", "disabled"]
        assert services["google_oauth"] in ["enabled", "disabled"]


class TestAdminStats:
    """GET /api/admin/stats"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return resp.json()["access_token"]
    
    def test_stats_returns_quick_stats(self, admin_token):
        """Stats should return totals for users and facilities"""
        resp = requests.get(f"{BASE_URL}/api/admin/stats", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        assert "total_users" in data
        assert "total_facilities" in data
        assert "active_facilities" in data
        assert isinstance(data["total_users"], int)
        assert isinstance(data["total_facilities"], int)


class TestUserManagement:
    """User Management Endpoints: List, Get, Update Role, Update Facility"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return resp.json()["access_token"]
    
    def test_list_users(self, admin_token):
        """GET /admin/users returns paginated user list"""
        resp = requests.get(f"{BASE_URL}/api/admin/users", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        assert "users" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["users"], list)
        
        if data["users"]:
            user = data["users"][0]
            assert "id" in user
            assert "email" in user
            assert "role" in user
    
    def test_list_users_with_role_filter(self, admin_token):
        """GET /admin/users?role=admin filters by role"""
        resp = requests.get(f"{BASE_URL}/api/admin/users?role=admin", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        # All returned users should have admin role
        for user in data["users"]:
            assert user["role"] == "admin"
    
    def test_list_users_with_search(self, admin_token):
        """GET /admin/users?search=nischint filters by search term"""
        resp = requests.get(f"{BASE_URL}/api/admin/users?search=nischint", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        # Should find the admin user
        if data["total"] > 0:
            emails = [u["email"] for u in data["users"]]
            assert any("nischint" in e.lower() for e in emails)
    
    def test_get_user_detail(self, admin_token):
        """GET /admin/users/{id} returns user details"""
        # First get a user ID
        resp = requests.get(f"{BASE_URL}/api/admin/users?limit=1", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        users = resp.json()["users"]
        if not users:
            pytest.skip("No users in database")
        
        user_id = users[0]["id"]
        
        # Get detail
        resp = requests.get(f"{BASE_URL}/api/admin/users/{user_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        assert data["id"] == user_id
        assert "email" in data
        assert "role" in data
        assert "full_name" in data
    
    def test_get_user_detail_not_found(self, admin_token):
        """GET /admin/users/{id} returns 404 for invalid ID"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        resp = requests.get(f"{BASE_URL}/api/admin/users/{fake_uuid}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 404


class TestFacilityManagement:
    """Facility Management: List, Create, Update, Delete"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return resp.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def created_facility_id(self, admin_token):
        """Create a test facility to be used by other tests"""
        import uuid
        unique_code = f"TEST_{uuid.uuid4().hex[:6].upper()}"
        resp = requests.post(f"{BASE_URL}/api/admin/facilities", json={
            "name": "Test Facility for Admin Panel",
            "code": unique_code,
            "city": "Mumbai",
            "state": "Maharashtra"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        if resp.status_code == 201:
            return resp.json()["id"]
        pytest.skip(f"Could not create test facility: {resp.text}")
    
    def test_list_facilities(self, admin_token):
        """GET /admin/facilities returns facility list with user counts"""
        resp = requests.get(f"{BASE_URL}/api/admin/facilities", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        
        assert "facilities" in data
        assert "total" in data
        assert isinstance(data["facilities"], list)
        
        if data["facilities"]:
            fac = data["facilities"][0]
            assert "id" in fac
            assert "name" in fac
            assert "code" in fac
            assert "is_active" in fac
            assert "user_count" in fac
    
    def test_create_facility(self, admin_token):
        """POST /admin/facilities creates new facility"""
        import uuid
        unique_code = f"TEST_{uuid.uuid4().hex[:6].upper()}"
        
        resp = requests.post(f"{BASE_URL}/api/admin/facilities", json={
            "name": "TEST Facility Creation",
            "code": unique_code,
            "city": "Delhi",
            "state": "Delhi",
            "phone": "+91-1111111111",
            "email": "test@facility.com"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 201
        data = resp.json()
        
        assert "id" in data
        assert data["code"] == unique_code
        assert data["is_active"] == True
        
        # Cleanup: delete the created facility
        requests.delete(f"{BASE_URL}/api/admin/facilities/{data['id']}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
    
    def test_create_facility_duplicate_code(self, admin_token, created_facility_id):
        """POST /admin/facilities with duplicate code returns 409"""
        # Get the existing facility code
        resp = requests.get(f"{BASE_URL}/api/admin/facilities", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        facilities = resp.json()["facilities"]
        existing_code = None
        for f in facilities:
            if f["id"] == created_facility_id:
                existing_code = f["code"]
                break
        
        if not existing_code:
            pytest.skip("Could not find created facility")
        
        # Try to create with same code
        resp = requests.post(f"{BASE_URL}/api/admin/facilities", json={
            "name": "Duplicate Code Test",
            "code": existing_code
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 409
    
    def test_update_facility(self, admin_token, created_facility_id):
        """PUT /admin/facilities/{id} updates facility"""
        resp = requests.put(f"{BASE_URL}/api/admin/facilities/{created_facility_id}", json={
            "name": "Updated Facility Name",
            "city": "Bangalore"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Facility Name"
    
    def test_update_facility_not_found(self, admin_token):
        """PUT /admin/facilities/{id} returns 404 for invalid ID"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        resp = requests.put(f"{BASE_URL}/api/admin/facilities/{fake_uuid}", json={
            "name": "Nonexistent"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 404
    
    def test_delete_facility(self, admin_token):
        """DELETE /admin/facilities/{id} deletes facility"""
        import uuid
        unique_code = f"DEL_{uuid.uuid4().hex[:6].upper()}"
        
        # Create a facility to delete
        resp = requests.post(f"{BASE_URL}/api/admin/facilities", json={
            "name": "To Be Deleted",
            "code": unique_code
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 201
        fac_id = resp.json()["id"]
        
        # Delete it
        resp = requests.delete(f"{BASE_URL}/api/admin/facilities/{fac_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert resp.status_code == 200
        assert resp.json()["deleted"] == True
        
        # Verify it's gone
        resp = requests.get(f"{BASE_URL}/api/admin/facilities", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        fac_ids = [f["id"] for f in resp.json()["facilities"]]
        assert fac_id not in fac_ids
    
    def test_delete_facility_not_found(self, admin_token):
        """DELETE /admin/facilities/{id} returns 404 for invalid ID"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        resp = requests.delete(f"{BASE_URL}/api/admin/facilities/{fake_uuid}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        
        assert resp.status_code == 404


class TestUserRoleAndFacilityUpdate:
    """User role and facility assignment updates"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
        })
        return resp.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def test_user_id(self, admin_token):
        """Get the operator user ID for testing"""
        resp = requests.get(f"{BASE_URL}/api/admin/users?search=operator", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        users = resp.json()["users"]
        for u in users:
            if u["email"] == OPERATOR_EMAIL:
                return u["id"]
        pytest.skip("Operator user not found")
    
    def test_update_user_role(self, admin_token, test_user_id):
        """PUT /admin/users/{id}/role updates user role"""
        # Get current role
        resp = requests.get(f"{BASE_URL}/api/admin/users/{test_user_id}", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        original_role = resp.json()["role"]
        
        # Update to caregiver
        resp = requests.put(f"{BASE_URL}/api/admin/users/{test_user_id}/role", json={
            "role": "caregiver"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "caregiver"
        assert data["previous_role"] == original_role
        
        # Restore original role
        requests.put(f"{BASE_URL}/api/admin/users/{test_user_id}/role", json={
            "role": original_role
        }, headers={"Authorization": f"Bearer {admin_token}"})
    
    def test_update_user_role_invalid(self, admin_token, test_user_id):
        """PUT /admin/users/{id}/role with invalid role returns 422"""
        resp = requests.put(f"{BASE_URL}/api/admin/users/{test_user_id}/role", json={
            "role": "super_admin"  # Invalid role
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 422
    
    def test_update_user_facility(self, admin_token, test_user_id):
        """PUT /admin/users/{id}/facility assigns user to facility"""
        # First get or create a facility
        resp = requests.get(f"{BASE_URL}/api/admin/facilities", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        facilities = resp.json()["facilities"]
        
        if not facilities:
            # Create one
            import uuid
            resp = requests.post(f"{BASE_URL}/api/admin/facilities", json={
                "name": "Test Facility for User Assignment",
                "code": f"ASSIGN_{uuid.uuid4().hex[:4].upper()}"
            }, headers={"Authorization": f"Bearer {admin_token}"})
            fac_id = resp.json()["id"]
        else:
            fac_id = facilities[0]["id"]
        
        # Assign user to facility
        resp = requests.put(f"{BASE_URL}/api/admin/users/{test_user_id}/facility", json={
            "facility_id": fac_id
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 200
        assert resp.json()["facility_id"] == fac_id
        
        # Unassign (set to null)
        resp = requests.put(f"{BASE_URL}/api/admin/users/{test_user_id}/facility", json={
            "facility_id": None
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 200
        assert resp.json()["facility_id"] is None
    
    def test_update_user_facility_invalid(self, admin_token, test_user_id):
        """PUT /admin/users/{id}/facility with invalid facility returns 404"""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        resp = requests.put(f"{BASE_URL}/api/admin/users/{test_user_id}/facility", json={
            "facility_id": fake_uuid
        }, headers={"Authorization": f"Bearer {admin_token}"})
        
        assert resp.status_code == 404


# Cleanup fixture to remove test facilities
@pytest.fixture(scope="module", autouse=True)
def cleanup_test_facilities():
    """Cleanup TEST_ prefixed facilities after all tests"""
    yield
    
    # Login as admin
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    if resp.status_code != 200:
        return
    
    token = resp.json()["access_token"]
    
    # Get all facilities
    resp = requests.get(f"{BASE_URL}/api/admin/facilities", headers={
        "Authorization": f"Bearer {token}"
    })
    if resp.status_code != 200:
        return
    
    # Delete test facilities
    for fac in resp.json()["facilities"]:
        if fac["code"].startswith("TEST_") or fac["code"].startswith("DEL_") or fac["code"].startswith("ASSIGN_"):
            requests.delete(f"{BASE_URL}/api/admin/facilities/{fac['id']}", headers={
                "Authorization": f"Bearer {token}"
            })
