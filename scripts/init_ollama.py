#!/usr/bin/env python3
"""
Script to initialize Ollama model for the SSH Log Analysis API.
This script downloads and sets up the required Ollama model.
"""

import subprocess
import sys
import time
import requests
import json

from langchain_community.chat_models import ChatOllama

OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "llama3.2"  # You can change this to any model you prefer

def check_ollama_installed():
    """Check if Ollama is installed and running."""
    try:
        # Check if ollama command exists
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Ollama is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama command not found")
            return False
    except FileNotFoundError:
        print("❌ Ollama is not installed")
        return False

def check_ollama_running():
    """Check if Ollama service is running."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama service is running")
            return True
        else:
            print(f"❌ Ollama service not responding: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to Ollama service")
        return False

def list_installed_models():
    """List currently installed models."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            if models:
                print("📋 Currently installed models:")
                for model in models:
                    print(f"   - {model['name']} (size: {model.get('size', 'unknown')})")
                return [model['name'] for model in models]
            else:
                print("📋 No models currently installed")
                return []
        else:
            print(f"❌ Failed to list models: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Error listing models: {e}")
        return []

def pull_model(model_name):
    """Download and install a model."""
    print(f"📥 Pulling model '{model_name}'...")
    print("   This may take several minutes depending on model size and internet speed...")
    
    try:
        # Use ollama pull command
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Stream output in real-time
        for line in process.stdout:
            print(f"   {line.strip()}")
        
        process.wait()
        
        if process.returncode == 0:
            print(f"✅ Model '{model_name}' successfully installed")
            return True
        else:
            print(f"❌ Failed to install model '{model_name}'")
            return False
            
    except Exception as e:
        print(f"❌ Error pulling model: {e}")
        return False

def test_model(model_name):
    """Test if the model is working correctly using LangChain ChatOllama."""
    print(f"🧪 Testing model '{model_name}' via LangChain...")
    try:
        llm = ChatOllama(model=model_name, base_url=OLLAMA_BASE_URL)
        reply = llm.invoke("Hello, respond with just OK")
        response_text = getattr(reply, "content", "").strip()
        print(f"✅ Model test successful. Response: '{response_text}'")
        return True
    except Exception as e:
        print(f"❌ Error testing model via LangChain: {e}")
        return False

def main():
    """Main initialization function."""
    print("🚀 Ollama Model Initialization Script")
    print("=" * 50)
    
    # Check if Ollama is installed
    if not check_ollama_installed():
        print("\n📖 To install Ollama:")
        print("   Visit: https://ollama.ai/download")
        print("   Or run: curl -fsSL https://ollama.ai/install.sh | sh")
        return False
    
    # Check if Ollama service is running
    if not check_ollama_running():
        print("\n🔄 Starting Ollama service...")
        try:
            # Try to start ollama serve in background
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("   Waiting for service to start...")
            time.sleep(5)
            
            if not check_ollama_running():
                print("❌ Failed to start Ollama service")
                print("   Try running: ollama serve")
                return False
        except Exception as e:
            print(f"❌ Error starting Ollama service: {e}")
            return False
    
    # List current models
    installed_models = list_installed_models()
    
    # Check if our target model is already installed
    if MODEL_NAME in installed_models:
        print(f"✅ Model '{MODEL_NAME}' is already installed")
        if test_model(MODEL_NAME):
            print(f"\n🎉 Model '{MODEL_NAME}' is ready to use!")
            return True
        else:
            print(f"⚠️  Model '{MODEL_NAME}' is installed but not working properly")
            return False
    
    # Install the model
    print(f"\n📥 Installing model '{MODEL_NAME}'...")
    if pull_model(MODEL_NAME):
        if test_model(MODEL_NAME):
            print(f"\n🎉 Model '{MODEL_NAME}' is ready to use!")
            print(f"\n💡 You can now use this model in your FastAPI application")
            return True
        else:
            print(f"⚠️  Model '{MODEL_NAME}' installed but test failed")
            return False
    else:
        print(f"❌ Failed to install model '{MODEL_NAME}'")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Ollama initialization completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Ollama initialization failed!")
        sys.exit(1)
