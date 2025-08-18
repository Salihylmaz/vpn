import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import os
from huggingface_hub import snapshot_download
import json

class ModelDownloader:
    def __init__(self):
        self.models = {
            "codellama": "codellama/CodeLlama-7b-Instruct-hf",
        }
        
        # GPU kontrolü
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔧 Cihaz: {self.device}")
        
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            print(f"🎮 GPU: {gpu_name}")
            print(f"💾 VRAM: {vram:.1f} GB")

    def download_model(self, model_key="codellama", use_4bit=True):
        """Model indir ve yükle"""
        
        if model_key not in self.models:
            print(f"❌ Geçersiz model. Mevcut: {list(self.models.keys())}")
            return None, None
            
        model_name = self.models[model_key]
        print(f"📥 {model_name} indiriliyor...")
        
        try:
            # Quantization ayarları (VRAM tasarrufu için)
            if use_4bit and self.device == "cuda":
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
                print("🔧 4-bit quantization aktif")
            else:
                bnb_config = None
            
            # Tokenizer indir
            print("📝 Tokenizer yükleniyor...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True
            )
            
            # Model indir
            print("🤖 Model yükleniyor... (Bu biraz zaman alabilir)")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto" if self.device == "cuda" else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            print("✅ Model başarıyla yüklendi!")
            
            # Model bilgileri kaydet
            model_info = {
                "name": model_name,
                "device": self.device,
                "quantized": use_4bit,
                "parameters": sum(p.numel() for p in model.parameters()) / 1e9
            }
            
            with open(f"model_info_{model_key}.json", "w") as f:
                json.dump(model_info, f, indent=2)
            
            print(f"📊 Model bilgileri: {model_info['parameters']:.1f}B parametreli")
            
            return model, tokenizer
            
        except Exception as e:
            print(f"❌ Hata: {e}")
            return None, None
    
    def test_model(self, model, tokenizer, prompt="Generate Elasticsearch query for today's logs"):
        """Model test et"""
        try:
            print(f"🧪 Test başlıyor: '{prompt[:50]}...'")
            
            # Input hazırla
            inputs = tokenizer.encode(prompt, return_tensors="pt")
            if self.device == "cuda":
                inputs = inputs.to("cuda")
            
            # Generate
            with torch.no_grad():
                outputs = model.generate(
                    inputs,
                    max_new_tokens=200,
                    temperature=0.1,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            # Decode
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            print("✅ Model testi başarılı!")
            print(f"📤 Cevap: {response[len(prompt):][:200]}...")
            
            return True
            
        except Exception as e:
            print(f"❌ Test hatası: {e}")
            return False
    
    def download_offline(self, model_key="codellama"):
        """Modeli tamamen offline kullanım için indir"""
        model_name = self.models[model_key]
        
        try:
            print(f"📦 {model_name} offline indiriliyor...")
            
            # Model dosyalarını indir
            cache_dir = snapshot_download(
                repo_id=model_name,
                cache_dir="./models/",
                resume_download=True
            )
            
            print(f"✅ Model indirildi: {cache_dir}")
            return cache_dir
            
        except Exception as e:
            print(f"❌ Offline indirme hatası: {e}")
            return None

def main():
    """Ana fonksiyon"""
    downloader = ModelDownloader()
    
    print("🚀 Hugging Face Model Downloader")
    print("Mevcut modeller:")
    for key, name in downloader.models.items():
        print(f"  {key}: {name}")
    
    # Model seç
    model_choice = input("\nHangi modeli indirmek istiyorsunuz? (codellama): ").strip()
    if not model_choice:
        model_choice = "codellama"
    
    # 4-bit quantization
    use_4bit = input("4-bit quantization kullanılsın mı? (y/N): ").lower() == 'y'
    
    # Model indir
    model, tokenizer = downloader.download_model(model_choice, use_4bit)
    
    if model and tokenizer:
        # Test et
        test_prompt = input("Test prompt'u (Enter=varsayılan): ").strip()
        if not test_prompt:
            test_prompt = "Create Elasticsearch query to find system logs from today"
        
        downloader.test_model(model, tokenizer, test_prompt)
        
        # Kaydet
        save_path = f"./models/{model_choice}"
        try:
            model.save_pretrained(save_path)
            tokenizer.save_pretrained(save_path)
            print(f"💾 Model kaydedildi: {save_path}")
        except Exception as e:
            print(f"⚠️  Kaydetme hatası: {e}")

if __name__ == "__main__":
    main()