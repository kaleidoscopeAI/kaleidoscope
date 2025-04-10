#!/usr/bin/env python3
"""
Unified LLM Module for Kaleidoscope AI
======================================
Provides a comprehensive interface for interacting with various Language Model APIs,
with built-in support for multiple providers, chunking, caching, and error handling.

This module unifies functionality from:
- gpt_processor.py
- llm_chunking_utils.py
- llm_integration.py
- ollama_client.py

Features:
- Support for local models (via llama.cpp, Ollama) and API-based models
- Efficient text chunking for handling large files
- Token counting and management
- Response caching to reduce redundant calls
- Comprehensive error handling and logging
- Asynchronous streaming capabilities
"""

import os
import sys
import time
import json
import logging
import hashlib
import asyncio
import tempfile
import subprocess
import functools
import threading
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Tuple, Set, Optional, Union, Any, Generator, AsyncGenerator, Callable

# Setup basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("kaleidoscope_llm.log")
    ]
)

logger = logging.getLogger("unifiedLLM")

# Try to import optional dependencies but don't fail if they're not available
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.warning("PyTorch not available. Some local model capabilities will be limited.")

try:
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logger.warning("Transformers library not available. Using fallback tokenizer.")

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    logger.warning("TikToken not available. Using regex tokenizer instead.")

try:
    import requests
    import aiohttp
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("Requests/aiohttp not available. API calls will not work.")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("NumPy not available. Some vector operations will be limited.")

# Global configuration
DEFAULT_CACHE_DIR = os.path.expanduser("~/.cache/kaleidoscope/llm")

# ===== Core Classes =====

class ModelProvider(Enum):
    """Supported LLM providers"""
    LOCAL_TORCH = auto()
    LOCAL_LLAMACPP = auto()
    OLLAMA = auto()
    OPENAI = auto()
    ANTHROPIC = auto()
    CUSTOM_API = auto()

class TokenizerType(Enum):
    """Supported tokenizer types"""
    TRANSFORMERS = auto()
    TIKTOKEN = auto()
    REGEX = auto()

@dataclass
class ModelConfig:
    """Configuration for a language model"""
    provider: ModelProvider
    model_name: str
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 40
    repetition_penalty: float = 1.1
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    context_window: int = 4096
    tokenizer_type: TokenizerType = TokenizerType.REGEX
    threads: int = max(1, (os.cpu_count() or 4) - 1)
    device: str = "cpu"
    stop_sequences: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate configuration and set defaults"""
        # Validate temperature
        if not 0.0 <= self.temperature <= 2.0:
            logger.warning(f"Temperature {self.temperature} outside normal range [0.0, 2.0]. Clamping.")
            self.temperature = max(0.0, min(2.0, self.temperature))
        
        # Validate probabilities
        if not 0.0 <= self.top_p <= 1.0:
            logger.warning(f"Top-p {self.top_p} outside valid range [0.0, 1.0]. Clamping.")
            self.top_p = max(0.0, min(1.0, self.top_p))
        
        # Check required fields based on provider
        if self.provider in (ModelProvider.OPENAI, ModelProvider.ANTHROPIC) and not self.api_key:
            # Try to get key from environment variables
            env_var = f"{self.provider.name}_API_KEY"
            self.api_key = os.environ.get(env_var)
            if not self.api_key:
                logger.warning(f"No API key provided for {self.provider.name} and none found in {env_var} environment variable")
        
        # Set API base URLs if not provided
        if self.provider == ModelProvider.OPENAI and not self.api_base:
            self.api_base = "https://api.openai.com/v1"
        elif self.provider == ModelProvider.ANTHROPIC and not self.api_base:
            self.api_base = "https://api.anthropic.com/v1"
        elif self.provider == ModelProvider.OLLAMA and not self.api_base:
            self.api_base = "http://localhost:11434/api"
        elif self.provider == ModelProvider.LOCAL_LLAMACPP and not self.api_base:
            self.api_base = "http://localhost:8080"

        # Auto-detect best tokenizer
        if self.tokenizer_type == TokenizerType.REGEX:
            if HAS_TRANSFORMERS and self.provider in (ModelProvider.LOCAL_TORCH, ModelProvider.LOCAL_LLAMACPP):
                self.tokenizer_type = TokenizerType.TRANSFORMERS
            elif HAS_TIKTOKEN and self.provider in (ModelProvider.OPENAI, ModelProvider.ANTHROPIC):
                self.tokenizer_type = TokenizerType.TIKTOKEN

@dataclass
class ChunkingConfig:
    """Configuration for text chunking"""
    max_chunk_size: int = 4000
    overlap_size: int = 500
    separator: str = "\n"
    preserve_paragraphs: bool = True

@dataclass
class CacheConfig:
    """Configuration for response caching"""
    enabled: bool = True
    cache_dir: str = DEFAULT_CACHE_DIR
    ttl_seconds: int = 7 * 24 * 60 * 60  # 1 week
    max_cache_size_mb: int = 1024  # 1 GB
    compression: bool = True

@dataclass
class UnifiedLLMConfig:
    """Configuration for the UnifiedLLM class"""
    model: ModelConfig
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    retry_attempts: int = 3
    retry_delay: float = 2.0
    max_retry_delay: float = 60.0
    request_timeout: float = 120.0
    verbose_logging: bool = False
    
    def __post_init__(self):
        """Initialize the configuration"""
        # Create cache directory if it doesn't exist and caching is enabled
        if self.cache.enabled:
            os.makedirs(self.cache.cache_dir, exist_ok=True)

@dataclass
class CompletionResult:
    """Result of a completion request"""
    text: str
    tokens_used: int
    finish_reason: Optional[str] = None
    model_name: Optional[str] = None
    cached: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    generation_time: float = 0.0
    
    def __str__(self) -> str:
        return self.text
    
    def __repr__(self) -> str:
        return f"CompletionResult(text='{self.text[:30]}{'...' if len(self.text) > 30 else ''}', tokens={self.tokens_used}, cached={self.cached})"

@dataclass
class Message:
    """A message in a conversation"""
    role: str  # 'system', 'user', 'assistant'
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to a dictionary for API requests"""
        return {"role": self.role, "content": self.content}

