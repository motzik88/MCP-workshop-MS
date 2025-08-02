import requests
import json
from typing import List, Dict, Optional

class OllamaCall:
    def __init__(self, model_name: str = "llama3.2:latest", base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama client
        
        Args:
            model_name: Name of the Ollama model to use
            base_url: Base URL for Ollama API (default: http://localhost:11434)
        """
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/chat"
        
    def is_ollama_running(self) -> bool:
        """Check if Ollama server is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def list_models(self) -> List[str]:
        """List available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except requests.exceptions.RequestException:
            return []
    
    def call_ollama(self, messages: List[Dict[str, str]], stream: bool = False) -> str:
        """
        Call Ollama API with chat messages
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            stream: Whether to stream the response
            
        Returns:
            Response content as string
        """
        if not self.is_ollama_running():
            raise Exception("Ollama server is not running. Please start it with 'ollama serve'")
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=120  # Increased timeout for local models
            )
            
            if response.status_code == 200:
                if stream:
                    # Handle streaming response
                    full_response = ""
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line.decode('utf-8'))
                            if 'message' in data and 'content' in data['message']:
                                full_response += data['message']['content']
                    return full_response
                else:
                    # Handle non-streaming response
                    data = response.json()
                    return data['message']['content']
            else:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to Ollama: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test connection to Ollama with a simple message"""
        try:
            test_messages = [{"role": "user", "content": "Hello, respond with just 'OK' if you can see this."}]
            response = self.call_ollama(test_messages)
            return "OK" in response or "ok" in response.lower()
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False