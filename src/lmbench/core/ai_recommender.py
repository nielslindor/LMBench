import httpx
import asyncio
import json
from typing import List, Dict, Optional
from rich.console import Console

class AIRecommender:
    def __init__(self, backend_url: str):
        self.url = backend_url
        self.console = Console()
        self.recommender_model_id = "tinyllama" # Default small model for recommendation

    async def _load_model(self, model_id: str):
        async with httpx.AsyncClient(timeout=None) as client:
            try:
                payload = {"model": model_id, "stream": False}
                response = await client.post(f"{self.url}/api/generate", json=payload) # Use generate endpoint for loading check
                if response.status_code == 200:
                    # Check if response indicates success (e.g., model is loaded or available)
                    # This is a heuristic; a dedicated endpoint would be better
                    return True 
            except Exception:
                pass
        return False

    async def _unload_model(self, model_id: str):
        # Ollama specific unload
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(f"{self.url}/api/delete", json={"name": model_id})
            except Exception:
                pass # Ignore errors on unload

    async def get_recommendations(self, system_info: Dict) -> List[Dict]:
        """
        Use a transient AI model to recommend LLMs based on system_info.
        """
        if not await self._load_model(self.recommender_model_id):
            self.console.print(f"[yellow]Warning: Could not load recommender model '{self.recommender_model_id}'. Falling back to heuristic recommendations.[/yellow]")
            # Fallback to existing heuristic recommender
            from .recommender import Recommender
            heuristic_rec = Recommender(system_info)
            return heuristic_rec.select_top_10() # Return heuristic recs

        # Prepare prompt for AI recommender
        prompt = f"""
        System: You are an AI assistant specialized in recommending local LLMs based on hardware.
        User: My system has the following specifications:
        - OS: {system_info.get('os')}
        - Architecture: {system_info.get('arch')}
        - CPU: {system_info.get('cpu')}
        - RAM: {system_info['ram_available_gb']}GB available / {system_info['ram_total_gb']}GB total
        - GPU: {', '.join([f"{g['name']} ({g['vram_total_gb']}GB VRAM)" for g in system_info.get('gpus', [])])}

        Based on this hardware, please recommend ~10 diverse and high-quality LLM models suitable for benchmarking. Prioritize models that fit within the detected VRAM. Categorize them by their primary use case (Code, Reasoning, General, Tool Use).
        Your output MUST be a single JSON array of objects, where each object has: "id" (for pulling), "name" (display name), "vram_gb" (estimated VRAM), "type" (e.g., 'Code'), and "tier" (e.g., 'Mid').
        """

        recommendations = []
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                payload = {
                    "model": self.recommender_model_id,
                    "prompt": prompt,
                    "stream": True
                }
                async with client.stream("POST", f"{self.url}/api/generate", json=payload) as response:
                    full_response = ""
                    async for line in response.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            if chunk.get("done"):
                                # Parse the final JSON response
                                if "response" in chunk:
                                    full_response += chunk["response"]
                                break
                            elif "response" in chunk:
                                full_response += chunk["response"]
                
                # Attempt to parse JSON from the collected response
                import json
                recommendations = json.loads(full_response)

        except Exception as e:
            self.console.print(f"[yellow]Warning: Failed to get AI recommendations: {e}. Falling back to heuristic.[/yellow]")
            # Fallback to heuristic
            from .recommender import Recommender
            heuristic_rec = Recommender(system_info)
            recommendations = heuristic_rec.select_top_10()

        finally:
            # Unload the recommender model
            await self._unload_model(self.recommender_model_id)
            
        return recommendations

def run_ai_recommendations(backend_url: str, system_info: Dict):
    recommender_instance = AIRecommender(backend_url)
    return asyncio.run(recommender_instance.get_recommendations(system_info))
