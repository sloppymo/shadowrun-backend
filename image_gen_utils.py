import os
import json
import time
import asyncio
import httpx
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime

class ImageGenerationError(Exception):
    """Custom exception for image generation errors"""
    pass

class ImageGenerator:
    """Handles image generation with multiple providers"""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.stability_api_key = os.getenv("STABILITY_API_KEY")
        self.replicate_api_key = os.getenv("REPLICATE_API_TOKEN")
        
    async def enhance_prompt_for_shadowrun(self, original_prompt: str, context: str = "") -> str:
        """Use LLM to enhance prompts specifically for Shadowrun imagery"""
        enhancement_prompt = f"""
        Transform this Shadowrun scene description into a detailed, visual prompt for AI image generation.
        Focus on cyberpunk aesthetics, neon lighting, urban decay, and high-tech/low-life atmosphere.
        
        Original description: {original_prompt}
        Additional context: {context}
        
        Enhanced prompt should include:
        - Specific visual details (lighting, colors, atmosphere)
        - Shadowrun-appropriate technology and setting elements
        - Composition and framing suggestions
        - Art style keywords (cyberpunk, neo-noir, dystopian)
        
        Keep it under 500 characters for optimal generation results.
        """
        
        # Import from llm_utils if available
        try:
            from llm_utils import call_llm
            messages = [{"role": "user", "content": enhancement_prompt}]
            enhanced = await call_llm("openai", messages, model_name="gpt-4o-mini")
            return enhanced.strip()
        except Exception as e:
            print(f"Prompt enhancement failed: {e}")
            # Fallback to basic enhancement
            return self._basic_prompt_enhancement(original_prompt)
    
    def _basic_prompt_enhancement(self, prompt: str) -> str:
        """Basic prompt enhancement without LLM"""
        shadowrun_keywords = [
            "cyberpunk aesthetic", "neon lighting", "urban decay", 
            "high-tech low-life", "dystopian atmosphere", "chrome and shadows",
            "rain-soaked streets", "holographic displays", "corporate towers"
        ]
        
        enhanced = f"{prompt}, {', '.join(shadowrun_keywords[:3])}, cinematic lighting, detailed, 4k"
        return enhanced
    
    async def generate_with_dalle(self, prompt: str, size: str = "1024x1024", quality: str = "standard", **kwargs) -> Dict[str, Any]:
        """Generate image using DALL-E 3"""
        if not self.openai_api_key:
            raise ImageGenerationError("OpenAI API key not configured")
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "size": size,
                        "quality": quality,
                        "response_format": "url"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                generation_time = time.time() - start_time
                
                return {
                    "success": True,
                    "image_url": data["data"][0]["url"],
                    "revised_prompt": data["data"][0].get("revised_prompt", prompt),
                    "generation_time": generation_time,
                    "provider": "dalle"
                }
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if e.response else str(e)
                raise ImageGenerationError(f"DALL-E API error: {e.response.status_code} - {error_detail}")
            except Exception as e:
                raise ImageGenerationError(f"DALL-E generation failed: {str(e)}")
    
    async def generate_with_stability(self, prompt: str, style_preset: str = "cyberpunk", **kwargs) -> Dict[str, Any]:
        """Generate image using Stability AI"""
        if not self.stability_api_key:
            raise ImageGenerationError("Stability AI API key not configured")
        
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.stability_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "text_prompts": [{"text": prompt}],
                        "cfg_scale": 7,
                        "height": 1024,
                        "width": 1024,
                        "samples": 1,
                        "steps": 30,
                        "style_preset": style_preset
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                generation_time = time.time() - start_time
                
                # Stability returns base64 encoded images
                image_data = base64.b64decode(data["artifacts"][0]["base64"])
                
                # In production, you'd save this to cloud storage
                # For now, we'll return a placeholder URL
                image_url = f"data:image/png;base64,{data['artifacts'][0]['base64']}"
                
                return {
                    "success": True,
                    "image_url": image_url,
                    "image_data": image_data,
                    "generation_time": generation_time,
                    "provider": "stability"
                }
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if e.response else str(e)
                raise ImageGenerationError(f"Stability AI error: {e.response.status_code} - {error_detail}")
            except Exception as e:
                raise ImageGenerationError(f"Stability AI generation failed: {str(e)}")
    
    async def generate_image(self, prompt: str, provider: str = "dalle", **kwargs) -> Dict[str, Any]:
        """Generate image with specified provider"""
        enhanced_prompt = await self.enhance_prompt_for_shadowrun(prompt, kwargs.get("context", ""))
        
        if provider == "dalle":
            return await self.generate_with_dalle(enhanced_prompt, **kwargs)
        elif provider == "stability":
            return await self.generate_with_stability(enhanced_prompt, **kwargs)
        else:
            raise ImageGenerationError(f"Unsupported provider: {provider}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available image generation providers"""
        providers = []
        if self.openai_api_key:
            providers.append("dalle")
        if self.stability_api_key:
            providers.append("stability")
        return providers

# Utility functions for database operations
async def create_image_generation_request(session_id: str, user_id: str, prompt: str, 
                                        request_type: str = "scene", priority: int = 1, 
                                        style_preferences: Dict = None) -> str:
    """Create a new image generation request"""
    from app import db, ImageGeneration
    
    request = ImageGeneration(
        session_id=session_id,
        user_id=user_id,
        request_type=request_type,
        context=prompt,
        style_preferences=json.dumps(style_preferences or {}),
        priority=priority
    )
    
    db.session.add(request)
    db.session.commit()
    
    return request.id

async def process_image_generation(request_id: str) -> Dict[str, Any]:
    """Process a queued image generation request"""
    from app import db, ImageGeneration, GeneratedImage
    
    request = ImageGeneration.query.get(request_id)
    if not request:
        raise ImageGenerationError("Generation request not found")
    
    # Update status to processing
    request.status = "processing"
    request.started_at = datetime.utcnow()
    db.session.commit()
    
    try:
        generator = ImageGenerator()
        style_prefs = json.loads(request.style_preferences or "{}")
        provider = style_prefs.get("provider", "dalle")
        
        # Generate the image
        result = await generator.generate_image(
            request.context,
            provider=provider,
            context=f"Session: {request.session_id}, Type: {request.request_type}",
            **style_prefs
        )
        
        # Create GeneratedImage record
        generated_image = GeneratedImage(
            session_id=request.session_id,
            user_id=request.user_id,
            prompt=request.context,
            enhanced_prompt=result.get("revised_prompt", request.context),
            image_url=result["image_url"],
            provider=result["provider"],
            status="completed",
            generation_time=result["generation_time"],
            completed_at=datetime.utcnow()
        )
        
        db.session.add(generated_image)
        
        # Update request status
        request.status = "completed"
        request.result_image_id = generated_image.id
        request.completed_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            "success": True,
            "request_id": request_id,
            "image_id": generated_image.id,
            "image_url": result["image_url"],
            "generation_time": result["generation_time"]
        }
        
    except Exception as e:
        # Update request with error
        request.status = "failed"
        request.retry_count += 1
        request.completed_at = datetime.utcnow()
        
        # Create failed GeneratedImage record for tracking
        failed_image = GeneratedImage(
            session_id=request.session_id,
            user_id=request.user_id,
            prompt=request.context,
            provider=style_prefs.get("provider", "dalle"),
            status="failed",
            error_message=str(e),
            completed_at=datetime.utcnow()
        )
        
        db.session.add(failed_image)
        request.result_image_id = failed_image.id
        db.session.commit()
        
        return {
            "success": False,
            "request_id": request_id,
            "error": str(e)
        }

async def get_session_images(session_id: str, user_id: str = None, limit: int = 20) -> List[Dict]:
    """Get generated images for a session"""
    from app import GeneratedImage
    
    query = GeneratedImage.query.filter_by(session_id=session_id)
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    images = query.order_by(GeneratedImage.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": img.id,
            "prompt": img.prompt,
            "image_url": img.image_url,
            "provider": img.provider,
            "status": img.status,
            "created_at": img.created_at.isoformat(),
            "is_favorite": img.is_favorite,
            "tags": json.loads(img.tags) if img.tags else []
        }
        for img in images
    ] 