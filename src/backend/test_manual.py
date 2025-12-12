"""Manual test to verify response utils"""
import json
from src.app.utils.response import success_response, error_response

# Test 1: success_response_default
print("Test 1: success_response_default")
r1 = success_response({"key": "value"})
body1 = json.loads(r1.body.decode())
assert r1.status_code == 200
assert body1["is_success"] is True
assert "key" in body1["data"]
assert body1["data"]["key"] == "value"
print("✓ PASS")

# Test 2: success_response_custom_message
print("Test 2: success_response_custom_message")
r2 = success_response({"id": 1}, message="Operation successful")
body2 = json.loads(r2.body.decode())
assert r2.status_code == 200
assert body2["message"] == "Operation successful"
print("✓ PASS")

# Test 3: success_response_custom_status_code
print("Test 3: success_response_custom_status_code")
r3 = success_response({"id": 1}, status_code=201)
assert r3.status_code == 201
print("✓ PASS")

# Test 4: success_response_no_data
print("Test 4: success_response_no_data")
r4 = success_response()
body4 = json.loads(r4.body.decode())
assert r4.status_code == 200
assert body4["is_success"] is True
print("✓ PASS")

# Test 5: error_response_default
print("Test 5: error_response_default")
r5 = error_response("Something went wrong")
body5 = json.loads(r5.body.decode())
assert r5.status_code == 400
assert body5["is_success"] is False
assert "Something went wrong" in body5["message"]
print("✓ PASS")

# Test 6: error_response_custom_status_code
print("Test 6: error_response_custom_status_code")
r6 = error_response("Not found", status_code=404)
assert r6.status_code == 404
print("✓ PASS")

# Test 7: error_response_with_details
print("Test 7: error_response_with_details")
details = {"field": "email", "reason": "invalid format"}
r7 = error_response("Validation failed", details=details)
body7 = json.loads(r7.body.decode())
assert r7.status_code == 400
assert "Validation failed" in body7["message"]
assert "field" in str(body7) or "email" in str(body7)
print("✓ PASS")

# Test 8: error_response_unauthorized
print("Test 8: error_response_unauthorized")
r8 = error_response("Unauthorized", status_code=401)
body8 = json.loads(r8.body.decode())
assert r8.status_code == 401
assert "Unauthorized" in body8["message"]
print("✓ PASS")

# Test 9: error_response_forbidden
print("Test 9: error_response_forbidden")
r9 = error_response("Forbidden", status_code=403)
assert r9.status_code == 403
print("✓ PASS")

print("\n✅ All response utils tests passed!")




