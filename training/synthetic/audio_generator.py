# training/synthetic/audio_generator.py
"""
Generate synthetic audio using Google TTS
"""
from gtts import gTTS
from pathlib import Path
import uuid
from typing import List, Dict
import json

from src.core.logging import logger


class SyntheticAudioGenerator:
    """Generate audio files from text using TTS"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_audio_dataset(
        self,
        samples: List[Dict],
        language: str = "fr"
    ) -> List[Dict]:
        """
        Generate audio files for each text sample
        
        Args:
            samples: List of {text, intent, entities}
            language: Language code (fr, en)
            
        Returns:
            List with added 'audio_path' field
        """
        logger.info(f"Generating {len(samples)} audio files...")
        
        dataset = []
        
        for i, sample in enumerate(samples):
            try:
                # Generate unique filename
                audio_id = uuid.uuid4()
                filename = f"{sample['intent']}_{audio_id}.mp3"
                audio_path = self.output_dir / filename
                
                # Generate audio with gTTS
                tts = gTTS(text=sample['text'], lang=language, slow=False)
                tts.save(str(audio_path))
                
                # Add to dataset
                dataset.append({
                    **sample,
                    "audio_path": str(audio_path),
                    "audio_id": str(audio_id),
                })
                
                if (i + 1) % 50 == 0:
                    logger.info(f"Generated {i + 1}/{len(samples)} audio files")
                    
            except Exception as e:
                logger.error(f"Failed to generate audio for: {sample['text'][:50]}... Error: {e}")
                continue
        
        logger.info(f"✅ Generated {len(dataset)} audio files")
        return dataset
    
    def save_dataset(self, dataset: List[Dict], output_file: Path):
        """Save dataset to JSON"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Dataset saved to {output_file}")


# Usage
if __name__ == "__main__":
    from phrase_templates import BankingPhraseGenerator
    
    # Generate phrases
    generator = BankingPhraseGenerator()
    samples = generator.generate_samples(n_per_intent=100)
    
    # Generate audio
    audio_gen = SyntheticAudioGenerator(
        output_dir=Path("./data/synthetic/audio")
    )
    
    dataset = audio_gen.generate_audio_dataset(samples)
    
    # Save
    audio_gen.save_dataset(
        dataset,
        Path("./data/synthetic/banking_dataset.json")
    )
    
    print(f"✅ Complete dataset with {len(dataset)} samples ready!")