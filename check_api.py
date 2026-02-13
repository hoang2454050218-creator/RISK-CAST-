import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            # Test root
            r = await client.get("http://localhost:8000/")
            print("Root endpoint:")
            print(r.json())
            print()
            
            # Test docs
            print("Checking /docs availability...")
            r2 = await client.get("http://localhost:8000/docs")
            print(f"Docs status: {r2.status_code}")
            print()
            
            # Test OpenAPI schema
            r3 = await client.get("http://localhost:8000/openapi.json")
            schema = r3.json()
            print("Available paths:")
            for path in list(schema.get("paths", {}).keys())[:20]:
                print(f"  {path}")
                
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(main())
