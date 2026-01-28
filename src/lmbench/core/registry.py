from typing import List, Dict

class ModelRegistry:
    # Curated candidate models (optimized for Ollama pulling)
    CANDIDATES = [
        # TIER: Edge (1B-4B)
        {"id": "phi3:mini", "name": "Phi-3 Mini (3.8B)", "vram_gb": 4, "type": "General", "tier": "Edge"},
        {"id": "tinyllama", "name": "TinyLlama (1.1B)", "vram_gb": 2, "type": "Edge", "tier": "Edge"},
        {"id": "stable-code", "name": "Stable Code (3B)", "vram_gb": 4, "type": "Code", "tier": "Edge"},
        {"id": "qwen2:1.5b", "name": "Qwen 2 (1.5B)", "vram_gb": 3, "type": "General", "tier": "Edge"},
        {"id": "granite-code:3b", "name": "IBM Granite Code (3B)", "vram_gb": 4, "type": "Code", "tier": "Edge"},
        
        # TIER: Mid (7B-14B)
        {"id": "llama3:8b", "name": "Llama 3 (8B)", "vram_gb": 8, "type": "General", "tier": "Mid"},
        {"id": "mistral", "name": "Mistral (7B)", "vram_gb": 8, "type": "General", "tier": "Mid"},
        {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder (7B)", "vram_gb": 8, "type": "Code", "tier": "Mid"},
        {"id": "gemma2:9b", "name": "Gemma 2 (9B)", "vram_gb": 10, "type": "Reasoning", "tier": "Mid"},
        {"id": "phi3:medium", "name": "Phi-3 Medium (14B)", "vram_gb": 14, "type": "General", "tier": "Mid"},
        {"id": "codellama:7b", "name": "Code Llama (7B)", "vram_gb": 8, "type": "Code", "tier": "Mid"},
        {"id": "neural-chat", "name": "Neural Chat (7B)", "vram_gb": 8, "type": "General", "tier": "Mid"},
        
        # TIER: Large (30B+)
        {"id": "llama3:70b", "name": "Llama 3 (70B)", "vram_gb": 40, "type": "Reasoning", "tier": "Large"},
        {"id": "mixtral", "name": "Mixtral (8x7B)", "vram_gb": 24, "type": "General", "tier": "Large"},
        {"id": "codestral", "name": "Codestral (22B)", "vram_gb": 18, "type": "Code", "tier": "Large"},
        {"id": "command-r", "name": "Command R (35B)", "vram_gb": 24, "type": "Tool Use", "tier": "Large"}
    ]

    @classmethod
    def get_candidates(cls) -> List[Dict]:
        return cls.CANDIDATES
