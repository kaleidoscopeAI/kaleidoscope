#!/usr/bin/env python3
"""
Kaleidoscope AI - Licensing and Monetization System
==================================================
Comprehensive licensing system for managing application ownership,
usage tracking, profit sharing, and subscription management.
"""

import os
import sys
import time
import json
import uuid
import hmac
import hashlib
import base64
import logging
import requests
import sqlite3
import datetime
import threading
import asyncio
import jwt
import stripe
import docker
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union, Set, Tuple
from enum import Enum, auto
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("licensing.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
LICENSE_DB_PATH = "kaleidoscope_licenses.db"
ENCRYPTION_KEY_ENV = "KALEIDOSCOPE_ENCRYPTION_KEY"
JWT_SECRET_ENV = "KALEIDOSCOPE_JWT_SECRET"
API_BASE_URL = "https://api.kaleidoscopeai.com/v1"
DEFAULT_PROFIT_SHARE_PERCENTAGE = 5.0  # 5% profit share
USAGE_TRACKING_INTERVAL = 3600  # 1 hour

class LicenseType(Enum):
    """Types of licenses"""
    PERSONAL = auto()
    STARTUP = auto()
    BUSINESS = auto()
    ENTERPRISE = auto()
    EDUCATIONAL = auto()
    NONPROFIT = auto()
    TRIAL = auto()

class SubscriptionTier(Enum):
    """Subscription tiers"""
    FREE = auto()
    BASIC = auto()
    PROFESSIONAL = auto()
    PREMIUM = auto()
    ULTIMATE = auto()

@dataclass
class LicenseInfo:
    """License information"""
    license_id: str
    user_id: str
    app_id: str
    app_name: str
    license_type: LicenseType
    subscription_tier: SubscriptionTier
    creation_date: float
    expiration_date: Optional[float] = None
    profit_share_percentage: float = DEFAULT_PROFIT_SHARE_PERCENTAGE
    usage_limits: Dict[str, Any] = field(default_factory=dict)
    features: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        # Convert enum values to strings
        result['license_type'] = self.license_type.name
        result['subscription_tier'] = self.subscription_tier.name
        # Convert set to list
        result['features'] = list(self.features)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LicenseInfo':
        """Create from dictionary"""
        # Convert string values to enums
        if 'license_type' in data:
            data['license_type'] = LicenseType[data['license_type']]
        if 'subscription_tier' in data:
            data['subscription_tier'] = SubscriptionTier[data['subscription_tier']]
        # Convert list to set
        if 'features' in data:
            data['features'] = set(data['features'])
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Check if license is valid"""
        if self.expiration_date is None:
            return True
        return time.time() < self.expiration_date

@dataclass
class UsageMetrics:
    """Usage metrics for billing and monitoring"""
    app_id: str
    license_id: str
    start_time: float
    cpu_time: float = 0.0
    memory_usage: float = 0.0
    storage_usage: float = 0.0
    api_calls: int = 0
    user_count: int = 0
    transaction_volume: float = 0.0
    revenue: float = 0.0
    profit: float = 0.0
    last_update: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class EncryptionManager:
    """Manages encryption for sensitive data"""
    
    def __init__(self, key_env_var: str = ENCRYPTION_KEY_ENV):
        """
        Initialize the encryption manager
        
        Args:
            key_env_var: Environment variable containing the encryption key
        """
        # Get encryption key from environment or generate one
        key_base64 = os.environ.get(key_env_var)
        if key_base64:
            self.key = base64.urlsafe_b64decode(key_base64)
        else:
            # Generate a new key
            self.key = Fernet.generate_key()
            # Log the key for setup purposes (would be removed in production)
            key_base64 = base64.urlsafe_b64encode(self.key).decode()
            logger.warning(f"Generated new encryption key. Set {key_env_var}={key_base64}")
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt data
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data (base64 encoded)
        """
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt data
        
        Args:
            encrypted_data: Encrypted data (base64 encoded)
            
        Returns:
            Decrypted data
        """
        return self.cipher.decrypt(encrypted_data.encode()).decode()
    
    def generate_license_key(self, license_info: LicenseInfo) -> str:
        """
        Generate a license key
        
        Args:
            license_info: License information
            
        Returns:
            License key
        """
        # Create license data
        license_data = {
            "license_id": license_info.license_id,
            "user_id": license_info.user_id,
            "app_id": license_info.app_id,
            "type": license_info.license_type.name,
            "tier": license_info.subscription_tier.name,
            "created": license_info.creation_date,
            "expires": license_info.expiration_date
        }
        
        # Convert to JSON and encrypt
        license_json = json.dumps(license_data)
        encrypted = self.encrypt(license_json)
        
        # Format as a license key
        prefix = "KAI"
        checksum = self._calculate_checksum(encrypted)
        license_key = f"{prefix}-{encrypted[:8]}-{encrypted[8:16]}-{encrypted[16:24]}-{checksum[:6]}"
        
        return license_key
    
    def _calculate_checksum(self, data: str) -> str:
        """
        Calculate checksum for data
        
        Args:
            data: Data to calculate checksum for
            
        Returns:
            Checksum (hex encoded)
        """
        return hashlib.sha256(data.encode()).hexdigest()

class DatabaseManager:
    """Manages database operations for license storage"""
    
    def __init__(self, db_path: str = LICENSE_DB_PATH):
        """
        Initialize the database manager
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize the database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create licenses table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                license_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                app_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                license_type TEXT NOT NULL,
                subscription_tier TEXT NOT NULL,
                creation_date REAL NOT NULL,
                expiration_date REAL,
                profit_share_percentage REAL NOT NULL,
                usage_limits TEXT,
                features TEXT,
                metadata TEXT,
                license_key TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
            ''')
            
            # Create usage metrics table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL,
                license_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                cpu_time REAL NOT NULL,
                memory_usage REAL NOT NULL,
                storage_usage REAL NOT NULL,
                api_calls INTEGER NOT NULL,
                user_count INTEGER NOT NULL,
                transaction_volume REAL NOT NULL,
                revenue REAL NOT NULL,
                profit REAL NOT NULL,
                metadata TEXT,
                FOREIGN KEY (license_id) REFERENCES licenses (license_id)
            )
            ''')
            
            # Create revenue share table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                payment_id TEXT,
                status TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (license_id) REFERENCES licenses (license_id)
            )
            ''')
            
            # Create index on app_id for licenses
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_licenses_app_id ON licenses (app_id)
            ''')
            
            # Create index on license_id for usage metrics
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_usage_metrics_license_id ON usage_metrics (license_id)
            ''')
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_license(self, license_info: LicenseInfo, license_key: str) -> bool:
        """
        Save a license to the database
        
        Args:
            license_info: License information
            license_key: Generated license key
            
        Returns:
            Success status
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                INSERT OR REPLACE INTO licenses (
                    license_id, user_id, app_id, app_name, license_type, 
                    subscription_tier, creation_date, expiration_date, 
                    profit_share_percentage, usage_limits, features, 
                    metadata, license_key, active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    license_info.license_id,
                    license_info.user_id,
                    license_info.app_id,
                    license_info.app_name,
                    license_info.license_type.name,
                    license_info.subscription_tier.name,
                    license_info.creation_date,
                    license_info.expiration_date,
                    license_info.profit_share_percentage,
                    json.dumps(license_info.usage_limits),
                    json.dumps(list(license_info.features)),
                    json.dumps(license_info.metadata),
                    license_key,
                    1  # active
                ))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error saving license: {str(e)}")
                return False
    
    def get_license(self, license_id: str) -> Optional[Tuple[LicenseInfo, str]]:
        """
        Get a license from the database
        
        Args:
            license_id: License ID
            
        Returns:
            Tuple of (license_info, license_key) or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM licenses WHERE license_id = ? AND active = 1
            ''', (license_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Convert row to dictionary
            license_data = dict(row)
            
            # Parse JSON fields
            license_data['usage_limits'] = json.loads(license_data['usage_limits'])
            license_data['features'] = json.loads(license_data['features'])
            license_data['metadata'] = json.loads(license_data['metadata'])
            
            # Extract license key
            license_key = license_data.pop('license_key')
            
            # Remove active field
            license_data.pop('active')
            
            # Create license info
            license_info = LicenseInfo.from_dict(license_data)
            
            return license_info, license_key
    
    def get_license_by_app(self, app_id: str) -> Optional[Tuple[LicenseInfo, str]]:
        """
        Get a license for an app
        
        Args:
            app_id: App ID
            
        Returns:
            Tuple of (license_info, license_key) or None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM licenses WHERE app_id = ? AND active = 1
            ''', (app_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            # Convert row to dictionary
            license_data = dict(row)
            
            # Parse JSON fields
            license_data['usage_limits'] = json.loads(license_data['usage_limits'])
            license_data['features'] = json.loads(license_data['features'])
            license_data['metadata'] = json.loads(license_data['metadata'])
            
            # Extract license key
            license_key = license_data.pop('license_key')
            
            # Remove active field
            license_data.pop('active')
            
            # Create license info
            license_info = LicenseInfo.from_dict(license_data)
            
            return license_info, license_key
    
    def list_licenses(self, user_id: Optional[str] = None) -> List[Tuple[LicenseInfo, str]]:
        """
        List licenses
        
        Args:
            user_id: Optional user ID to filter by
            
        Returns:
            List of (license_info, license_key) tuples
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                SELECT * FROM licenses WHERE user_id = ? AND active = 1
                ''', (user_id,))
            else:
                cursor.execute('''
                SELECT * FROM licenses WHERE active = 1
                ''')
            
            rows = cursor.fetchall()
            
            licenses = []
            for row in rows:
                # Convert row to dictionary
                license_data = dict(row)
                
                # Parse JSON fields
                license_data['usage_limits'] = json.loads(license_data['usage_limits'])
                license_data['features'] = json.loads(license_data['features'])
                license_data['metadata'] = json.loads(license_data['metadata'])
                
                # Extract license key
                license_key = license_data.pop('license_key')
                
                # Remove active field
                license_data.pop('active')
                
                # Create license info
                license_info = LicenseInfo.from_dict(license_data)
                
                licenses.append((license_info, license_key))
            
            return licenses
    
    def deactivate_license(self, license_id: str) -> bool:
        """
        Deactivate a license
        
        Args:
            license_id: License ID
            
        Returns:
            Success status
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE licenses SET active = 0 WHERE license_id = ?
            ''', (license_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def save_usage_metrics(self, metrics: UsageMetrics) -> bool:
        """
        Save usage metrics
        
        Args:
            metrics: Usage metrics
            
        Returns:
            Success status
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                INSERT INTO usage_metrics (
                    app_id, license_id, timestamp, cpu_time, memory_usage,
                    storage_usage, api_calls, user_count, transaction_volume,
                    revenue, profit, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics.app_id,
                    metrics.license_id,
                    metrics.last_update,
                    metrics.cpu_time,
                    metrics.memory_usage,
                    metrics.storage_usage,
                    metrics.api_calls,
                    metrics.user_count,
                    metrics.transaction_volume,
                    metrics.revenue,
                    metrics.profit,
                    json.dumps(metrics.metadata)
                ))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error saving usage metrics: {str(e)}")
                return False
    
    def get_usage_metrics(self, license_id: str, days: int = 30) -> List[UsageMetrics]:
        """
        Get usage metrics for a license
        
        Args:
            license_id: License ID
            days: Number of days to retrieve metrics for
            
        Returns:
            List of usage metrics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            start_time = time.time() - (days * 86400)
            
            cursor.execute('''
            SELECT * FROM usage_metrics
            WHERE license_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
            ''', (license_id, start_time))
            
            rows = cursor.fetchall()
            
            metrics = []
            for row in rows:
                # Convert row to dictionary
                data = dict(row)
                
                # Parse metadata
                data['metadata'] = json.loads(data['metadata'])
                
                # Create metrics object
                metrics_obj = UsageMetrics(
                    app_id=data['app_id'],
                    license_id=data['license_id'],
                    start_time=data['timestamp'],
                    cpu_time=data['cpu_time'],
                    memory_usage=data['memory_usage'],
                    storage_usage=data['storage_usage'],
                    api_calls=data['api_calls'],
                    user_count=data['user_count'],
                    transaction_volume=data['transaction_volume'],
                    revenue=data['revenue'],
                    profit=data['profit'],
                    last_update=data['timestamp'],
                    metadata=data['metadata']
                )
                
                metrics.append(metrics_obj)
            
            return metrics
    
    def save_revenue_share(
        self, 
        license_id: str, 
        amount: float, 
        currency: str = "USD",
        payment_id: Optional[str] = None, 
        status: str = "pending",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a revenue share record
        
        Args:
            license_id: License ID
            amount: Amount to share
            currency: Currency code
            payment_id: Optional payment ID
            status: Status of the share (pending, processed, failed)
            metadata: Optional metadata
            
        Returns:
            Success status
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                INSERT INTO revenue_shares (
                    license_id, timestamp, amount, currency,
                    payment_id, status, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    license_id,
                    time.time(),
                    amount,
                    currency,
                    payment_id,
                    status,
                    json.dumps(metadata or {})
                ))
                
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error saving revenue share: {str(e)}")
                return False
    
    def get_revenue_shares(self, license_id: str) -> List[Dict[str, Any]]:
        """
        Get revenue shares for a license
        
        Args:
            license_id: License ID
            
        Returns:
            List of revenue share records
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM revenue_shares WHERE license_id = ?
            ORDER BY timestamp DESC
            ''', (license_id,))
            
            rows = cursor.fetchall()
            
            shares = []
            for row in rows:
                data = dict(row)
                data['metadata'] = json.loads(data['metadata'])
                shares.append(data)
            
            return shares

class LicenseManager:
    """Manages license creation, validation, and enforcement"""
    
    def __init__(self):
        """Initialize the license manager"""
        self.encryption_manager = EncryptionManager()
        self.db_manager = DatabaseManager()
    
    def create_license(
        self, 
        user_id: str, 
        app_id: str, 
        app_name: str,
        license_type: LicenseType,
        subscription_tier: SubscriptionTier,
        expiration_days: Optional[int] = None,
        profit_share_percentage: float = DEFAULT_PROFIT_SHARE_PERCENTAGE,
        usage_limits: Optional[Dict[str, Any]] = None,
        features: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[LicenseInfo, str]:
        """
        Create a new license
        
        Args:
            user_id: User ID
            app_id: App ID
            app_name: App name
            license_type: License type
            subscription_tier: Subscription tier
            expiration_days: Number of days until expiration (None for perpetual)
            profit_share_percentage: Profit share percentage
            usage_limits: Optional usage limits
            features: Optional set of features
            metadata: Optional metadata
            
        Returns:
            Tuple of (license_info, license_key)
        """
        license_id = str(uuid.uuid4())
        creation_date = time.time()
        
        # Calculate expiration date if provided
        expiration_date = None
        if expiration_days is not None and expiration_days > 0:
            expiration_date = creation_date + (expiration_days * 86400)
        
        # Create license info
        license_info = LicenseInfo(
            license_id=license_id,
            user_id=user_id,
            app_id=app_id,
            app_name=app_name,
            license_type=license_type,
            subscription_tier=subscription_tier,
            creation_date=creation_date,
            expiration_date=expiration_date,
            profit_share_percentage=profit_share_percentage,
            usage_limits=usage_limits or {},
            features=features or set(),
            metadata=metadata or {}
        )
        
        # Generate license key
        license_key = self.encryption_manager.generate_license_key(license_info)
        
        # Save to database
        if not self.db_manager.save_license(license_info, license_key):
            raise RuntimeError("Failed to save license to database")
        
        return license_info, license_key
    
    def validate_license(self, license_id: str) -> Tuple[bool, Optional[LicenseInfo]]:
        """
        Validate a license
        
        Args:
            license_id: License ID
            
        Returns:
            Tuple of (valid, license_info)
        """
        # Get license from database
        result = self.db_manager.get_license(license_id)
        if not result:
            return False, None
        
        license_info, _ = result
        
        # Check if license is valid
        if not license_info.is_valid():
            return False, license_info
        
        return True, license_info
    
    def validate_app_license(self, app_id: str) -> Tuple[bool, Optional[LicenseInfo]]:
        """
        Validate a license for an app
        
        Args:
            app_id: App ID
            
        Returns:
            Tuple of (valid, license_info)
        """
        # Get license from database
        result = self.db_manager.get_license_by_app(app_id)
        if not result:
            return False, None
        
        license_info, _ = result
        
        # Check if license is valid
        if not license_info.is_valid():
            return False, license_info
        
        return True, license_info
    
    def get_license_key(self, license_id: str) -> Optional[str]:
        """
        Get a license key
        
        Args:
            license_id: License ID
            
        Returns:
            License key or None
        """
        # Get license from database
        result = self.db_manager.get_license(license_id)
        if not result:
            return None
        
        _, license_key = result
        return license_key
    
    def list_user_licenses(self, user_id: str) -> List[Tuple[LicenseInfo, str]]:
        """
        List licenses for a user
        
        Args:
            user_id: User ID
            
        Returns:
            List of (license_info, license_key) tuples
        """
        return self.db_manager.list_licenses(user_id)
    
    def revoke_license(self, license_id: str) -> bool:
        """
        Revoke a license
        
        Args:
            license_id: License ID
            
        Returns:
            Success status
        """
        return self.db_manager.deactivate_license(license_id)
    
    def apply_license_embedded(
        self, 
        license_info: LicenseInfo, 
        code_directory: str
    ) -> bool:
        """
        Apply license information to code
        
        Args:
            license_info: License information
            code_directory: Directory containing code
            
        Returns:
            Success status
        """
        try:
            license_data = license_info.to_dict()
            license_key = self.encryption_manager.generate_license_key(license_info)
            
            # Find main source files to embed license
            embedded = False
            
            # Python
            py_files = list(Path(code_directory).glob("**/*.py"))
            for py_file in py_files:
                # Look for main/app files
                filename = py_file.name.lower()
                if any(name in filename for name in ["main", "app", "init", "setup"]):
                    # Embed license
                    self._embed_license_in_file(py_file, license_key, license_data, "python")
                    embedded = True
                    break
            
            # JavaScript/TypeScript
            js_files = list(Path(code_directory).glob("**/*.js")) + list(Path(code_directory).glob("**/*.ts"))
            for js_file in js_files:
                # Look for main/app files
                filename = js_file.name.lower()
                if any(name in filename for name in ["main", "app", "index", "server"]):
                    # Embed license
                    self._embed_license_in_file(js_file, license_key, license_data, "javascript")
                    embedded = True
                    break
            
            # If no suitable files found, create a license file
            if not embedded:
                license_file = os.path.join(code_directory, "LICENSE.json")
                with open(license_file, 'w') as f:
                    json.dump({
                        "license_key": license_key,
                        "info": license_data
                    }, f, indent=2)
                embedded = True
            
            return embedded
            
        except Exception as e:
            logger.error(f"Error applying embedded license: {str(e)}")
            return False
    
    def _embed_license_in_file(
        self, 
        file_path: str, 
        license_key: str, 
        license_data: Dict[str, Any],
        language: str
    ) -> None:
        """
        Embed license information in a file
        
        Args:
            file_path: Path to the file
            license_key: License key
            license_data: License data
            language: Programming language
        """
        # Read file content
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Create license comment based on language
        if language == "python":
            license_comment = (
                "# KALEIDOSCOPE AI LICENSE\n"
                "# ================================\n"
                f"# License Key: {license_key}\n"
                "# DO NOT REMOVE OR MODIFY THIS SECTION\n"
                "# Visit https://kaleidoscopeai.com/license for details\n"
                "# ================================\n"
            )
        elif language == "javascript":
            license_comment = (
                "// KALEIDOSCOPE AI LICENSE\n"
                "// ================================\n"
                f"// License Key: {license_key}\n"
                "// DO NOT REMOVE OR MODIFY THIS SECTION\n"
                "// Visit https://kaleidoscopeai.com/license for details\n"
                "// ================================\n"
            )
        else:
            license_comment = (
                "/*\n"
                " * KALEIDOSCOPE AI LICENSE\n"
                " * ================================\n"
                f" * License Key: {license_key}\n"
                " * DO NOT REMOVE OR MODIFY THIS SECTION\n"
                " * Visit https://kaleidoscopeai.com/license for details\n"
                " * ================================\n"
                " */\n"
            )
        
        # Add license comment to the beginning of the file
        new_content = license_comment + content
        
        # Write updated content
        with open(file_path, 'w') as f:
            f.write(new_content)

class UsageTracker:
    """Tracks application usage for billing and revenue sharing"""
    
    def __init__(self, interval: int = USAGE_TRACKING_INTERVAL):
        """
        Initialize the usage tracker
        
        Args:
            interval: Tracking interval in seconds
        """
        self.db_manager = DatabaseManager()
        self.interval = interval
        self.tracking_threads = {}
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Docker client initialization failed: {str(e)}")
    
    def start_tracking(self, license_info: LicenseInfo, container_id: Optional[str] = None) -> bool:
        """
        Start tracking usage for an app
        
        Args:
            license_info