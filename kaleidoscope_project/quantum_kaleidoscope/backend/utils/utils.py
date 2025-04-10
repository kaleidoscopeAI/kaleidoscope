#!/usr/bin/env python3
"""
Kaleidoscope AI - Utility Functions
==================================
Common utility functions for file handling, security, encoding/decoding,
and system management to support the Kaleidoscope AI platform.
"""

import os
import sys
import json
import yaml
import base64
import hashlib
import logging
import shutil
import tempfile
import tarfile
import zipfile
import uuid
import re
import platform
import subprocess
import threading
import asyncio
import time
from typing import Dict, List, Any, Optional, Union, Tuple, Set, Callable, TypeVar, Generic
from pathlib import Path
from datetime import datetime, timedelta
import urllib.request
import urllib.parse
import urllib.error
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("kaleidoscope_utils.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Activate virtual environment
VENV_ACTIVATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv/bin/activate")
if os.path.exists(VENV_ACTIVATE):
    activate_cmd = f"source {VENV_ACTIVATE}"
    os.system(activate_cmd)
    logger.info(f"Activated virtual environment from {VENV_ACTIVATE}")
else:
    logger.warning("Virtual environment not found, using system Python")

# Type variables for generics
T = TypeVar('T')

# Constants
FILE_CHUNK_SIZE = 1024 * 1024  # 1MB chunks for file operations
DEFAULT_TIMEOUT = 60  # Default timeout for network operations
MAX_RETRY_COUNT = 3  # Maximum retry count
RETRY_DELAY_BASE = 2  # Base for exponential backoff

class FileUtils:
    """Utilities for file operations"""
    
    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
        """
        Calculate hash of a file
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (md5, sha1, sha256, etc.)
            
        Returns:
            Hash string
        """
        hash_func = getattr(hashlib, algorithm)()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(FILE_CHUNK_SIZE), b''):
                hash_func.update(chunk)
                
        return hash_func.hexdigest()
    
    @staticmethod
    def create_temp_directory(prefix: str = "kaleidoscope_") -> str:
        """
        Create a temporary directory
        
        Args:
            prefix: Directory name prefix
            
        Returns:
            Path to the temporary directory
        """
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir
    
    @staticmethod
    def extract_archive(archive_path: str, output_dir: str) -> bool:
        """
        Extract an archive file
        
        Args:
            archive_path: Path to the archive file
            output_dir: Directory to extract to
            
        Returns:
            Success status
        """
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Determine archive type and extract
            if archive_path.endswith(('.tar.gz', '.tgz')):
                with tarfile.open(archive_path, 'r:gz') as tar:
                    tar.extractall(path=output_dir)
            elif archive_path.endswith('.tar'):
                with tarfile.open(archive_path, 'r') as tar:
                    tar.extractall(path=output_dir)
            elif archive_path.endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(output_dir)
            else:
                logger.error(f"Unsupported archive format: {archive_path}")
                return False
            
            logger.info(f"Extracted {archive_path} to {output_dir}")
            return True
        
        except Exception as e:
            logger.error(f"Error extracting archive {archive_path}: {str(e)}")
            return False
    
    @staticmethod
    def create_archive(directory: str, output_path: str, format: str = 'zip') -> bool:
        """
        Create an archive from a directory
        
        Args:
            directory: Directory to archive
            output_path: Path to the output archive file
            format: Archive format (zip, tar, tar.gz)
            
        Returns:
            Success status
        """
        try:
            if format == 'zip':
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(directory):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, directory)
                            zipf.write(file_path, arcname)
            
            elif format == 'tar':
                with tarfile.open(output_path, 'w') as tar:
                    tar.add(directory, arcname=os.path.basename(directory))
            
            elif format == 'tar.gz' or format == 'tgz':
                with tarfile.open(output_path, 'w:gz') as tar:
                    tar.add(directory, arcname=os.path.basename(directory))
            
            else:
                logger.error(f"Unsupported archive format: {format}")
                return False
            
            logger.info(f"Created {format} archive at {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error creating archive {output_path}: {str(e)}")
            return False
    
    @staticmethod
    def get_file_type(file_path: str) -> str:
        """
        Determine file type using magic numbers or file extension
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type string
        """
        # Try to use the 'file' command if available
        if platform.system() != "Windows":
            try:
                output = subprocess.check_output(['file', '--brief', '--mime-type', file_path], 
                                               stderr=subprocess.PIPE,
                                               universal_newlines=True)
                return output.strip()
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
        
        # Fall back to extension-based detection
        extension = os.path.splitext(file_path)[1].lower()
        
        # Map of extensions to MIME types
        extension_map = {
            '.txt': 'text/plain',
            '.py': 'text/x-python',
            '.js': 'application/javascript',
            '.html': 'text/html',
            '.css': 'text/css',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.exe': 'application/octet-stream',
            '.dll': 'application/octet-stream',
            '.so': 'application/octet-stream',
            '.zip': 'application/zip',
            '.tar': 'application/x-tar',
            '.gz': 'application/gzip',
            '.tgz': 'application/gzip',
            '.tar.gz': 'application/gzip'
        }
        
        return extension_map.get(extension, 'application/octet-stream')
    
    @staticmethod
    def is_binary_file(file_path: str) -> bool:
        """
        Check if a file is binary or text
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if binary, False if text
        """
        try:
            with open(file_path, 'r') as f:
                f.read(1024)
            return False  # If we can read it as text, it's a text file
        except UnicodeDecodeError:
            return True  # If we can't decode it as unicode, it's binary
    
    @staticmethod
    def safe_delete(path: str) -> bool:
        """
        Safely delete a file or directory
        
        Args:
            path: Path to delete
            
        Returns:
            Success status
        """
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            else:
                logger.warning(f"Path does not exist: {path}")
                return False
            
            logger.debug(f"Deleted: {path}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting {path}: {str(e)}")
            return False
    
    @staticmethod
    def ensure_directory(path: str) -> bool:
        """
        Ensure a directory exists, creating it if necessary
        
        Args:
            path: Directory path
            
        Returns:
            Success status
        """
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {path}: {str(e)}")
            return False
    
    @staticmethod
    def copy_file(src: str, dst: str, overwrite: bool = True) -> bool:
        """
        Copy a file
        
        Args:
            src: Source path
            dst: Destination path
            overwrite: Whether to overwrite existing files
            
        Returns:
            Success status
        """
        try:
            # Check if destination exists
            if os.path.exists(dst) and not overwrite:
                logger.warning(f"Destination file exists and overwrite is False: {dst}")
                return False
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            # Copy file
            shutil.copy2(src, dst)
            logger.debug(f"Copied {src} to {dst}")
            return True
        
        except Exception as e:
            logger.error(f"Error copying {src} to {dst}: {str(e)}")
            return False
    
    @staticmethod
    def move_file(src: str, dst: str, overwrite: bool = True) -> bool:
        """
        Move a file
        
        Args:
            src: Source path
            dst: Destination path
            overwrite: Whether to overwrite existing files
            
        Returns:
            Success status
        """
        try:
            # Check if destination exists
            if os.path.exists(dst) and not overwrite:
                logger.warning(f"Destination file exists and overwrite is False: {dst}")
                return False
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            # Move file
            shutil.move(src, dst)
            logger.debug(f"Moved {src} to {dst}")
            return True
        
        except Exception as e:
            logger.error(f"Error moving {src} to {dst}: {str(e)}")
            return False
    
    @staticmethod
    def list_files(directory: str, pattern: Optional[str] = None, recursive: bool = False) -> List[str]:
        """
        List files in a directory
        
        Args:
            directory: Directory to list
            pattern: Optional regex pattern to filter files
            recursive: Whether to search recursively
            
        Returns:
            List of file paths
        """
        result = []
        
        try:
            if recursive:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if pattern is None or re.search(pattern, file_path):
                            result.append(file_path)
            else:
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.isfile(item_path) and (pattern is None or re.search(pattern, item_path)):
                        result.append(item_path)
            
            return result
        
        except Exception as e:
            logger.error(f"Error listing files in {directory}: {str(e)}")
            return []

