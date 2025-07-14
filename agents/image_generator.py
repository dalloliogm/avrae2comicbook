"""Image Generation Coordinator for interfacing with multiple image generation APIs."""

import asyncio
import time
from typing import List, Dict, Optional, Any
from pathlib import Path
import requests
from PIL import Image
import io
import hashlib
from loguru import logger

from models import (
    Mission, Panel, ImageGenerationRequest, ImageGenerationResult
)
from config import settings


class ImageGenerationCoordinator:
    """Coordinator for managing image generation from multiple APIs."""
    
    def __init__(self, output_dir: Path = Path("generated_images")):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        # API configurations
        self.apis = {
            'openai': {
                'available': bool(settings.openai_api_key),
                'rate_limit': 5,  # requests per minute
                'last_request': 0,
                'quality_score': 0.8
            },
            'stability': {
                'available': False,  # Would need Stability AI API key
                'rate_limit': 10,
                'last_request': 0,
                'quality_score': 0.7
            }
        }
        
        # Quality assessment cache
        self.quality_cache: Dict[str, float] = {}
        
    async def generate_all_panel_images(self, mission: Mission) -> Mission:
        """Generate images for all panels in a mission."""
        logger.info(f"Starting image generation for mission: {mission.id}")
        
        # Collect all panels
        all_panels = []
        for page in mission.pages:
            all_panels.extend(page.panels)
            
        # Create generation requests
        requests = []
        for panel in all_panels:
            if panel.visual_prompt:
                request = ImageGenerationRequest(
                    id=f"req_{panel.id}",
                    prompt=panel.visual_prompt,
                    panel_id=panel.id,
                    priority=self._calculate_priority(panel, mission)
                )
                requests.append(request)
                
        # Process requests in batches
        results = await self._process_generation_requests(requests)
        
        # Update panels with generated images
        for result in results:
            if result.success and result.panel_id:
                panel = self._find_panel_by_id(result.panel_id, mission)
                if panel:
                    panel.generated_image_path = result.image_path
                    
        logger.info(f"Generated {len([r for r in results if r.success])} images successfully")
        return mission
        
    async def _process_generation_requests(self, requests: List[ImageGenerationRequest]) -> List[ImageGenerationResult]:
        """Process image generation requests with rate limiting and retry logic."""
        results = []
        
        # Sort by priority
        requests.sort(key=lambda r: r.priority, reverse=True)
        
        # Process in batches to respect rate limits
        batch_size = 3
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = []
            for request in batch:
                task = asyncio.create_task(self._generate_single_image(request))
                batch_tasks.append(task)
                
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle results and exceptions
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Image generation failed: {result}")
                    results.append(ImageGenerationResult(
                        request_id="unknown",
                        success=False,
                        error_message=str(result),
                        generation_time=0.0,
                        api_used="unknown"
                    ))
                else:
                    results.append(result)
                    
            # Rate limiting delay between batches
            await asyncio.sleep(2)
            
        return results
        
    async def _generate_single_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate a single image with retry logic and API fallback."""
        start_time = time.time()
        
        # Try each available API
        for api_name, api_config in self.apis.items():
            if not api_config['available']:
                continue
                
            try:
                # Check rate limits
                await self._wait_for_rate_limit(api_name)
                
                # Generate image
                if api_name == 'openai':
                    result = await self._generate_openai_image(request)
                elif api_name == 'stability':
                    result = await self._generate_stability_image(request)
                else:
                    continue
                    
                if result.success:
                    result.generation_time = time.time() - start_time
                    result.api_used = api_name
                    return result
                    
            except Exception as e:
                logger.warning(f"API {api_name} failed: {e}")
                continue
                
        # All APIs failed
        return ImageGenerationResult(
            request_id=request.id,
            success=False,
            error_message="All image generation APIs failed",
            generation_time=time.time() - start_time,
            api_used="none"
        )
        
    async def _generate_openai_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate image using OpenAI DALL-E."""
        try:
            import openai
            
            client = openai.OpenAI(api_key=settings.openai_api_key)
            
            response = client.images.generate(
                model="dall-e-3",
                prompt=request.prompt,
                size=request.size,
                quality=request.quality,
                n=1
            )
            
            # Download and save image
            image_url = response.data[0].url
            image_path = await self._download_and_save_image(image_url, request.id)
            
            if image_path:
                quality_score = await self._assess_image_quality(image_path, request.prompt)
                
                return ImageGenerationResult(
                    request_id=request.id,
                    success=True,
                    image_path=str(image_path),
                    quality_score=quality_score,
                    generation_time=0.0,  # Will be set by caller
                    api_used="openai"
                )
            else:
                return ImageGenerationResult(
                    request_id=request.id,
                    success=False,
                    error_message="Failed to download image",
                    generation_time=0.0,
                    api_used="openai"
                )
                
        except Exception as e:
            return ImageGenerationResult(
                request_id=request.id,
                success=False,
                error_message=str(e),
                generation_time=0.0,
                api_used="openai"
            )
            
    async def _generate_stability_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate image using Stability AI (placeholder for future implementation)."""
        # This would be implemented when Stability AI API is available
        return ImageGenerationResult(
            request_id=request.id,
            success=False,
            error_message="Stability AI not implemented yet",
            generation_time=0.0,
            api_used="stability"
        )
        
    async def _download_and_save_image(self, image_url: str, request_id: str) -> Optional[Path]:
        """Download image from URL and save to disk."""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Create filename
            filename = f"{request_id}_{hashlib.md5(image_url.encode()).hexdigest()[:8]}.png"
            image_path = self.output_dir / filename
            
            # Save image
            with open(image_path, 'wb') as f:
                f.write(response.content)
                
            logger.info(f"Image saved: {image_path}")
            return image_path
            
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            return None
            
    async def _assess_image_quality(self, image_path: Path, prompt: str) -> float:
        """Assess the quality of generated image."""
        # Simple quality assessment based on file size and format
        try:
            with Image.open(image_path) as img:
                # Basic quality metrics
                width, height = img.size
                file_size = image_path.stat().st_size
                
                # Quality score based on resolution and file size
                resolution_score = min((width * height) / (1024 * 1024), 1.0)  # Max 1.0 for 1MP+
                size_score = min(file_size / (500 * 1024), 1.0)  # Max 1.0 for 500KB+
                
                # Combine scores
                quality_score = (resolution_score + size_score) / 2
                
                # Cache the result
                self.quality_cache[str(image_path)] = quality_score
                
                return quality_score
                
        except Exception as e:
            logger.warning(f"Quality assessment failed: {e}")
            return 0.5  # Default quality score
            
    async def _wait_for_rate_limit(self, api_name: str) -> None:
        """Wait for rate limit constraints."""
        api_config = self.apis[api_name]
        
        current_time = time.time()
        time_since_last = current_time - api_config['last_request']
        min_interval = 60.0 / api_config['rate_limit']  # seconds between requests
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            await asyncio.sleep(wait_time)
            
        api_config['last_request'] = time.time()
        
    def _calculate_priority(self, panel: Panel, mission: Mission) -> int:
        """Calculate priority for image generation."""
        priority = 1
        
        # Higher priority for action panels
        if panel.panel_type == 'action':
            priority += 2
            
        # Higher priority for panels with more characters
        if len(panel.characters) > 1:
            priority += 1
            
        # Higher priority for dramatic scenes
        scene = next((s for s in mission.scenes if s.id == panel.scene_id), None)
        if scene and scene.dramatic_tension > 0.7:
            priority += 2
            
        return priority
        
    def _find_panel_by_id(self, panel_id: str, mission: Mission) -> Optional[Panel]:
        """Find a panel by ID in the mission."""
        for page in mission.pages:
            for panel in page.panels:
                if panel.id == panel_id:
                    return panel
        return None
        
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about image generation."""
        stats = {
            'apis': {},
            'quality_stats': {},
            'total_images': len(self.quality_cache)
        }
        
        # API availability stats
        for api_name, api_config in self.apis.items():
            stats['apis'][api_name] = {
                'available': api_config['available'],
                'rate_limit': api_config['rate_limit']
            }
            
        # Quality statistics
        if self.quality_cache:
            qualities = list(self.quality_cache.values())
            stats['quality_stats'] = {
                'average': sum(qualities) / len(qualities),
                'min': min(qualities),
                'max': max(qualities)
            }
            
        return stats
        
    def clear_cache(self) -> None:
        """Clear quality assessment cache."""
        self.quality_cache.clear()
        
    def set_output_directory(self, output_dir: Path) -> None:
        """Set the output directory for generated images."""
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        
    async def regenerate_low_quality_images(self, mission: Mission, quality_threshold: float = 0.5) -> Mission:
        """Regenerate images that fall below quality threshold."""
        logger.info(f"Regenerating low quality images (threshold: {quality_threshold})")
        
        regeneration_requests = []
        
        for page in mission.pages:
            for panel in page.panels:
                if panel.generated_image_path:
                    quality = self.quality_cache.get(panel.generated_image_path, 0.5)
                    if quality < quality_threshold:
                        request = ImageGenerationRequest(
                            id=f"regen_{panel.id}",
                            prompt=panel.visual_prompt,
                            panel_id=panel.id,
                            priority=3  # High priority for regeneration
                        )
                        regeneration_requests.append(request)
                        
        if regeneration_requests:
            results = await self._process_generation_requests(regeneration_requests)
            
            # Update panels with new images
            for result in results:
                if result.success and result.panel_id:
                    panel = self._find_panel_by_id(result.panel_id, mission)
                    if panel:
                        panel.generated_image_path = result.image_path
                        
            logger.info(f"Regenerated {len([r for r in results if r.success])} images")
            
        return mission