# ===== Tokenization =====

class TokenCounter:
    """Count tokens for different models"""
    
    def __init__(self, config: ModelConfig):
        """Initialize the token counter"""
        self.config = config
        self.tokenizer = None
        
        # Initialize appropriate tokenizer
        if config.tokenizer_type == TokenizerType.TRANSFORMERS and HAS_TRANSFORMERS:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
                # Add padding token if it doesn't exist
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                logger.info(f"Initialized transformers tokenizer for {config.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize transformers tokenizer: {e}")
                self.tokenizer = None
                config.tokenizer_type = TokenizerType.REGEX
        
        elif config.tokenizer_type == TokenizerType.TIKTOKEN and HAS_TIKTOKEN:
            try:
                # Map model names to encoding names
                model_to_encoding = {
                    "gpt-4": "cl100k_base",
                    "gpt-3.5-turbo": "cl100k_base",
                    "text-davinci-003": "p50k_base",
                    "claude-2": "cl100k_base",  # Approximation
                    "claude-instant": "cl100k_base",  # Approximation
                }
                
                encoding_name = model_to_encoding.get(config.model_name, "cl100k_base")
                
                try:
                    self.tokenizer = tiktoken.encoding_for_model(config.model_name)
                except KeyError:
                    self.tokenizer = tiktoken.get_encoding(encoding_name)
                
                logger.info(f"Initialized tiktoken tokenizer for {config.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken tokenizer: {e}")
                self.tokenizer = None
                config.tokenizer_type = TokenizerType.REGEX
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in a piece of text"""
        if not text:
            return 0
        
        if self.config.tokenizer_type == TokenizerType.TRANSFORMERS and self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Error counting tokens with transformers: {e}")
        
        elif self.config.tokenizer_type == TokenizerType.TIKTOKEN and self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Error counting tokens with tiktoken: {e}")
        
        # Fallback to regex-based approximation
        # This is a simple approximation and will not be accurate for all models
        words = text.split()
        num_words = len(words)
        
        # Average tokens per word varies by language and model
        # 1.3 is a reasonable approximation for English
        return int(num_words * 1.3)
    
    def count_messages_tokens(self, messages: List[Message]) -> int:
        """Count tokens in a list of messages"""
        total = 0
        
        for message in messages:
            # Add overhead for message format (role, metadata)
            # Different models have different overhead, but 4 is a reasonable approximation
            total += 4
            
            # Add content tokens
            total += self.count_tokens(message.content)
        
        # Add overhead for completion format
        total += 2
        
        return total

class TextChunker:
    """Split text into overlapping chunks for processing large documents"""
    
    def __init__(self, config: ChunkingConfig, token_counter: TokenCounter):
        """Initialize the text chunker"""
        self.config = config
        self.token_counter = token_counter
    
    def split_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if not text:
            return []
        
        # Estimate if chunking is needed
        if self.token_counter.count_tokens(text) <= self.config.max_chunk_size:
            return [text]
        
        chunks = []
        lines = text.split(self.config.separator)
        
        current_chunk = []
        current_token_count = 0
        
        for line in lines:
            line_token_count = self.token_counter.count_tokens(line)
            
            # If adding this line would exceed the max chunk size, finalize the chunk
            if current_token_count + line_token_count > self.config.max_chunk_size and current_chunk:
                chunks.append(self.config.separator.join(current_chunk))
                
                # Calculate overlap lines
                overlap_token_count = 0
                overlap_lines = []
                
                # Start from the end and work backwards until we reach desired overlap
                for prev_line in reversed(current_chunk):
                    prev_line_tokens = self.token_counter.count_tokens(prev_line)
                    
                    if overlap_token_count + prev_line_tokens > self.config.overlap_size:
                        break
                    
                    overlap_lines.insert(0, prev_line)
                    overlap_token_count += prev_line_tokens
                
                # Start new chunk with overlap
                current_chunk = overlap_lines
                current_token_count = overlap_token_count
            
            # Add the current line
            current_chunk.append(line)
            current_token_count += line_token_count
        
        # Add the last chunk if not empty
        if current_chunk:
            chunks.append(self.config.separator.join(current_chunk))
        
        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

# ===== Caching =====

class ResponseCache:
    """Cache LLM responses to avoid redundant API calls"""
    
    def __init__(self, config: CacheConfig):
        """Initialize the cache"""
        self.config = config
        
        if config.enabled:
            os.makedirs(config.cache_dir, exist_ok=True)
            
            # Perform cache cleanup if necessary
            if self._get_cache_size() > config.max_cache_size_mb * 1024 * 1024:
                self._cleanup_cache()
    
    def _get_cache_key(self, model_name: str, prompt: str, settings: Dict[str, Any]) -> str:
        """Generate a cache key for a prompt and settings"""
        # Create a deterministic representation of settings
        settings_str = json.dumps(settings, sort_keys=True)
        combined = f"{model_name}:{prompt}:{settings_str}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key"""
        return Path(self.config.cache_dir) / f"{cache_key}.json"
    
    def _get_cache_size(self) -> int:
        """Get the total size of the cache in bytes"""
        total_size = 0
        for entry in os.scandir(self.config.cache_dir):
            if entry.is_file() and entry.name.endswith('.json'):
                total_size += entry.stat().st_size
        return total_size
    
    def _cleanup_cache(self) -> None:
        """Remove oldest cache entries to stay under max size"""
        logger.info("Performing cache cleanup")
        
        # Get all cache files with their modification times
        cache_files = []
        for entry in os.scandir(self.config.cache_dir):
            if entry.is_file() and entry.name.endswith('.json'):
                cache_files.append((entry.path, entry.stat().st_mtime))
        
        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x[1])
        
        # Remove files until we're under the limit
        current_size = self._get_cache_size()
        target_size = self.config.max_cache_size_mb * 1024 * 1024 * 0.8  # Target 80% of max
        
        for file_path, _ in cache_files:
            if current_size <= target_size:
                break
            
            try:
                file_size = os.path.getsize(file_path)
                os.unlink(file_path)
                current_size -= file_size
                logger.debug(f"Removed cache file: {file_path}")
            except OSError as e:
                logger.warning(f"Error removing cache file {file_path}: {e}")
    
    def get(self, model_name: str, prompt: str, settings: Dict[str, Any]) -> Optional[CompletionResult]:
        """Retrieve a cached response"""
        if not self.config.enabled:
            return None
        
        cache_key = self._get_cache_key(model_name, prompt, settings)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
        
        # Check TTL
        if self.config.ttl_seconds > 0:
            mtime = cache_path.stat().st_mtime
            if time.time() - mtime > self.config.ttl_seconds:
                try:
                    os.unlink(cache_path)
                    return None
                except OSError:
                    pass  # Ignore errors during cleanup
        
        # Read cache file
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            result = CompletionResult(
                text=data["text"],
                tokens_used=data["tokens_used"],
                finish_reason=data.get("finish_reason"),
                model_name=data.get("model_name"),
                cached=True,
                metadata=data.get("metadata", {}),
                generation_time=data.get("generation_time", 0.0)
            )
            return result
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Error reading cache file {cache_path}: {e}")
            return None
    
    def put(self, model_name: str, prompt: str, settings: Dict[str, Any], result: CompletionResult) -> None:
        """Store a response in the cache"""
        if not self.config.enabled:
            return
        
        cache_key = self._get_cache_key(model_name, prompt, settings)
        cache_path = self._get_cache_path(cache_key)
        
        data = {
            "text": result.text,
            "tokens_used": result.tokens_used,
            "finish_reason": result.finish_reason,
            "model_name": result.model_name or model_name,
            "metadata": result.metadata,
            "generation_time": result.generation_time,
            "cached_at": time.time()
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f)
        except OSError as e:
            logger.warning(f"Error writing to cache file {cache_path}: {e}")

