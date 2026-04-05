import sys
import asyncio
from app.routes.predict import predict

async def test():
    try:
        result = await predict(
            title="Test Berita",
            body="Ini adalah test berita untuk melihat error"
        )
        print("SUCCESS:", result)
    except Exception as e:
        print("ERROR:", type(e).__name__)
        print("Message:", str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
