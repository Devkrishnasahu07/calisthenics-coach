import asyncio
import os
from dotenv import load_dotenv
from backboard import BackboardClient

load_dotenv()

async def register_coach():
    client = BackboardClient(api_key=os.getenv("BACKBOARD_API_KEY"))
    # This registers the agent on their servers
    assistant = await client.create_assistant(name="Gemma Calisthenics Coach") 
    
    print("\n🎉 Assistant Successfully Registered!")
    # This extracts your new, valid UUID
    print(f"👉 YOUR REAL ID: {assistant.assistant_id}\n") 

if __name__ == "__main__":
    asyncio.run(register_coach())