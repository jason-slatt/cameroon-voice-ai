# src/services/llama/service.py
"""
LLaMA service - Simple chat
"""
import asyncio
from typing import Optional
import time

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

from src.core.exception import LLMInferenceError
from src.core.config import settings
from src.core.constants import CameroonLanguage
from src.core.logging import logger
import platform


class LlamaService:
    """LLaMA chat service"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._is_ready = False
        
    async def initialize(self) -> None:
        """Load model"""
        if self._is_ready:
            return
            
        logger.info("Loading LLaMA model...")
        start_time = time.time()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model_sync)
        
        load_time = time.time() - start_time
        logger.info(f"✅ LLaMA loaded in {load_time:.2f}s")
        self._is_ready = True
        
    def _load_model_sync(self) -> None:
        """Load model"""
        
        model_name = "distilgpt2"
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        quantization_config = None
        if settings.LLAMA_USE_QLORA and platform.system() != "Windows":
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True,
        )
        
        self.model.eval()
        
    async def generate_response(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        language: Optional[CameroonLanguage] = None,
    ) -> str:
        """Generate response"""
        
        if not self._is_ready:
            raise LLMInferenceError("Model not loaded")
        
        logger.info(f"Generating response...")
        
        prompt = self._build_prompt(user_message, language)
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._generate_sync, prompt)
        
        return response
        
    def _build_prompt(self, message: str, language: Optional[CameroonLanguage]) -> str:
        """Build prompt"""
        system = "You are a helpful assistant for people in Cameroon. Be friendly and concise."
        
        if language:
            system += f" Respond in {language.value}."
        
        prompt = f"<|system|>\n{system}</s>\n<|user|>\n{message}</s>\n<|assistant|>\n"
        return prompt
        
    def _generate_sync(self, prompt: str) -> str:
        """Generate"""
        
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        ).to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=settings.LLAMA_MAX_NEW_TOKENS,
                temperature=settings.LLAMA_TEMPERATURE,
                top_p=settings.LLAMA_TOP_P,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        input_length = inputs["input_ids"].shape[1]
        response_ids = outputs[0][input_length:]
        response = self.tokenizer.decode(response_ids, skip_special_tokens=True)
        
        return response.strip()
    
    def is_ready(self) -> bool:
        return self._is_ready
        
    async def cleanup(self) -> None:
        """Cleanup"""
        if self.model:
            del self.model
            del self.tokenizer
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                
        self._is_ready = False
        logger.info("LLaMA cleaned up")