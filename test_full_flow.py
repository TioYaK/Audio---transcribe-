import requests
import json
import time
import wave
import struct
import math
import os

# Configuration
BASE_URL = "http://localhost:8000"
TEST_AUDIO_FILE = "test_audio_440hz.wav"

def create_dummy_wav(filename, duration=3.0):
    # Create 3 seconds of 440Hz sine wave, 16-bit Mono, 16kHz (native whisper)
    sample_rate = 16000
    n_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(n_samples):
            value = int(32767.0 * math.sin(2 * math.pi * 440.0 * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)
            
    print(f"Created dummy audio: {filename}")

def run_test():
    print("=== STARTING FULL SYSTEM TEST ===")
    
    # 0. Create Audio
    create_dummy_wav(TEST_AUDIO_FILE)
    
    try:
        # 1. Login
        print("\n--- 1. Login ---")
        login_data = {"username": "admin", "password": "any_password_works_for_admin"}
        resp = requests.post(f"{BASE_URL}/token", data=login_data)
        
        if resp.status_code != 200:
            print(f"LOGIN FAILED: {resp.status_code} - {resp.text}")
            return
            
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login Success.")
        
        # 2. Upload
        print("\n--- 2. Upload ---")
        with open(TEST_AUDIO_FILE, 'rb') as f:
            files = {'file': (TEST_AUDIO_FILE, f, 'audio/wav')}
            data = {'timestamp': True, 'diarization': True}
            resp = requests.post(f"{BASE_URL}/api/upload", files=files, data=data, headers=headers)
        
        if resp.status_code != 200:
            print(f"UPLOAD FAILED: {resp.status_code} - {resp.text}")
            return
            
        task_data = resp.json()
        task_id = task_data["task_id"]
        print(f"Upload Success. Task ID: {task_id}")
        
        # 3. Poll Status
        print("\n--- 3. Polling Status ---")
        start_time = time.time()
        while True:
            resp = requests.get(f"{BASE_URL}/api/status/{task_id}", headers=headers)
            status_data = resp.json()
            status = status_data["status"]
            progress = status_data.get("progress", 0)
            
            print(f"Status: {status} ({progress}%)")
            
            if status == "completed":
                print("Processing Completed!")
                break
            if status == "failed":
                print(f"PROCESSING FAILED: {status_data.get('error')}")
                return
            
            if time.time() - start_time > 60:
                print("TIMEOUT: Processing took longer than 60s")
                return
                
            time.sleep(2)
            
        # 4. Get Result
        print("\n--- 4. Get Result ---")
        resp = requests.get(f"{BASE_URL}/api/result/{task_id}", headers=headers)
        result = resp.json()
        
        print(f"Text Length: {len(result.get('text', ''))}")
        print(f"Summary: {result.get('summary')[:50]}...")
        print(f"Topics: {result.get('topics')}")
        
        if result.get('text'):
            print("\n✅ TEST PASSED: Transcription generated.")
        else:
            print("\n⚠️ TEST WARNING: No text generated (expected for sine wave 'silence', but pipeline worked).")
            
        # 5. Cleanup
        print("\n--- 5. Cleanup ---")
        requests.delete(f"{BASE_URL}/api/task/{task_id}", headers=headers)
        if os.path.exists(TEST_AUDIO_FILE):
            os.remove(TEST_AUDIO_FILE)
        print("Cleanup done.")
            
    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")

if __name__ == "__main__":
    run_test()
