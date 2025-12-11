"""
Test the new RL metrics endpoint
Run this after logging in as admin
"""
import requests

print("=" * 80)
print("🧪 TESTING RL METRICS ENDPOINT")
print("=" * 80)

# Test the endpoint
url = "http://localhost:5000/api/admin/analytics/rl-metrics"

try:
    print(f"\n📡 Calling: {url}")
    response = requests.get(url)
    
    print(f"\n📊 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get('success'):
            metrics = data['data']
            
            print("\n✅ SUCCESS! Here's what we got:")
            print("-" * 80)
            print(f"Total Users:        {metrics['total_users']}")
            print(f"Total Bookmarks:    {metrics['total_bookmarks']}")
            print(f"Total Interactions: {metrics['total_interactions']}")
            print(f"Overall CTR:        {metrics['overall_ctr']:.2f}%")
            print(f"Position data points: {len(metrics['ctr_by_position'])}")
            print(f"Domain data points:   {len(metrics['ctr_by_domain'])}")
            print(f"Top projects:         {len(metrics['top_projects'])}")
            
            print("\n📈 CTR by Position (first 5):")
            for pos in metrics['ctr_by_position'][:5]:
                print(f"   Position {pos['position']}: {pos['ctr']:.2f}%")
            
            print("\n🏷️  CTR by Domain:")
            for domain in metrics['ctr_by_domain']:
                print(f"   {domain['domain']}: {domain['ctr']:.2f}%")
            
            print("\n🏆 Top Projects:")
            for project in metrics['top_projects'][:3]:
                print(f"   {project['title']} ({project['domain']})")
                print(f"      Clicks: {project['clicks']}, Bookmarks: {project['bookmarks']}")
            
            print("\n" + "=" * 80)
            print("✅ ENDPOINT WORKING CORRECTLY!")
            print("=" * 80)
        else:
            print(f"\n❌ API returned error: {data.get('error')}")
    
    elif response.status_code == 401:
        print("\n⚠️  UNAUTHORIZED - You need to login as admin first!")
        print("\n   Steps:")
        print("   1. Logout: http://localhost:5000/logout")
        print("   2. Login with: tonykondaveetijmj98@gmail.com")
        print("   3. Run this test again")
    
    elif response.status_code == 403:
        print("\n⚠️  FORBIDDEN - Admin access required!")
        print("   Make sure you're logged in with an admin email")
    
    else:
        print(f"\n❌ Unexpected status code: {response.status_code}")
        print(f"Response: {response.text[:200]}")

except requests.exceptions.ConnectionError:
    print("\n❌ CONNECTION ERROR!")
    print("   Make sure Flask app is running: python app.py")

except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("\n" + "=" * 80)
