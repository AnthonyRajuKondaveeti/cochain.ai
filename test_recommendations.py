from app import recommendation_service
import json

user_id = '82650b59-367b-4c53-b1e8-741536c84e4a'
print(f"Testing recommendations for user: {user_id}")

result = recommendation_service.get_recommendations_for_user(user_id, 12)

print(f"\nSuccess: {result.get('success')}")
print(f"Error: {result.get('error')}")
print(f"Recommendations count: {len(result.get('recommendations', []))}")
print(f"Cached: {result.get('cached', False)}")

if result.get('recommendations'):
    print(f"\nFirst recommendation:")
    print(json.dumps(result['recommendations'][0], indent=2, default=str))
