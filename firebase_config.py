"""
Firebase Admin SDK Configuration Module
CRITICAL: This module initializes Firebase with production-grade error handling
and environment-aware configuration. Using Firestore for decentralized state
management as per mission constraints.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore_v1 import Client

@dataclass
class FirebaseConfig:
    """Validated Firebase configuration container"""
    project_id: str
    credentials_path: Optional[Path] = None
    use_emulator: bool = False
    emulator_host: str = "localhost:8080"

class FirebaseInitializationError(Exception):
    """Custom exception for Firebase initialization failures"""
    pass

class FirebaseManager:
    """Singleton manager for Firebase Firestore with health checks"""
    
    _instance: Optional['FirebaseManager'] = None
    _client: Optional[Client] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.logger = logging.getLogger(__name__)
            self._config = None
            self._initialized = True
    
    def initialize(self, config: FirebaseConfig) -> Client:
        """
        Initialize Firebase with comprehensive error handling
        
        Args:
            config: Validated Firebase configuration
            
        Returns:
            Initialized Firestore client
            
        Raises:
            FirebaseInitializationError: If initialization fails
            FileNotFoundError: If credentials file doesn't exist
            ValueError: If configuration is invalid
        """
        try:
            # Validate credentials path if provided
            if config.credentials_path:
                if not config.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Firebase credentials not found at {config.credentials_path}"
                    )
                cred = credentials.Certificate(str(config.credentials_path))
            else:
                # Use Application Default Credentials
                cred = credentials.ApplicationDefault()
            
            # Initialize Firebase app
            firebase_admin.initialize_app(cred, {
                'projectId': config.project_id,
            })
            
            # Get Firestore client
            self._client = firestore.client()
            
            # Configure emulator if needed
            if config.use_emulator:
                os.environ["FIRESTORE_EMULATOR_HOST"] = config.emulator_host
                self.logger.info(f"Using Firestore emulator at {config.emulator_host}")
            
            # Test connection
            self._health_check()
            
            self.logger.info(f"Firebase initialized for project: {config.project_id}")
            return self._client
            
        except Exception as e:
            self.logger.error(f"Firebase initialization failed: {str(e)}")
            raise FirebaseInitializationError(f"Failed to initialize Firebase: {str(e)}")
    
    def _health_check(self):
        """Validate Firebase connection by attempting a simple operation"""
        try:
            # Create a test document in a temporary collection
            test_ref = self._client.collection("_system_health").document("connection_test")
            test_ref.set({"timestamp": firestore.SERVER_TIMESTAMP, "status": "healthy"})
            test_ref.delete()
            self.logger.debug("Firebase health check passed")
        except Exception as e:
            self.logger.error(f"Firebase health check failed: {str(e)}")
            raise FirebaseInitializationError(f"Health check failed: {str(e)}")
    
    def get_client(self) -> Client:
        """Get Firestore client with lazy initialization check"""
        if self._client is None:
            raise RuntimeError("Firebase not initialized. Call initialize() first.")
        return self._client
    
    def shutdown(self):
        """Clean shutdown of Firebase resources"""
        try:
            firebase_admin.delete_app(firebase_admin.get_app())
            self._client = None
            self.logger.info("Firebase resources cleaned up")
        except Exception as e:
            self.logger.warning(f"Error during Firebase shutdown: {str(e)}")

# Global instance
firebase_manager = FirebaseManager()