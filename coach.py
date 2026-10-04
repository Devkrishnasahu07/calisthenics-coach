import os
import json
import ollama
import asyncio
from dotenv import load_dotenv
from backboard import BackboardClient
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play

# Load API keys from the .env file
load_dotenv()

# Initialize the API Clients
bb_client = BackboardClient(api_key=os.getenv("BACKBOARD_API_KEY"))
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
assistant_id = "dd3804df-ed18-4f22-98f8-4aa5fcea2809" 

async def generate_workout(user_state: str):
    print("🧠 Checking Backboard memory for past workouts...")
    try:
        memories = await bb_client.get_memories(assistant_id)
        history_context = "\n".join([m.content for m in memories.memories]) if memories.memories else "No past workouts yet."
    except Exception:
        history_context = "No past workouts yet."

    print("🤖 Generating workout locally using Gemma 2...")
    
    system_prompt = f"""You are a strict, bodyweight-only calisthenics coach.
User's History: {history_context}

RULES:
1. ONLY assign bodyweight exercises.
2. Identify the language of the user's input.
3. The 'coach_message' MUST be written entirely in that identified language and explicitly mention the exercise name and rep count.
4. Assign a real exercise for fitness queries, or "Penalty Burpees" for off-topic queries.

Output ONLY valid JSON format exactly like this:
{{"detected_language": "...", "exercise": "Squats", "reps": 20, "rest_seconds": 30, "coach_message": "..."}}
"""

    # Send the prompt to your LOCAL Gemma model via Ollama
    response = ollama.chat(model='gemma2:2b', messages=[
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': f"USER INPUT: {user_state}\n\n(CRITICAL INSTRUCTION: You MUST fill out the 'detected_language' key first. Then write the 'coach_message' in that exact language.)"}
    ])
    
    result_text = response['message']['content']
    
    # Clean up the output if Gemma adds markdown code blocks
    if result_text.startswith("```json"):
        result_text = result_text.replace("```json\n", "").replace("```", "").strip()

    try:
        workout_data = json.loads(result_text)
        
        # If the AI gets clever and returns a list of exercises, just grab the first one
        if isinstance(workout_data, list) and len(workout_data) > 0:
            workout_data = workout_data[0]
            
    except Exception as e:
        print(f"⚠️ AI Formatting Error. Raw output was: {result_text}")
        workout_data = {
            "exercise": "Burpees",
            "reps": 10,
            "rest_seconds": 30,
            "coach_message": "Let's kick off this circuit with some burpees! Keep moving!"
        }

    # Save today's workout to Backboard memory for tomorrow
    print("💾 Saving today's workout to Backboard memory...")
    await bb_client.add_memory(
        assistant_id=assistant_id,
        content=f"User stated: '{user_state}'. Assigned: {workout_data.get('reps', 10)} {workout_data.get('exercise', 'exercises')}.",
        metadata={"type": "workout"}
    )

    return workout_data

def speak_workout(workout_data):
    print("🗣️ Generating audio with ElevenLabs...")
    
    # Extract ONLY the coach message so it doesn't repeat the exercise twice
    speech_text = workout_data.get('coach_message', 'Great job.')
    
    audio = eleven_client.text_to_speech.convert(
        text=speech_text,
        voice_id="JBFqnCBsd6RMkjVDRZzb",
        model_id="eleven_multilingual_v2"
    )
    play(audio)