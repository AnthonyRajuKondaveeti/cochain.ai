"""
Embedding API Client for HuggingFace Inference API
Replaces local sentence-transformers to reduce memory footprint from 1.3GB to <100MB
"""

import os
import logging
import time
import asyncio
from typing import List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)

# Try to import httpx for async HTTP requests
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available - falling back to requests")
    import requests

# Configuration
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY')
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'

# Official HuggingFace Router API endpoint (November 2024+)
# Format: https://router.huggingface.co/hf-inference/models/{model}/pipeline/feature-extraction
API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL_NAME}/pipeline/feature-extraction"

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
TIMEOUT = 30  # seconds

# In-memory cache for embeddings
_embedding_cache = {}


class EmbeddingAPIClient:
    """Client for HuggingFace Inference API with caching and retry logic"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = MODEL_NAME):
        """
        Initialize the embedding API client
        
        Args:
            api_key: HuggingFace API key (defaults to HUGGINGFACE_API_KEY env var)
            model_name: Model identifier on HuggingFace Hub
        """
        self.api_key = api_key or HUGGINGFACE_API_KEY
        self.model_name = model_name
        # Official HuggingFace Router API endpoint (November 2024+)
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{model_name}/pipeline/feature-extraction"
        
        if not self.api_key:
            logger.warning("⚠️ HUGGINGFACE_API_KEY not set - API calls will fail!")
        
        self.cache = _embedding_cache
        self.use_httpx = HTTPX_AVAILABLE
        
        logger.info(f"✅ EmbeddingAPIClient initialized (model: {model_name}, httpx: {self.use_httpx})")
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        # Simple hash-based cache key
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()
    
    def _call_api_sync(self, text: str, retries: int = 0) -> Optional[List[float]]:
        """
        Synchronous API call with retry logic
        
        Args:
            text: Text to encode
            retries: Current retry attempt number
            
        Returns:
            Embedding vector as list of floats, or None on failure
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        # HuggingFace expects {"inputs": [text]} for batch processing
        payload = {"inputs": [text]}  # Wrap text in list for batch API format
        
        try:
            if self.use_httpx:
                with httpx.Client(timeout=TIMEOUT) as client:
                    response = client.post(self.api_url, headers=headers, json=payload)
            else:
                response = requests.post(
                    self.api_url, 
                    headers=headers, 
                    json=payload,
                    timeout=TIMEOUT
                )
            
            if response.status_code == 200:
                result = response.json()
                
                # HuggingFace returns [[embedding]] for single input
                # or [[emb1], [emb2], ...] for batch
                if isinstance(result, list) and len(result) > 0:
                    # Get first embedding from batch response
                    embedding = result[0]
                    
                    # Verify it's a valid embedding (list of numbers with correct dimensions)
                    if isinstance(embedding, list) and len(embedding) == 384:
                        logger.debug(f"✅ Embedding generated: {len(embedding)} dimensions")
                        return embedding
                    else:
                        logger.error(f"❌ Invalid embedding format: length={len(embedding) if isinstance(embedding, list) else 'not a list'}")
                        logger.error(f"Response sample: {str(result)[:200]}")
                        return None
                else:
                    logger.error(f"❌ Unexpected API response format: {type(result)}")
                    logger.error(f"Response: {str(result)[:200]}")
                    return None
            
            elif response.status_code == 503 and retries < MAX_RETRIES:
                # Model is loading - retry after delay
                logger.warning(f"⏳ Model loading (503) - retry {retries + 1}/{MAX_RETRIES}")
                time.sleep(RETRY_DELAY * (retries + 1))
                return self._call_api_sync(text, retries + 1)
            
            elif response.status_code == 429 and retries < MAX_RETRIES:
                # Rate limit - retry with exponential backoff
                logger.warning(f"⚠️ Rate limited (429) - retry {retries + 1}/{MAX_RETRIES}")
                time.sleep(RETRY_DELAY * (2 ** retries))
                return self._call_api_sync(text, retries + 1)
            
            else:
                logger.error(f"❌ API error {response.status_code}: {response.text}")
                return None
        
        except Exception as e:
            if retries < MAX_RETRIES:
                logger.warning(f"⚠️ API call failed: {str(e)} - retry {retries + 1}/{MAX_RETRIES}")
                time.sleep(RETRY_DELAY)
                return self._call_api_sync(text, retries + 1)
            else:
                logger.error(f"❌ API call failed after {MAX_RETRIES} retries: {str(e)}")
                return None
    
    async def _call_api_async(self, text: str, retries: int = 0) -> Optional[List[float]]:
        """
        Asynchronous API call with retry logic
        
        Args:
            text: Text to encode
            retries: Current retry attempt number
            
        Returns:
            Embedding vector as list of floats, or None on failure
        """
        if not HTTPX_AVAILABLE:
            logger.error("❌ httpx not available for async calls")
            return self._call_api_sync(text, retries)
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": text}
        
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(self.api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                
                if isinstance(result, list):
                    if len(result) > 0:
                        if isinstance(result[0], list):
                            embedding = result[0]
                        else:
                            embedding = result
                        
                        logger.debug(f"✅ Embedding generated (async): {len(embedding)} dimensions")
                        return embedding
                
                logger.error(f"❌ Unexpected API response format: {type(result)}")
                return None
            
            elif response.status_code == 503 and retries < MAX_RETRIES:
                logger.warning(f"⏳ Model loading (503) - async retry {retries + 1}/{MAX_RETRIES}")
                await asyncio.sleep(RETRY_DELAY * (retries + 1))
                return await self._call_api_async(text, retries + 1)
            
            elif response.status_code == 429 and retries < MAX_RETRIES:
                logger.warning(f"⚠️ Rate limited (429) - async retry {retries + 1}/{MAX_RETRIES}")
                await asyncio.sleep(RETRY_DELAY * (2 ** retries))
                return await self._call_api_async(text, retries + 1)
            
            else:
                logger.error(f"❌ API error {response.status_code}: {response.text}")
                return None
        
        except Exception as e:
            if retries < MAX_RETRIES:
                logger.warning(f"⚠️ Async API call failed: {str(e)} - retry {retries + 1}/{MAX_RETRIES}")
                await asyncio.sleep(RETRY_DELAY)
                return await self._call_api_async(text, retries + 1)
            else:
                logger.error(f"❌ Async API call failed after {MAX_RETRIES} retries: {str(e)}")
                return None
    
    def encode(self, text: Union[str, List[str]], use_cache: bool = True) -> Optional[Union[np.ndarray, List[np.ndarray]]]:
        """
        Encode text to embedding vector (synchronous)
        
        Args:
            text: Single text string or list of texts
            use_cache: Whether to use in-memory cache
            
        Returns:
            Embedding as numpy array, or list of arrays for batch input
        """
        # Handle batch input
        if isinstance(text, list):
            embeddings = []
            for t in text:
                emb = self.encode(t, use_cache=use_cache)
                if emb is not None:
                    embeddings.append(emb)
            return embeddings if embeddings else None
        
        # Single text input
        cache_key = self._get_cache_key(text) if use_cache else None
        
        # Check cache
        if use_cache and cache_key in self.cache:
            logger.debug(f"✅ Cache hit for text: {text[:50]}...")
            return self.cache[cache_key]
        
        # Call API
        embedding = self._call_api_sync(text)
        
        if embedding is not None:
            embedding_array = np.array(embedding, dtype=np.float32)
            
            # Store in cache
            if use_cache and cache_key:
                self.cache[cache_key] = embedding_array
            
            return embedding_array
        
        return None
    
    async def encode_async(self, text: Union[str, List[str]], use_cache: bool = True) -> Optional[Union[np.ndarray, List[np.ndarray]]]:
        """
        Encode text to embedding vector (asynchronous)
        
        Args:
            text: Single text string or list of texts
            use_cache: Whether to use in-memory cache
            
        Returns:
            Embedding as numpy array, or list of arrays for batch input
        """
        import asyncio
        
        # Handle batch input
        if isinstance(text, list):
            tasks = [self.encode_async(t, use_cache=use_cache) for t in text]
            embeddings = await asyncio.gather(*tasks)
            return [e for e in embeddings if e is not None]
        
        # Single text input
        cache_key = self._get_cache_key(text) if use_cache else None
        
        # Check cache
        if use_cache and cache_key in self.cache:
            logger.debug(f"✅ Cache hit (async) for text: {text[:50]}...")
            return self.cache[cache_key]
        
        # Call API
        embedding = await self._call_api_async(text)
        
        if embedding is not None:
            embedding_array = np.array(embedding, dtype=np.float32)
            
            # Store in cache
            if use_cache and cache_key:
                self.cache[cache_key] = embedding_array
            
            return embedding_array
        
        return None
    
    def clear_cache(self):
        """Clear in-memory embedding cache"""
        self.cache.clear()
        logger.info("🗑️ Embedding cache cleared")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'keys': list(self.cache.keys())[:10]  # First 10 keys
        }


# Singleton instance
_client_instance = None


def get_embedding_client() -> EmbeddingAPIClient:
    """Get or create singleton embedding client"""
    global _client_instance
    if _client_instance is None:
        _client_instance = EmbeddingAPIClient()
    return _client_instance


# Convenience functions
def encode_text(text: Union[str, List[str]], use_cache: bool = True) -> Optional[Union[np.ndarray, List[np.ndarray]]]:
    """
    Convenience function to encode text using the singleton client
    
    Args:
        text: Text or list of texts to encode
        use_cache: Whether to use caching
        
    Returns:
        Embedding vector(s) as numpy array(s)
    """
    client = get_embedding_client()
    return client.encode(text, use_cache=use_cache)


async def encode_text_async(text: Union[str, List[str]], use_cache: bool = True) -> Optional[Union[np.ndarray, List[np.ndarray]]]:
    """
    Async convenience function to encode text using the singleton client
    
    Args:
        text: Text or list of texts to encode
        use_cache: Whether to use caching
        
    Returns:
        Embedding vector(s) as numpy array(s)
    """
    client = get_embedding_client()
    return await client.encode_async(text, use_cache=use_cache)