# ===== API Clients =====

class LlamaClientWrapper:
    """Client for interacting with llama.cpp local inference server"""
    
    def __init__(self, config: ModelConfig):
        """Initialize the llama.cpp client"""
        self.config = config
        self.api_base = config.api_base or "http://localhost:8080"
        
        # Verify server is running
        self._server_running = self._check_server()
        if not self._server_running:
            logger.warning("llama.cpp server not running")
    
    def _check_server(self) -> bool:
        """Check if llama.cpp server is running"""
        if not HAS_REQUESTS:
            return False
        
        try:
            response = requests.get(f"{self.api_base}/health", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def ensure_server_running(self, model_path: Optional[str] = None) -> bool:
        """Ensure llama.cpp server is running, start it if needed"""
        if self._server_running:
            return True
        
        if not model_path:
            logger.error("Cannot start llama.cpp server without model path")
            return False
        
        # Look for llama-server executable
        server_paths = [
            "llama-server",
            "server",
            os.path.expanduser("~/.local/bin/llama-server"),
            os.path.expanduser("~/.local/bin/server"),
            "/usr/local/bin/llama-server",
            "/usr/local/bin/server"
        ]
        
        server_path = None
        for path in server_paths:
            try:
                subprocess.run([path, "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1)
                server_path = path
                break
            except (subprocess.SubprocessError, FileNotFoundError, OSError):
                continue
        
        if not server_path:
            logger.error("llama-server executable not found")
            return False
        
        # Parse the API base URL to get host and port
        import urllib.parse
        parsed_url = urllib.parse.urlparse(self.api_base)
        host = parsed_url.hostname or "127.0.0.1"
        port = parsed_url.port or 8080
        
        # Start server
        cmd = [
            server_path,
            "-m", model_path,
            "--host", host,
            "--port", str(port),
            "--threads", str(self.config.threads),
            "-c", str(self.config.context_window),
            "--batch-size", "512"
        ]
        
        try:
            logger.info(f"Starting llama.cpp server: {' '.join(cmd)}")
            server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start
            for _ in range(30):  # 30 second timeout
                time.sleep(1)
                if self._check_server():
                    self._server_running = True
                    logger.info("llama.cpp server started successfully")
                    return True
                
                # Check if process has terminated
                if server_process.poll() is not None:
                    stdout, stderr = server_process.communicate()
                    logger.error(f"Server failed to start: {stderr}")
                    return False
            
            logger.error("Timed out waiting for llama.cpp server to start")
            return False
        
        except Exception as e:
            logger.error(f"Error starting llama.cpp server: {e}")
            return False
    
    def generate_completion(self, prompt: str, settings: Dict[str, Any]) -> CompletionResult:
        """Generate a completion using the llama.cpp API"""
        if not HAS_REQUESTS:
            raise RuntimeError("Requests library required for API calls")
        
        if not self._server_running and not self._check_server():
            raise RuntimeError("llama.cpp server not running")
        
        # Prepare request data
        request_data = {
            "prompt": prompt,
            "n_predict": settings.get("max_tokens", self.config.max_tokens),
            "temperature": settings.get("temperature", self.config.temperature),
            "top_p": settings.get("top_p", self.config.top_p),
            "top_k": settings.get("top_k", self.config.top_k),
            "repeat_penalty": settings.get("repetition_penalty", self.config.repetition_penalty),
            "stop": settings.get("stop_sequences", self.config.stop_sequences),
            "stream": False,
            "n_threads": settings.get("threads", self.config.threads)
        }
        
        try:
            # Make request
            start_time = time.time()
            response = requests.post(
                f"{self.api_base}/completion",
                json=request_data,
                timeout=settings.get("timeout", 120)
            )
            response.raise_for_status()
            end_time = time.time()
            
            data = response.json()
            
            # Parse response
            result = CompletionResult(
                text=data.get("content", ""),
                tokens_used=data.get("tokens_used", 0),  # llama.cpp may not provide this
                finish_reason=data.get("stop_reason", "length"),
                model_name=data.get("model", self.config.model_name),
                cached=False,
                metadata={},
                generation_time=end_time - start_time
            )
            
            # Estimate tokens if not provided
            if result.tokens_used == 0:
                result.tokens_used = len(data.get("tokens", []))
            
            return result
        
        except requests.RequestException as e:
            raise RuntimeError(f"Error calling llama.cpp API: {e}")

class OllamaClientWrapper:
    """Client for interacting with Ollama models"""
    
    def __init__(self, config: ModelConfig):
        """Initialize the Ollama client"""
        self.config = config
        self.api_base = config.api_base or "http://localhost:11434/api"
    
    def _check_server(self) -> bool:
        """Check if Ollama server is running"""
        if not HAS_REQUESTS:
            return False
        
        try:
            response = requests.get(f"{self.api_base.rstrip('/api')}/", timeout=2)
            return response.status_code == 200
        except Exception:
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available Ollama models"""
        if not HAS_REQUESTS:
            return []
        
        try:
            response = requests.get(f"{self.api_base}/tags", timeout=5)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            logger.warning(f"Error listing Ollama models: {e}")
            return []
    
    def generate_completion(self, prompt: str, settings: Dict[str, Any]) -> CompletionResult:
        """Generate a completion using the Ollama API"""
        if not HAS_REQUESTS:
            raise RuntimeError("Requests library required for API calls")
        
        # Check if server is running
        if not self._check_server():
            raise RuntimeError("Ollama server not running")
        
        # Prepare request data
        request_data = {
            "model": self.config.model_name,
            "prompt": prompt,
            "options": {
                "temperature": settings.get("temperature", self.config.temperature),
                "top_p": settings.get("top_p", self.config.top_p),
                "top_k": settings.get("top_k", self.config.top_k),
                "repeat_penalty": settings.get("repetition_penalty", self.config.repetition_penalty),
                "num_predict": settings.get("max_tokens", self.config.max_tokens),
                "stop": settings.get("stop_sequences", self.config.stop_sequences)
            }
        }
        
        try:
            # Make request
            start_time = time.time()
            response = requests.post(
                f"{self.api_base}/chat",
                json=request_data,
                timeout=settings.get("timeout", 120)
            )
            response.raise_for_status()
            end_time = time.time()
            
            data = response.json()
            
            # Parse response
            result = CompletionResult(
                text=data.get("message", {}).get("content", ""),
                tokens_used=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                finish_reason="stop" if data.get("done", False) else "length",
                model_name=self.config.model_name,
                cached=False,
                metadata={
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0)
                },
                generation_time=end_time - start_time
            )
            
            return result
        
        except requests.RequestException as e:
            raise RuntimeError(f"Error calling Ollama API: {e}")

class OpenAIClientWrapper:
    """Client for interacting with OpenAI API models"""
    
    def __init__(self, config: ModelConfig):
        """Initialize the OpenAI client"""
        self.config = config
        self.api_base = config.api_base or "https://api.openai.com/v1"
        self.api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.warning("No OpenAI API key provided")
    
    def generate_chat_completion(self, messages: List[Message], settings: Dict[str, Any]) -> CompletionResult:
        """Generate a chat completion using the OpenAI API"""
        if not HAS_REQUESTS:
            raise RuntimeError("Requests library required for API calls")
        
        if not self.api_key:
            raise RuntimeError("OpenAI API key required")
        
        # Prepare request data
        request_data = {
            "model": self.config.model_name,
            "messages": [message.to_dict() for message in messages],
            "temperature": settings.get("temperature", self.config.temperature),
            "top_p": settings.get("top_p", self.config.top_p),
            "max_tokens": settings.get("max_tokens", self.config.max_tokens),
            "n": 1,
            "stream": False
        }
        
        # Add stop sequences if provided
        stop_sequences = settings.get("stop_sequences", self.config.stop_sequences)
        if stop_sequences:
            request_data["stop"] = stop_sequences
        
        # Set headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            # Make request
            start_time = time.time()
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=request_data,
                timeout=settings.get("timeout", 120)
            )
            response.raise_for_status()
            end_time = time.time()
            
            data = response.json()
            
            if "choices" not in data or len(data["choices"]) == 0:
                raise RuntimeError("Invalid response from OpenAI API")
            
            # Parse response
            choice = data["choices"][0]
            message = choice.get("message", {})
            
            result = CompletionResult(
                text=message.get("content", ""),
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                finish_reason=choice.get("finish_reason"),
                model_name=data.get("model", self.config.model_name),
                cached=False,
                metadata={
                    "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("completion_tokens", 0)
                },
                generation_time=end_time - start_time
            )
            
            return result
        
        except requests.RequestException as e:
            raise RuntimeError(f"Error calling OpenAI API: {e}")

class AnthropicClientWrapper:
    """Client for interacting with Anthropic API models (Claude)"""
    
    def __init__(self, config: ModelConfig):
        """Initialize the Anthropic client"""
        self.config = config
        self.api_base = config.api_base or "https://api.anthropic.com/v1"
        self.api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            logger.warning("No Anthropic API key provided")
    
    def generate_chat_completion(self, messages: List[Message], settings: Dict[str, Any]) -> CompletionResult:
        """Generate a chat completion using the Anthropic API"""
        if not HAS_REQUESTS:
            raise RuntimeError("Requests library required for API calls")
        
        if not self.api_key:
            raise RuntimeError("Anthropic API key required")
        
        # Convert messages to Anthropic format
        anthropic_messages = []
        for message in messages:
            if message.role == "system":
                # Handle system message specially
                system_content = message.content
                continue
            
            # Map roles
            role = "assistant" if message.role == "assistant" else "user"
            anthropic_messages.append({"role": role, "content": message.content})
        
        # Prepare request data
        request_data = {
            "model": self.config.model_name,
            "messages": anthropic_messages,
            "temperature": settings.get("temperature", self.config.temperature),
            "top_p": settings.get("top_p", self.config.top_p),
            "max_tokens": settings.get("max_tokens", self.config.max_tokens)
        }
        
        # Add system prompt if present
        if system_content:
            request_data["system"] = system_content
        
        # Add stop sequences if provided
        stop_sequences = settings.get("stop_sequences", self.config.stop_sequences)
        if stop_sequences:
            request_data["stop_sequences"] = stop_sequences
        
        # Set headers
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        try:
            # Make request
            start_time = time.time()
            response = requests.post(
                f"{self.api_base}/messages",
                headers=headers,
                json=request_data,
                timeout=settings.get("timeout", 120)
            )
            response.raise_for_status()
            end_time = time.time()
            
            data = response.json()
            
            if "content" not in data or len(data["content"]) == 0:
                raise RuntimeError("Invalid response from Anthropic API")
            
            # Parse response
            content_blocks = data["content"]
            text_blocks = [block["text"] for block in content_blocks if block["type"] == "text"]
            text = "".join(text_blocks)
            
            result = CompletionResult(
                text=text,
                tokens_used=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                finish_reason=data.get("stop_reason"),
                model_name=data.get("model", self.config.model_name),
                cached=False,
                metadata={
                    "input_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": data.get("usage", {}).get("output_tokens", 0)
                },
                generation_time=end_time - start_time
            )
            
            return result
        
        except requests.RequestException as e:
            raise RuntimeError(f"Error calling Anthropic API: {e}")

# ===== LLM Models =====

class TorchModelWrapper:
    """Wrapper for PyTorch transformer models"""
    
    def __init__(self, config: ModelConfig):
        """Initialize the PyTorch model"""
        self.config = config
        self.model = None
        self.tokenizer = None
        
        if not HAS_TORCH:
            raise RuntimeError("PyTorch not available")
        
        if not HAS_TRANSFORMERS:
            raise RuntimeError("transformers library not available")
    
    def load_model(self) -> bool:
        """Load the model and tokenizer"""
        if self.model and self.tokenizer:
            return True
        
        try:
            logger.info(f"Loading transformer model: {self.config.model_name}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Determine torch data type
            if torch.cuda.is_available() and self.config.device == "cuda":
                dtype = torch.float16
                device = "cuda"
            else:
                dtype = torch.float32
                device = "cpu"
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype=dtype,
                device_map=device
            )
            
            self.model.eval()
            logger.info(f"Model {self.config.model_name} loaded successfully on {device}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load model {self.config.model_name}: {e}")
            self.model = None
            self.tokenizer = None
            return False
    
    def generate_completion(self, prompt: str, settings: Dict[str, Any]) -> CompletionResult:
        """Generate a completion using the local PyTorch model"""
        if not self.load_model():
            raise RuntimeError("Failed to load model")
        
        # Get settings
        max_tokens = settings.get("max_tokens", self.config.max_tokens)
        temperature = settings.get("temperature", self.config.temperature)
        top_p = settings.get("top_p", self.config.top_p)
        top_k = settings.get("top_k", self.config.top_k)
        repetition_penalty = settings.get("repetition_penalty", self.config.repetition_penalty)
        
        try:
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=self.config.context_window)
            input_ids = inputs["input_ids"].to(self.model.device)
            
            # Generate
            start_time = time.time()
            with torch.no_grad():
                output_sequences = self.model.generate(
                    input_ids=input_ids,
                    max_length=max_tokens + len(input_ids[0]),
                    num_return_sequences=1,
                    do_sample=temperature > 0.0,
                    top_k=top_k,
                    top_p=top_p,
                    temperature=max(0.1, temperature),  # Avoid 0 temperature
                    repetition_penalty=repetition_penalty,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            end_time = time.time()
            
            # Decode output
            response_text = self.tokenizer.decode(output_sequences[0][len(input_ids[0]):], skip_special_tokens=True)
            
            return CompletionResult(
                text=response_text.strip(),
                tokens_used=len(input_ids[0]) + len(output_sequences[0]) - len(input_ids[0]),
                finish_reason="length",  # No better way to determine this
                model_name=self.config.model_name,
                cached=False,
                metadata={},
                generation_time=end_time - start_time
            )
        
        except Exception as e:
            logger.error(f"Error generating text with PyTorch model: {e}")
            raise RuntimeError(f"Error generating text: {e}")

# ===== Main Unified LLM Class =====

class UnifiedLLM:
    """Unified interface for interacting with language models"""
    
    def __init__(self, config: UnifiedLLMConfig):
        """Initialize the LLM interface"""
        self.config = config
        self.token_counter = TokenCounter(config.model)
        self.chunker = TextChunker(config.chunking, self.token_counter)
        self.cache = ResponseCache(config.cache)
        self.model_client = self._create_model_client()
    
    def _create_model_client(self):
        """Create the appropriate client for the model provider"""
        provider = self.config.model.provider
        
        if provider == ModelProvider.LOCAL_TORCH:
            if not HAS_TORCH or not HAS_TRANSFORMERS:
                raise RuntimeError("PyTorch and transformers required for LOCAL_TORCH provider")
            return TorchModelWrapper(self.config.model)
        
        elif provider == ModelProvider.LOCAL_LLAMACPP:
            return LlamaClientWrapper(self.config.model)
        
        elif provider == ModelProvider.OLLAMA:
            return OllamaClientWrapper(self.config.model)
        
        elif provider == ModelProvider.OPENAI:
            return OpenAIClientWrapper(self.config.model)
        
        elif provider == ModelProvider.ANTHROPIC:
            return AnthropicClientWrapper(self.config.model)
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _apply_retry(self, func):
        """Apply retry logic to a function"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            delay = self.config.retry_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retry_count += 1
                    if retry_count > self.config.retry_attempts:
                        logger.error(f"Maximum retry attempts ({self.config.retry_attempts}) exceeded")
                        raise
                    
                    logger.warning(f"Attempt {retry_count}/{self.config.retry_attempts} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    
                    # Exponential backoff with jitter
                    delay = min(delay * 1.5 + random.uniform(0, 1), self.config.max_retry_delay)
        
        return wrapper
    
    def complete(self, prompt: str, **kwargs) -> CompletionResult:
        """Generate a completion for a prompt"""
        # Prepare settings
        settings = {
            "max_tokens": kwargs.get("max_tokens", self.config.model.max_tokens),
            "temperature": kwargs.get("temperature", self.config.model.temperature),
            "top_p": kwargs.get("top_p", self.config.model.top_p),
            "top_k": kwargs.get("top_k", self.config.model.top_k),
            "repetition_penalty": kwargs.get("repetition_penalty", self.config.model.repetition_penalty),
            "stop_sequences": kwargs.get("stop_sequences", self.config.model.stop_sequences),
            "timeout": kwargs.get("timeout", self.config.request_timeout)
        }
        
        # Check if a cached response exists
        cached_result = self.cache.get(self.config.model.model_name, prompt, settings)
        if cached_result:
            if self.config.verbose_logging:
                logger.info("Using cached response")
            return cached_result
        
        # Count prompt tokens
        prompt_tokens = self.token_counter.count_tokens(prompt)
        
        if self.config.verbose_logging:
            logger.info(f"Prompt tokens: {prompt_tokens}")
        
        # Generate completion with retry
        generate_with_retry = self._apply_retry(self._generate_completion)
        result = generate_with_retry(prompt, settings)
        
        # Cache the result
        self.cache.put(self.config.model.model_name, prompt, settings, result)
        
        return result
    
    def _generate_completion(self, prompt: str, settings: Dict[str, Any]) -> CompletionResult:
        """Generate a completion with the appropriate client"""
        provider = self.config.model.provider
        
        if provider == ModelProvider.LOCAL_TORCH:
            return self.model_client.generate_completion(prompt, settings)
        
        elif provider == ModelProvider.LOCAL_LLAMACPP:
            return self.model_client.generate_completion(prompt, settings)
        
        elif provider == ModelProvider.OLLAMA:
            return self.model_client.generate_completion(prompt, settings)
        
        elif provider in (ModelProvider.OPENAI, ModelProvider.ANTHROPIC):
            # Convert to chat format for these providers
            messages = [
                Message(role="user", content=prompt)
            ]
            return self.chat_complete(messages, **settings)
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def chat_complete(self, messages: List[Message], **kwargs) -> CompletionResult:
        """Generate a chat completion for a list of messages"""
        # Prepare settings
        settings = {
            "max_tokens": kwargs.get("max_tokens", self.config.model.max_tokens),
            "temperature": kwargs.get("temperature", self.config.model.temperature),
            "top_p": kwargs.get("top_p", self.config.model.top_p),
            "top_k": kwargs.get("top_k", self.config.model.top_k),
            "repetition_penalty": kwargs.get("repetition_penalty", self.config.model.repetition_penalty),
            "stop_sequences": kwargs.get("stop_sequences", self.config.model.stop_sequences),
            "timeout": kwargs.get("timeout", self.config.request_timeout)
        }
        
        # Serialize messages for cache key
        messages_str = json.dumps([msg.to_dict() for msg in messages])
        
        # Check if a cached response exists
        cached_result = self.cache.get(self.config.model.model_name, messages_str, settings)
        if cached_result:
            if self.config.verbose_logging:
                logger.info("Using cached response")
            return cached_result
        
        # Count tokens
        total_tokens = self.token_counter.count_messages_tokens(messages)
        
        if self.config.verbose_logging:
            logger.info(f"Messages tokens: {total_tokens}")
        
        # Generate completion with retry
        generate_with_retry = self._apply_retry(self._generate_chat_completion)
        result = generate_with_retry(messages, settings)
        
        # Cache the result
        self.cache.put(self.config.model.model_name, messages_str, settings, result)
        
        return result
    
    def _generate_chat_completion(self, messages: List[Message], settings: Dict[str, Any]) -> CompletionResult:
        """Generate a chat completion with the appropriate client"""
        provider = self.config.model.provider
        
        if provider == ModelProvider.OLLAMA:
            return self.model_client.generate_chat_completion(messages, settings)
        
        elif provider == ModelProvider.OPENAI:
            return self.model_client.generate_chat_completion(messages, settings)
        
        elif provider == ModelProvider.ANTHROPIC:
            return self.model_client.generate_chat_completion(messages, settings)
        
        elif provider in (ModelProvider.LOCAL_TORCH, ModelProvider.LOCAL_LLAMACPP):
            # Format as a prompt for non-chat models
            formatted_prompt = self._format_messages_as_prompt(messages)
            return self._generate_completion(formatted_prompt, settings)
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _format_messages_as_prompt(self, messages: List[Message]) -> str:
        """Format a list of messages as a prompt for non-chat models"""
        formatted_parts = []
        
        for message in messages:
            if message.role == "system":
                formatted_parts.append(f"### System Instruction:\n{message.content}\n")
            elif message.role == "user":
                formatted_parts.append(f"### User:\n{message.content}\n")
            elif message.role == "assistant":
                formatted_parts.append(f"### Assistant:\n{message.content}\n")
        
        # Add prompt for assistant response
        if messages[-1].role != "assistant":
            formatted_parts.append("### Assistant:\n")
        
        return "\n".join(formatted_parts)
    
    def process_large_text(self, text: str, system_prompt: str, **kwargs) -> str:
        """Process a large text by splitting into chunks and sending to LLM"""
        # Split text into chunks
        chunks = self.chunker.split_into_chunks(text)
        
        if len(chunks) == 1:
            # Single chunk, just process normally
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=chunks[0])
            ]
            result = self.chat_complete(messages, **kwargs)
            return result.text
        
        # Process multiple chunks
        results = []
        
        for i, chunk in enumerate(chunks):
            # Modify system prompt for chunk context
            chunk_system_prompt = f"{system_prompt}\n\nThis is chunk {i+1} of {len(chunks)} from a larger text."
            
            # If not the first chunk, add a reminder about previous chunks
            if i > 0:
                chunk_system_prompt += "\nRemember to maintain continuity with previous chunks."
            
            # Create messages for this chunk
            messages = [
                Message(role="system", content=chunk_system_prompt),
                Message(role="user", content=chunk)
            ]
            
            # Process chunk
            logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            result = self.chat_complete(messages, **kwargs)
            results.append(result.text)
        
        # Combine results
        combined_text = "\n\n".join(results)
        
        # If the combined result is still large, summarize it
        if self.token_counter.count_tokens(combined_text) > self.config.chunking.max_chunk_size:
            logger.info("Combined results too large, generating summary")
            
            # Create a summary prompt
            summary_prompt = f"""
            {system_prompt}
            
            Below is a long text that was processed in chunks. Please provide a cohesive summary or response.
            
            {combined_text}
            """
            
            # Generate summary
            summary_result = self.complete(summary_prompt, **kwargs)
            return summary_result.text
        
        return combined_text

# ===== Utility Functions =====

def create_default_config() -> UnifiedLLMConfig:
    """Create a default configuration"""
    model_config = ModelConfig(
        provider=ModelProvider.LOCAL_LLAMACPP,
        model_name="mistral-7b-instruct-v0.2"
    )
    return UnifiedLLMConfig(model=model_config)

def find_llamacpp_model() -> Optional[Path]:
    """Find a local llama.cpp model"""
    search_paths = [
        Path.cwd(),
        Path.cwd() / "models",
        Path.home() / ".cache/kaleidoscope/models",
        Path.home() / ".cache/huggingface/hub"
    ]
    
    model_extensions = [".gguf"]
    
    for path in search_paths:
        if not path.exists() or not path.is_dir():
            continue
        
        # Search for model files
        for ext in model_extensions:
            model_files = list(path.glob(f"**/*{ext}"))
            if model_files:
                return model_files[0]
    
    return None

def download_llm_model(model_id: str, model_file: Optional[str] = None) -> Optional[Path]:
    """Download a model from Hugging Face Hub"""
    try:
        from huggingface_hub import hf_hub_download, list_repo_files
        
        # Create model directory
        model_dir = Path(DEFAULT_CACHE_DIR) / model_id.replace("/", "_")
        model_dir.mkdir(parents=True, exist_ok=True)
        
        if model_file:
            # Download specific file
            logger.info(f"Downloading {model_id}/{model_file}...")
            return Path(hf_hub_download(
                repo_id=model_id,
                filename=model_file,
                local_dir=model_dir,
                local_files_only=False
            ))
        else:
            # Try to find a suitable GGUF file
            logger.info(f"Looking for GGUF models in {model_id}...")
            files = list_repo_files(model_id)
            gguf_files = [f for f in files if f.endswith(".gguf")]
            
            if not gguf_files:
                logger.error(f"No GGUF files found in {model_id}")
                return None
            
            # Sort by size suffix (Q4_K_M is usually good balance)
            def model_priority(filename):
                if "Q4_K_M" in filename: return 0
                if "Q4_K" in filename: return 1
                if "Q5_K" in filename: return 2
                if "Q6_K" in filename: return 3
                if "Q8_0" in filename: return 4
                return 5
            
            gguf_files.sort(key=model_priority)
            model_file = gguf_files[0]
            
            logger.info(f"Downloading {model_id}/{model_file}...")
            return Path(hf_hub_download(
                repo_id=model_id,
                filename=model_file,
                local_dir=model_dir,
                local_files_only=False
            ))
    
    except ImportError:
        logger.error("huggingface_hub module required for downloading models")
        return None
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        return None

# ===== Command Line Interface =====

def create_cli_parser():
    """Create a command line argument parser"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified LLM Module")
    
    # Model configuration
    parser.add_argument("--provider", choices=[p.name for p in ModelProvider], default="LOCAL_LLAMACPP",
                        help="Model provider to use")
    parser.add_argument("--model", help="Model name or path")
    parser.add_argument("--api-key", help="API key (for OpenAI/Anthropic)")
    parser.add_argument("--api-base", help="API base URL")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=2048, help="Maximum tokens to generate")
    parser.add_argument("--context-window", type=int, default=4096, help="Context window size")
    
    # Chunking configuration
    parser.add_argument("--chunk-size", type=int, default=4000, help="Maximum chunk size in tokens")
    parser.add_argument("--overlap-size", type=int, default=500, help="Overlap size in tokens")
    
    # Caching configuration
    parser.add_argument("--cache-dir", help="Cache directory")
    parser.add_argument("--disable-cache", action="store_true", help="Disable caching")
    
    # Input/output options
    parser.add_argument("--prompt", help="Prompt string")
    parser.add_argument("--prompt-file", help="Prompt file")
    parser.add_argument("--output-file", help="Output file")
    parser.add_argument("--system-prompt", help="System prompt for chat mode")
    parser.add_argument("--chat-mode", action="store_true", help="Use chat mode")
    
    # Utility options
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--download", help="Download model (e.g. TheBloke/Mistral-7B-Instruct-v0.2-GGUF)")
    parser.add_argument("--download-file", help="Specific file to download")
    
    return parser

def main():
    """Command line interface entry point"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # Handle model download
    if args.download:
        model_path = download_llm_model(args.download, args.download_file)
        if model_path:
            logger.info(f"Model downloaded to: {model_path}")
        else:
            logger.error("Failed to download model")
        return
    
    # Create model config
    provider = ModelProvider[args.provider]
    model_name = args.model
    
    # Auto-detect model if not specified
    if not model_name:
        if provider == ModelProvider.LOCAL_LLAMACPP:
            model_path = find_llamacpp_model()
            if model_path:
                model_name = str(model_path)
                logger.info(f"Using model: {model_name}")
            else:
                logger.error("No llama.cpp model found. Specify with --model or download with --download")
                return
        else:
            logger.error("Model name required for provider: {provider}")
            return
    
    model_config = ModelConfig(
        provider=provider,
        model_name=model_name,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        context_window=args.context_window,
        api_key=args.api_key,
        api_base=args.api_base
    )
    
    # Create chunking config
    chunking_config = ChunkingConfig(
        max_chunk_size=args.chunk_size,
        overlap_size=args.overlap_size
    )
    
    # Create cache config
    cache_config = CacheConfig(
        enabled=not args.disable_cache,
        cache_dir=args.cache_dir or DEFAULT_CACHE_DIR
    )
    
    # Create main config
    config = UnifiedLLMConfig(
        model=model_config,
        chunking=chunking_config,
        cache=cache_config,
        verbose_logging=args.verbose
    )
    
    # Create LLM
    llm = UnifiedLLM(config)
    
    # Get prompt
    prompt = None
    if args.prompt:
        prompt = args.prompt
    elif args.prompt_file:
        with open(args.prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read()
    else:
        # Interactive mode
        print("Enter prompt (Ctrl+D or Ctrl+Z on a blank line to end):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            prompt = "\n".join(lines)
    
    if not prompt:
        logger.error("No prompt provided")
        return
    
    # Generate completion
    try:
        if args.chat_mode:
            # Chat mode
            system_prompt = args.system_prompt or "You are a helpful assistant."
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=prompt)
            ]
            result = llm.chat_complete(messages)
        else:
            # Completion mode
            result = llm.complete(prompt)
        
        # Output result
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(result.text)
            print(f"Output written to {args.output_file}")
        else:
            print("\n--- Response ---")
            print(result.text)
            print(f"\nTokens used: {result.tokens_used}, Generation time: {result.generation_time:.2f}s")
    
    except Exception as e:
        logger.error(f"Error generating completion: {e}")

if __name__ == "__main__":
    main()_sequences", self.config.stop_sequences)
            }
        }
        
        try:
            # Make request
            start_time = time.time()
            response = requests.post(
                f"{self.api_base}/generate",
                json=request_data,
                timeout=settings.get("timeout", 120)
            )
            response.raise_for_status()
            end_time = time.time()
            
            data = response.json()
            
            # Parse response
            result = CompletionResult(
                text=data.get("response", ""),
                tokens_used=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                finish_reason="stop" if data.get("done", False) else "length",
                model_name=self.config.model_name,
                cached=False,
                metadata={
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                    "eval_count": data.get("eval_count", 0)
                },
                generation_time=end_time - start_time
            )
            
            return result
        
        except requests.RequestException as e:
            raise RuntimeError(f"Error calling Ollama API: {e}")
    
    def generate_chat_completion(self, messages: List[Message], settings: Dict[str, Any]) -> CompletionResult:
        """Generate a chat completion using the Ollama API"""
        if not HAS_REQUESTS:
            raise RuntimeError("Requests library required for API calls")
        
        # Check if server is running
        if not self._check_server():
            raise RuntimeError("Ollama server not running")
        
        # Prepare request data
        request_data = {
            "model": self.config.model_name,
            "messages": [message.to_dict() for message in messages],
            "options": {
                "temperature": settings.get("temperature", self.config.temperature),
                "top_p": settings.get("top_p", self.config.top_p),
                "top_k": settings.get("top_k", self.config.top_k),
                "repeat_penalty": settings.get("repetition_penalty", self.config.repetition_penalty),
                "num_predict": settings.get("max_tokens", self.config.max_tokens),
                "stop": settings.get("stop