class SecurityUtils:
    """Utilities for security operations"""
    
    @staticmethod
    def generate_secure_random_string(length: int = 32) -> str:
        """
        Generate a secure random string
        
        Args:
            length: String length
            
        Returns:
            Random string
        """
        random_bytes = os.urandom(length)
        return base64.urlsafe_b64encode(random_bytes).decode('utf-8')[:length]
    
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash a password with a salt
        
        Args:
            password: Password to hash
            salt: Optional salt (generated if not provided)
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        if salt is None:
            salt = SecurityUtils.generate_secure_random_string(16)
        
        # Use PBKDF2 with HMAC-SHA256
        dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        hashed = base64.b64encode(dk).decode('utf-8')
        
        return hashed, salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        Verify a password against a hash
        
        Args:
            password: Password to verify
            hashed_password: Stored hashed password
            salt: Salt used for hashing
            
        Returns:
            True if password matches, False otherwise
        """
        calculated_hash, _ = SecurityUtils.hash_password(password, salt)
        return calculated_hash == hashed_password
    
    @staticmethod
    def encrypt_data(data: bytes, key: bytes) -> bytes:
        """
        Encrypt data using AES
        
        Args:
            data: Data to encrypt
            key: Encryption key
            
        Returns:
            Encrypted data
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            # Generate a random IV
            iv = os.urandom(16)
            
            # Create an encryptor
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Pad the data to a multiple of 16 bytes (AES block size)
            padded_data = data + (16 - len(data) % 16) * bytes([16 - len(data) % 16])
            
            # Encrypt the data
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Prepend the IV to the encrypted data
            return iv + encrypted_data
        
        except ImportError:
            logger.error("cryptography module not installed, using base64 encoding instead")
            return base64.b64encode(data)
    
    @staticmethod
    def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
        """
        Decrypt data using AES
        
        Args:
            encrypted_data: Data to decrypt
            key: Encryption key
            
        Returns:
            Decrypted data
        """
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            
            # Extract the IV (first 16 bytes)
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            # Create a decryptor
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt the data
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove padding
            padding_len = padded_data[-1]
            data = padded_data[:-padding_len]
            
            return data
        
        except ImportError:
            logger.error("cryptography module not installed, using base64 decoding instead")
            return base64.b64decode(encrypted_data)
    
    @staticmethod
    def generate_jwt(payload: Dict[str, Any], secret: str, expires_in: int = 3600) -> str:
        """
        Generate a JSON Web Token (JWT)
        
        Args:
            payload: Token payload
            secret: Secret key
            expires_in: Expiration time in seconds
            
        Returns:
            JWT token
        """
        try:
            import jwt
            
            # Add expiration time
            exp = int(time.time()) + expires_in
            payload['exp'] = exp
            
            # Generate token
            token = jwt.encode(payload, secret, algorithm='HS256')
            
            return token
        
        except ImportError:
            logger.error("PyJWT module not installed")
            raise ImportError("PyJWT module is required for JWT operations")
    
    @staticmethod
    def verify_jwt(token: str, secret: str) -> Optional[Dict[str, Any]]:
        """
        Verify a JSON Web Token (JWT)
        
        Args:
            token: JWT token
            secret: Secret key
            
        Returns:
            Token payload or None if invalid
        """
        try:
            import jwt
            
            # Verify token
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            
            return payload
        
        except jwt.PyJWTError as e:
            logger.error(f"JWT verification error: {str(e)}")
            return None
        
        except ImportError:
            logger.error("PyJWT module not installed")
            raise ImportError("PyJWT module is required for JWT operations")
    
    @staticmethod
    def scan_file_for_malware(file_path: str) -> bool:
        """
        Scan a file for malware (if ClamAV is available)
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if safe, False if malware detected or scan failed
        """
        try:
            # Check if ClamAV is available
            clamscan_path = shutil.which('clamscan')
            if not clamscan_path:
                logger.warning("ClamAV not found, skipping malware scan")
                return True
            
            # Run ClamAV scan
            result = subprocess.run(
                [clamscan_path, '-v', '--no-summary', file_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False
            )
            
            # Check return code (0: no virus, 1: virus found, >1: error)
            if result.returncode == 0:
                logger.info(f"No malware detected in {file_path}")
                return True
            elif result.returncode == 1:
                logger.warning(f"Malware detected in {file_path}")
                return False
            else:
                logger.error(f"Error scanning {file_path}: {result.stderr.decode()}")
                return False
        
        except Exception as e:
            logger.error(f"Error scanning file for malware: {str(e)}")
            return False

class NetworkUtils:
    """Utilities for network operations"""
    
    @staticmethod
    async def download_file(url: str, destination: str, timeout: int = DEFAULT_TIMEOUT, verify_ssl: bool = True) -> bool:
        """
        Download a file from a URL
        
        Args:
            url: URL to download from
            destination: Path to save the file
            timeout: Timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            
        Returns:
            Success status
        """
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # Setup SSL context
        ssl_context = ssl.create_default_context()
        if not verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create a download coroutine
        async def download_coroutine():
            try:
                with urllib.request.urlopen(url, timeout=timeout, context=ssl_context) as response:
                    with open(destination, 'wb') as out_file:
                        chunk = response.read(FILE_CHUNK_SIZE)
                        while chunk:
                            out_file.write(chunk)
                            chunk = response.read(FILE_CHUNK_SIZE)
                
                logger.info(f"Downloaded {url} to {destination}")
                return True
            
            except Exception as e:
                logger.error(f"Error downloading {url}: {str(e)}")
                return False
        
        # Run in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: urllib.request.urlretrieve(url, destination))
    
    @staticmethod
    async def http_request(url: str, method: str = 'GET', data: Optional[Dict[str, Any]] = None, 
                         headers: Optional[Dict[str, str]] = None, timeout: int = DEFAULT_TIMEOUT,
                         verify_ssl: bool = True) -> Tuple[int, Optional[bytes], Optional[Dict[str, str]]]:
        """
        Make an HTTP request
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            data: Request data
            headers: Request headers
            timeout: Timeout in seconds
            verify_ssl: Whether to verify SSL certificates
            
        Returns:
            Tuple of (status_code, response_data, response_headers)
        """
        # Set default headers
        if headers is None:
            headers = {}
        
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'Kaleidoscope-AI/1.0'
        
        # Prepare request
        if data is not None:
            if method == 'GET':
                # Add query parameters to URL
                url_parts = list(urllib.parse.urlparse(url))
                query = dict(urllib.parse.parse_qsl(url_parts[4]))
                query.update(data)
                url_parts[4] = urllib.parse.urlencode(query)
                url = urllib.parse.urlunparse(url_parts)
                data = None
            else:
                # Convert data to JSON for other methods
                data = json.dumps(data).encode('utf-8')
                headers['Content-Type'] = 'application/json'
        
        # Create request
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        # Setup SSL context
        ssl_context = ssl.create_default_context()
        if not verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        # Make request with retry logic
        async def request_with_retry():
            for retry in range(MAX_RETRY_COUNT + 1):
                try:
                    with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
                        return (
                            response.status,
                            response.read(),
                            dict(response.getheaders())
                        )
                
                except urllib.error.HTTPError as e:
                    return e.code, e.read(), dict(e.headers)
                
                except (urllib.error.URLError, socket.timeout) as e:
                    if retry == MAX_RETRY_COUNT:
                        logger.error(f"Failed to make request to {url} after {MAX_RETRY_COUNT} retries: {str(e)}")
                        return None, None, None
                    
                    # Calculate backoff time
                    backoff = RETRY_DELAY_BASE ** retry
                    logger.warning(f"Request to {url} failed, retrying in {backoff}s: {str(e)}")
                    await asyncio.sleep(backoff)
        
        # Run in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: request_with_retry())
    
    @staticmethod
    def get_local_ip() -> str:
        """
        Get the local IP address
        
        Returns:
            Local IP address
        """
        try:
            # Create a socket to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # Connect to a public DNS server
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        
        except Exception as e:
            logger.error(f"Error getting local IP: {str(e)}")
            return "127.0.0.1"
    
    @staticmethod
    def check_port_in_use(port: int, host: str = '127.0.0.1') -> bool:
        """
        Check if a port is in use
        
        Args:
            port: Port number
            host: Host to check
            
        Returns:
            True if port is in use, False otherwise
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                return result == 0
        
        except Exception as e:
            logger.error(f"Error checking port {port}: {str(e)}")
            return False
    
    @staticmethod
    def find_free_port(start_port: int = 8000, end_port: int = 9000, host: str = '127.0.0.1') -> Optional[int]:
        """
        Find a free port in a range
        
        Args:
            start_port: Start of port range
            end_port: End of port range
            host: Host to check
            
        Returns:
            Free port number or None if no free ports
        """
        for port in range(start_port, end_port + 1):
            if not NetworkUtils.check_port_in_use(port, host):
                return port
        
        logger.error(f"No free ports found in range {start_port}-{end_port}")
        return None

class ConfigUtils:
    """Utilities for configuration management"""
    
    @staticmethod
    def load_config(file_path: str) -> Dict[str, Any]:
        """
        Load configuration from a file
        
        Args:
            file_path: Path to the configuration file
            
        Returns:
            Configuration dictionary
        """
        try:
            # Determine file format based on extension
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.yaml', '.yml']:
                with open(file_path, 'r') as f:
                    return yaml.safe_load(f)
            
            elif ext == '.json':
                with open(file_path, 'r') as f:
                    return json.load(f)
            
            else:
                logger.error(f"Unsupported configuration file format: {ext}")
                return {}
        
        except Exception as e:
            logger.error(f"Error loading configuration from {file_path}: {str(e)}")
            return {}
    
    @staticmethod
    def save_config(config: Dict[str, Any], file_path: str) -> bool:
        """
        Save configuration to a file
        
        Args:
            config: Configuration dictionary
            file_path: Path to save the configuration
            
        Returns:
            Success status
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Determine file format based on extension
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in ['.yaml', '.yml']:
                with open(file_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
            
            elif ext == '.json':
                with open(file_path, 'w') as f:
                    json.dump(config, f, indent=2)
            
            else:
                logger.error(f"Unsupported configuration file format: {ext}")
                return False
            
            logger.info(f"Saved configuration to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving configuration to {file_path}: {str(e)}")
            return False
    
    @staticmethod
    def merge_configs(base: Dict[str, Any], override: Dict[str, Any], deep_merge: bool = True) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries
        
        Args:
            base: Base configuration
            override: Override configuration
            deep_merge: Whether to perform deep merging of nested dictionaries
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in override.items():
            if deep_merge and key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = ConfigUtils.merge_configs(result[key], value, deep_merge)
            else:
                # Override or add value
                result[key] = value
        
        return result
    
    @staticmethod
    def get_config_value(config: Dict[str, Any], path: str, default: Any = None) -> Any:
        """
        Get a value from a nested configuration dictionary using dot notation
        
        Args:
            config: Configuration dictionary
            path: Path to the value (e.g. 'database.host')
            default: Default value to return if path not found
            
        Returns:
            Configuration value or default
        """
        parts = path.split('.')
        current = config
        
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return default
            
            current = current[part]
        
        return current

class SystemUtils:
    """Utilities for system operations"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        Get system information
        
        Returns:
            System information dictionary
        """
        info = {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'hostname': platform.node(),
            'cpu_count': os.cpu_count() or 0,
            'memory': SystemUtils.get_memory_info(),
            'disk': SystemUtils.get_disk_info(),
            'time': datetime.now().isoformat(),
            'timezone': time.tzname[0]
        }
        
        return info
    
    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """
        Get memory information
        
        Returns:
            Memory information dictionary
        """
        try:
            if platform.system() == "Linux":
                # On Linux, use /proc/meminfo
                mem_info = {}
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            mem_info[key.strip()] = value.strip()
                
                # Extract total and free memory
                total = int(mem_info.get('MemTotal', '0 kB').split()[0]) * 1024
                free = int(mem_info.get('MemAvailable', '0 kB').split()[0]) * 1024
                
                return {
                    'total': total,
                    'free': free,
                    'used': total - free,
                    'percent_used': round((total - free) / total * 100, 2) if total > 0 else 0
                }
            
            elif platform.system() == "Darwin":  # macOS
                # Use vm_stat command
                output = subprocess.check_output(['vm_stat'], universal_newlines=True)
                
                # Parse output
                vm_stats = {}
                for line in output.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        vm_stats[key.strip()] = value.strip()
                
                # Extract page size
                page_size = 4096  # Default page size
                
                # Calculate memory values
                free_pages = int(vm_stats.get('Pages free', '0').replace('.', ''))
                active_pages = int(vm_stats.get('Pages active', '0').replace('.', ''))
                inactive_pages = int(vm_stats.get('Pages inactive', '0').replace('.', ''))
                wired_pages = int(vm_stats.get('Pages wired down', '0').replace('.', ''))
                
                free = free_pages * page_size
                used = (active_pages + inactive_pages + wired_pages) * page_size
                total = free + used
                
                return {
                    'total': total,
                    'free': free,
                    'used': used,
                    'percent_used': round(used / total * 100, 2) if total > 0 else 0
                }
            
            elif platform.system() == "Windows":
                # Use Windows Management Instrumentation (WMI)
                try:
                    import psutil
                    memory = psutil.virtual_memory()
                    
                    return {
                        'total': memory.total,
                        'free': memory.available,
                        'used': memory.used,
                        'percent_used': memory.percent
                    }
                except ImportError:
                    # Fallback method using ctypes on Windows
                    import ctypes
                    
                    kernel32 = ctypes.windll.kernel32
                    c_ulong = ctypes.c_ulong
                    class MEMORYSTATUS(ctypes.Structure):
                        _fields_ = [
                            ('dwLength', c_ulong),
                            ('dwMemoryLoad', c_ulong),
                            ('dwTotalPhys', c_ulong),
                            ('dwAvailPhys', c_ulong),
                            ('dwTotalPageFile', c_ulong),
                            ('dwAvailPageFile', c_ulong),
                            ('dwTotalVirtual', c_ulong),
                            ('dwAvailVirtual', c_ulong)
                        ]
                    
                    memory_status = MEMORYSTATUS()
                    memory_status.dwLength = ctypes.sizeof(MEMORYSTATUS)
                    kernel32.GlobalMemoryStatus(ctypes.byref(memory_status))
                    
                    return {
                        'total': memory_status.dwTotalPhys,
                        'free': memory_status.dwAvailPhys,
                        'used': memory_status.dwTotalPhys - memory_status.dwAvailPhys,
                        'percent_used': memory_status.dwMemoryLoad
                    }
            
            # Default case if platform not specifically handled
            return {
                'total': 0,
                'free': 0,
                'used': 0,
                'percent_used': 0
            }
        
        except Exception as e:
            logger.error(f"Error getting memory info: {str(e)}")
            return {
                'total': 0,
                'free': 0,
                'used': 0,
                'percent_used': 0,
                'error': str(e)
            }
    
    @staticmethod
    def get_disk_info() -> Dict[str, Any]:
        """
        Get disk information
        
        Returns:
            Disk information dictionary
        """
        try:
            disk_info = {}
            
            # Get disk usage for the root directory
            usage = shutil.disk_usage('/')
            
            disk_info['root'] = {
                'total': usage.total,
                'free': usage.free,
                'used': usage.used,
                'percent_used': round(usage.used / usage.total * 100, 2) if usage.total > 0 else 0
            }
            
            # Try to get disk usage for the working directory if different
            cwd = os.getcwd()
            if os.path.splitdrive(cwd)[0] != os.path.splitdrive('/')[0]:
                try:
                    usage = shutil.disk_usage(cwd)
                    disk_info['working_dir'] = {
                        'path': cwd,
                        'total': usage.total,
                        'free': usage.free,
                        'used': usage.used,
                        'percent_used': round(usage.used / usage.total * 100, 2) if usage.total > 0 else 0
                    }
                except Exception as e:
                    logger.error(f"Error getting disk info for working directory: {str(e)}")
            
            return disk_info
        
        except Exception as e:
            logger.error(f"Error getting disk info: {str(e)}")
            return {
                'error': str(e)
            }
    
    @staticmethod
    def get_process_info() -> Dict[str, Any]:
        """
        Get information about the current process
        
        Returns:
            Process information dictionary
        """
        try:
            # Get current process ID
            pid = os.getpid()
            
            # Try to get detailed info using psutil
            try:
                import psutil
                process = psutil.Process(pid)
                
                return {
                    'pid': pid,
                    'name': process.name(),
                    'status': process.status(),
                    'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
                    'cpu_percent': process.cpu_percent(),
                    'memory_percent': process.memory_percent(),
                    'memory_info': {
                        'rss': process.memory_info().rss,
                        'vms': process.memory_info().vms
                    },
                    'num_threads': process.num_threads(),
                    'username': process.username(),
                    'executable': process.exe()
                }
            
            except ImportError:
                # Basic info without psutil
                return {
                    'pid': pid,
                    'executable': sys.executable,
                    'cwd': os.getcwd()
                }
        
        except Exception as e:
            logger.error(f"Error getting process info: {str(e)}")
            return {
                'pid': os.getpid(),
                'error': str(e)
            }
    
    @staticmethod
    def execute_command(command: List[str], timeout: int = 60, cwd: Optional[str] = None,
                      env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        """
        Execute a shell command
        
        Args:
            command: Command to execute (list of arguments)
            timeout: Timeout in seconds
            cwd: Working directory
            env: Environment variables
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        try:
            # Log command
            logger.debug(f"Executing command: {' '.join(command)}")
            
            # Run command
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                universal_newlines=True
            )
            
            # Wait for completion with timeout
            stdout, stderr = process.communicate(timeout=timeout)
            
            # Log result
            logger.debug(f"Command returned: {process.returncode}")
            
            return process.returncode, stdout, stderr
        
        except subprocess.TimeoutExpired:
            # Kill process on timeout
            process.kill()
            stdout, stderr = process.communicate()
            
            logger.error(f"Command timed out after {timeout}s: {' '.join(command)}")
            
            return -1, stdout, stderr
        
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            return -1, "", str(e)
