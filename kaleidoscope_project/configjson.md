{
  "system": {
    "dimension": 128,
    "auto_discovery": true,
    "max_active_nodes": 1000,
    "mutation_interval": 10.0
  },
  "paths": {
    "data_dir": "./data",
    "log_dir": "./data/logs",
    "persistence_dir": "./data",
    "model_cache": "~/.cache/unravel-ai/models",
    "reconstruction_dir": "./reconstructed",
    "applications_dir": "./applications"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8000
  },
  "visualizer": {
    "port": 8081
  },
  "llm": {
    "provider": "llamacpp_api", // or "ollama", etc.
    "model_id": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF", // Or the model you downloaded
    "model_file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf", // The specific GGUF file name
    // *** CRITICAL: Set the full path to your downloaded model file below ***
    "model_path": "/home/jg/.cache/unravel-ai/models/TheBloke_Mistral-7B-Instruct-v0.2-GGUF/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    "api_base": "http://localhost:8080", // For llamacpp_api server
    "n_ctx": 2048
  },
  "quantum_sync": {
    "enable": true, // Or false if not using quantum-sync-protocol
    "server_url": "ws://localhost:8765" // Default from quantum-sync-protocol.py
  },
  "sandbox": {
    "enable": true // Or false if not using execution-sandbox-system.py
  }
}
