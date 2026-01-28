from typing import List, Dict

class ModelRegistry:
    # Curated candidate models (optimized for Ollama pulling)
    CANDIDATES = [
        # TIER: Edge (1B-4B)
        {"id": "phi3:mini", "name": "Phi-3 Mini (3.8B)", "vram_gb": 4, "type": "General", "tier": "Edge", "reason": "High-efficiency general purpose model for restricted VRAM."},
        {"id": "tinyllama", "name": "TinyLlama (1.1B)", "vram_gb": 2, "type": "Edge", "tier": "Edge", "reason": "Ultralight model for testing baseline performance."},
        {"id": "stable-code", "name": "Stable Code (3B)", "vram_gb": 4, "type": "Code", "tier": "Edge", "reason": "Specialized for fast code completion on small hardware."},
        {"id": "qwen2:1.5b", "name": "Qwen 2 (1.5B)", "vram_gb": 3, "type": "General", "tier": "Edge", "reason": "Strong performance-to-size ratio from the Qwen family."},
        {"id": "granite-code:3b", "name": "IBM Granite Code (3B)", "vram_gb": 4, "type": "Code", "tier": "Edge", "reason": "Enterprise-grade code generation for edge devices."},
        
        # TIER: Mid (7B-14B)
        {"id": "llama3:8b", "name": "Llama 3 (8B)", "vram_gb": 8, "type": "General", "tier": "Mid", "reason": "Industry standard 8B model with excellent reasoning."},
        {"id": "mistral", "name": "Mistral (7B)", "vram_gb": 8, "type": "General", "tier": "Mid", "reason": "Versatile and reliable open-weights foundation."},
        {"id": "qwen2.5-coder:7b", "name": "Qwen 2.5 Coder (7B)", "vram_gb": 8, "type": "Code", "tier": "Mid", "reason": "Top-tier code intelligence in the 7B category."},
        {"id": "gemma2:9b", "name": "Gemma 2 (9B)", "vram_gb": 10, "type": "Reasoning", "tier": "Mid", "reason": "High-quality reasoning from Google's latest architecture."},
        {"id": "phi3:medium", "name": "Phi-3 Medium (14B)", "vram_gb": 14, "type": "General", "tier": "Mid", "reason": "Balanced power and speed for 16GB+ systems."},
        {"id": "codellama:7b", "name": "Code Llama (7B)", "vram_gb": 8, "type": "Code", "tier": "Mid", "reason": "Meta's specialized code-centric 7B model."},
        {"id": "neural-chat", "name": "Neural Chat (7B)", "vram_gb": 8, "type": "General", "tier": "Mid", "reason": "Fine-tuned for natural conversational flow."},
        
        # TIER: Large (30B+)
        {"id": "llama3:70b", "name": "Llama 3 (70B)", "vram_gb": 40, "type": "Reasoning", "tier": "Large", "reason": "State-of-the-art open reasoning for high-end GPUs."},
        {"id": "mixtral:8x7b", "name": "Mixtral (8x7B)", "vram_gb": 24, "type": "General", "tier": "Large", "reason": "High-throughput Mixture of Experts (MoE)."},
        {"id": "codestral", "name": "Codestral (22B)", "vram_gb": 18, "type": "Code", "tier": "Large", "reason": "Dense model optimized for advanced programming tasks."},
        {"id": "command-r", "name": "Command R (35B)", "vram_gb": 24, "type": "Tool Use", "tier": "Large", "reason": "Optimized for tool calling and RAG workflows."}
    ]

    @classmethod
    def get_candidates(cls) -> List[Dict]:
        return cls.CANDIDATES
