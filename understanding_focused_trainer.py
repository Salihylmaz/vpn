# fixed_understanding_trainer_v3.py
import os
import random
import math
import json
import torch
from typing import List, Dict, Optional
from datetime import datetime

import datasets as hf_datasets
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, TaskType, get_peft_model

from backend.elasticsearch_client_v8 import ElasticsearchClient

class ImprovedUnderstandingDataGenerator:
    """Geliştirilmiş anlama odaklı veri üreticisi"""
    
    def __init__(self, es_client=None):
        self.es_client = es_client
        
    def generate_comprehensive_training_data(self):
        """Kapsamlı eğitim verisi üretir"""
        
        all_pairs = []
        
        # 1. Temel kavram tanımları
        all_pairs.extend(self._generate_basic_concepts())
        
        # 2. Veri yapısı öğretimi
        all_pairs.extend(self._generate_data_structure_examples())
        
        # 3. Sorgu anlama patterns
        all_pairs.extend(self._generate_query_patterns())
        
        # 4. Zaman anlama
        all_pairs.extend(self._generate_time_understanding())
        
        # 5. Bağlam anlama
        all_pairs.extend(self._generate_context_examples())
        
        # 6. Gerçek veri örnekleri (varsa)
        if self.es_client:
            try:
                all_pairs.extend(self._generate_real_data_examples())
            except Exception as e:
                print(f"⚠️ Gerçek veri örnekleri eklenemedi: {e}")
        
        print(f"📊 Toplam {len(all_pairs)} eğitim örneği üretildi")
        return all_pairs
    
    def _generate_basic_concepts(self):
        """Temel kavramları öğret"""
        return [
            {
                "input": "CPU kullanımı %75 ne anlama gelir?",
                "output": "CPU kullanımı %75, işlemcinin orta-yüksek seviyede çalıştığını gösterir. Normal kullanım için biraz yüksek sayılır."
            },
            {
                "input": "RAM %90 dolu olması ne demek?",
                "output": "RAM %90 dolu olması, belleğin kritik seviyede olduğunu gösterir. Sistem yavaşlayabilir ve swap memory kullanmaya başlayabilir."
            },
            {
                "input": "VPN detected ne anlama gelir?",
                "output": "VPN detected, kullanıcının VPN (Virtual Private Network) kullandığını, yani IP adresinin gizlendiğini gösterir."
            },
            {
                "input": "Ping 150ms yüksek mi?",
                "output": "Evet, 150ms ping yüksek sayılır. İyi bir bağlantı için 50ms altı, kabul edilebilir için 100ms altı olmalıdır."
            },
            {
                "input": "Download speed 5 Mbps nasıl?",
                "output": "5 Mbps indirme hızı düşük sayılır. Temel internet kullanımı için minimum, video izleme için yetersiz olabilir."
            },
            {
                "input": "Disk kullanımı %95 tehlikeli mi?",
                "output": "Evet, disk kullanımı %95 tehlikelidir. Sistem donabilir, dosya kaydetme sorunları yaşanabilir. Acil disk temizliği gerekir."
            },
            {
                "input": "sistem yavaş ne demek?",
                "output": "Sistem yavaş genellikle CPU >%80, RAM >%90 veya disk >%95 olduğunda ortaya çıkar. Birden fazla metrik yüksekse kesin yavaştır."
            },
            {
                "input": "VPN kapalı mı?",
                "output": "VPN durumunu kontrol etmek için web_data.vpn_detection.status alanına bakmak gerekir. 'no_vpn' ise kapalı, 'vpn_detected' ise açık."
            }
        ]
    
    def _generate_data_structure_examples(self):
        """Veri yapısı örnekleri"""
        sample_data = {
            "collection_timestamp": "2024-01-15T14:30:00",
            "system_data": {
                "cpu": {"cpu_percent": 68.5, "core_count": 8},
                "memory": {
                    "virtual_memory": {
                        "percent": 72.1,
                        "used": 7516192768,
                        "total": 10737418240
                    }
                },
                "disk": {
                    "disk_usage": {
                        "main": {"percent": 45.8, "used": 107374182400, "total": 234567890123}
                    }
                }
            },
            "web_data": {
                "ip_address": "185.123.45.67",
                "vpn_detection": {"status": "no_vpn", "message": "Normal ISP connection"},
                "ip_info": {"city": "Istanbul", "country": "Turkey"},
                "speed_test": {"download_speed": 28.5, "upload_speed": 6.2, "ping": 22}
            }
        }
        
        return [
            {
                "input": f"Bu veride CPU bilgisi nerede?\n{json.dumps(sample_data['system_data']['cpu'], ensure_ascii=False)}",
                "output": "CPU bilgisi system_data.cpu.cpu_percent alanında bulunur. Bu örnekte %68.5 CPU kullanımı var, normal seviye."
            },
            {
                "input": f"Bu veride VPN kullanılıyor mu?\n{json.dumps(sample_data['web_data']['vpn_detection'], ensure_ascii=False)}",
                "output": "Hayır, VPN kullanılmıyor. vpn_detection.status 'no_vpn' olarak gözüküyor ve 'Normal ISP connection' mesajı var."
            },
            {
                "input": f"Bu sistemin bellek durumu nasıl?\n{json.dumps(sample_data['system_data']['memory'], ensure_ascii=False)}",
                "output": "Bellek %72.1 dolu (yaklaşık 7 GB / 10 GB kullanılıyor). Bu normal kullanım seviyesi, sorun yok."
            },
            {
                "input": f"Bu internet bağlantısı nasıl?\n{json.dumps(sample_data['web_data']['speed_test'], ensure_ascii=False)}",
                "output": "İnternet bağlantısı iyi durumda. 28.5 Mbps indirme hızı yeterli, 22ms ping düşük, 6.2 Mbps yükleme hızı normal."
            },
            {
                "input": "system_data.cpu.cpu_percent nerede bulunur?",
                "output": "system_data.cpu.cpu_percent, JSON verisinin sistem bilgileri bölümünde CPU kullanım yüzdesini gösterir."
            }
        ]
    
    def _generate_query_patterns(self):
        """Sorgu kalıplarını öğret"""
        return [
            {
                "input": "son 2 saatte VPN kullandım mı?",
                "output": "Bu sorgu son 2 saatlik zaman aralığında VPN durumunu sorgular. web_data.vpn_detection.status alanında 'vpn_detected' aranmalı."
            },
            {
                "input": "bugün sistem yavaş mıydı?",
                "output": "Bugünkü verilerde CPU >%80, RAM >%90 veya disk >%95 değerlerini kontrol etmek gerekir. Birden fazla metrik yüksekse sistem yavaştır."
            },
            {
                "input": "14:30'da internet hızım ne kadardı?",
                "output": "14:30 civarındaki (±30 dakika) verilerde web_data.speed_test.download_speed değerine bakmak gerekir."
            },
            {
                "input": "hangi ülkede görünüyordum?",
                "output": "En son verideki web_data.ip_info.country alanına bakmak gerekir. Bu konum bilgisini verir."
            },
            {
                "input": "bu hafta hangi bilgisayarların verisi var?",
                "output": "Bu haftalık zaman aralığında device_id ve user_id alanlarındaki benzersiz değerleri listelemek gerekir."
            },
            {
                "input": "bilgisayarım çok yavaş",
                "output": "Sistem performansını kontrol etmeliyim: CPU kullanımı, RAM kullanımı, disk kullanımı ve çalışan işlem sayısını incelemeliyim."
            },
            {
                "input": "internet problemim var",
                "output": "Ağ durumunu kontrol etmeliyim: internet hızı testi sonuçları, ping değeri, IP adresi değişiklikleri ve VPN durumunu incelemeliyim."
            }
        ]
    
    def _generate_time_understanding(self):
        """Zaman ifadelerini öğret"""
        return [
            {
                "input": "son 1 saat ne demek?",
                "output": "Son 1 saat, şu andan 1 saat geriye giden zaman aralığı. Elasticsearch range query ile collection_timestamp alanında arama yapılır."
            },
            {
                "input": "bugün ne zaman?",
                "output": "Bugün, günün başından (00:00) şu ana kadar olan zaman aralığı."
            },
            {
                "input": "dün akşam ne zaman?",
                "output": "Dün akşam, önceki günün 18:00-23:59 saatleri arası zaman dilimi."
            },
            {
                "input": "bu sabah ne zaman?",
                "output": "Bu sabah, bugünün 06:00-12:00 saatleri arası zaman dilimi."
            },
            {
                "input": "geçen hafta ne zaman?",
                "output": "Geçen hafta, 7 gün öncesinden bugüne kadar olan zaman aralığı."
            }
        ]
    
    def _generate_context_examples(self):
        """Bağlam anlama örnekleri"""
        return [
            {
                "input": "performans nasıl?",
                "output": "Sistem performansı için CPU, RAM ve disk kullanımına bakmam gerekir. Bu üç metriği de kontrol ederim."
            },
            {
                "input": "güvenlik durumu nedir?",
                "output": "Güvenlik için VPN durumu, IP adresi lokasyonu ve normal dışı ağ aktivitesi olup olmadığını kontrol ederim."
            },
            {
                "input": "bağlantı problemi var mı?",
                "output": "Bağlantı problemini kontrol etmek için internet hızı, ping değeri, IP değişiklikleri ve VPN durumunu incelerim."
            }
        ]
    
    def _generate_real_data_examples(self):
        """Gerçek veriden örnekler üret"""
        try:
            # Son 20 kaydı al
            query = {"query": {"match_all": {}}, "size": 20}
            results = self.es_client.search("combined-monitoring", query["query"], size=20)
            
            real_examples = []
            
            for hit in results[:5]:  # İlk 5 kayıt yeterli
                data = hit['_source']
                timestamp = data.get('collection_timestamp', '')[:16]
                
                # CPU örneği
                if data.get('system_data', {}).get('cpu', {}).get('cpu_percent'):
                    cpu_val = data['system_data']['cpu']['cpu_percent']
                    
                    real_examples.append({
                        "input": f"{timestamp} tarihinde CPU kullanımım nasıldı?",
                        "output": f"{timestamp} tarihinde CPU kullanımınız %{cpu_val}{'du. Yüksek seviye.' if cpu_val > 80 else 'di. Normal seviye.' if cpu_val > 50 else 'di. Düşük seviye.'}"
                    })
                
                # VPN örneği
                vpn_info = data.get('web_data', {}).get('vpn_detection', {})
                if vpn_info:
                    status = vpn_info.get('status', 'unknown')
                    real_examples.append({
                        "input": f"{timestamp} tarihinde VPN kullanıyor muydum?",
                        "output": f"{timestamp} tarihinde VPN durumunuz: {status}. {'VPN aktifti.' if status == 'vpn_detected' else 'VPN kullanmıyordunuz.' if status == 'no_vpn' else 'Durum belirsiz.'}"
                    })
            
            return real_examples
            
        except Exception as e:
            print(f"❌ Gerçek veri örnekleri oluşturulamadı: {e}")
            return []

def create_fixed_training_args(output_dir: str = "./qwen_understanding_model"):
    """Düzeltilmiş eğitim parametreleri"""
    return TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=1,  # Küçük batch size
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,  # Büyük effective batch için
        learning_rate=2e-5,
        warmup_steps=50,
        eval_strategy="steps",
        eval_steps=50,
        save_steps=100,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=10,
        save_total_limit=2,
        weight_decay=0.01,
        warmup_ratio=0.1,
        dataloader_pin_memory=False,
        fp16=torch.cuda.is_available(),
        dataloader_num_workers=0,
        remove_unused_columns=False,
        report_to=[],
        optim="adamw_torch",
        save_safetensors=True,
        seed=42,
        prediction_loss_only=True,
        group_by_length=True,  # Benzer uzunlukları grupla
    )

def create_optimized_lora_config():
    """Optimize edilmiş LoRA konfigürasyonu"""
    return LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,
        lora_alpha=16,
        lora_dropout=0.05,
        target_modules=[
            "q_proj",
            "k_proj", 
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        bias="none",
        inference_mode=False,
    )

def tokenize_function(examples, tokenizer, max_length=512):
    """DÜZELTILMIŞ Tokenization fonksiyonu"""
    
    # Girdi metinlerini al
    texts = examples["text"]
    
    # Her metin için tokenize et - padding=False, truncation=True
    model_inputs = tokenizer(
        texts,
        truncation=True,
        padding=False,  # Burada padding yapmıyoruz, DataCollator yapacak
        max_length=max_length,
        return_tensors=None  # Tensor olarak değil, liste olarak döndür
    )
    
    # Labels'ı input_ids'in kopyası yap
    model_inputs["labels"] = [ids.copy() for ids in model_inputs["input_ids"]]
    
    return model_inputs

def format_training_example(pair: Dict[str, str]) -> str:
    """Eğitim örneğini format'la"""
    input_text = pair.get("input", "").strip()
    output_text = pair.get("output", "").strip()
    
    # Qwen instruct format
    return f"<|im_start|>user\n{input_text}<|im_end|>\n<|im_start|>assistant\n{output_text}<|im_end|>"

def prepare_dataset(training_pairs: List[Dict], tokenizer, max_length: int = 512):
    """DÜZELTILMIŞ Dataset hazırlama"""
    
    # Train/validation böl
    random.shuffle(training_pairs)
    split_idx = max(1, int(len(training_pairs) * 0.85))
    train_pairs = training_pairs[:split_idx]
    eval_pairs = training_pairs[split_idx:] if split_idx < len(training_pairs) else train_pairs[-3:]
    
    # Format'la
    train_texts = [format_training_example(pair) for pair in train_pairs]
    eval_texts = [format_training_example(pair) for pair in eval_pairs]
    
    print(f"📚 Eğitim seti: {len(train_texts)} örnek")
    print(f"📝 Değerlendirme seti: {len(eval_texts)} örnek")
    
    # HuggingFace Dataset oluştur
    train_dataset = hf_datasets.Dataset.from_dict({"text": train_texts})
    eval_dataset = hf_datasets.Dataset.from_dict({"text": eval_texts})
    
    # Tokenize et - remove_columns doğru şekilde
    train_dataset = train_dataset.map(
        lambda examples: tokenize_function(examples, tokenizer, max_length),
        batched=True,
        remove_columns=train_dataset.column_names,  # Tüm orijinal sütunları kaldır
        desc="Tokenizing train dataset"
    )
    
    eval_dataset = eval_dataset.map(
        lambda examples: tokenize_function(examples, tokenizer, max_length),
        batched=True,
        remove_columns=eval_dataset.column_names,  # Tüm orijinal sütunları kaldır
        desc="Tokenizing eval dataset"
    )
    
    return train_dataset, eval_dataset

class CustomTrainer(Trainer):
    """Özelleştirilmiş Trainer"""
    
    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        """Loss hesaplama"""
        labels = inputs.get("labels")
        outputs = model(**inputs)
        
        # Shift so that tokens < n predict n
        shift_logits = outputs.logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        
        # Flatten the tokens
        loss_fct = torch.nn.CrossEntropyLoss()
        shift_logits = shift_logits.view(-1, shift_logits.size(-1))
        shift_labels = shift_labels.view(-1)
        
        # Enable model parallelism
        shift_labels = shift_labels.to(shift_logits.device)
        loss = loss_fct(shift_logits, shift_labels)
        
        return (loss, outputs) if return_outputs else loss

def debug_dataset(train_dataset, eval_dataset, tokenizer):
    """Dataset debug bilgileri"""
    print("\n🔍 Dataset Debug Bilgileri:")
    print("-" * 40)
    
    # Train dataset
    print(f"📚 Train dataset boyutu: {len(train_dataset)}")
    print(f"📚 Train sütunları: {train_dataset.column_names}")
    
    # İlk örneği incele
    if len(train_dataset) > 0:
        first_example = train_dataset[0]
        print(f"📝 İlk örnek anahtarları: {list(first_example.keys())}")
        
        if 'input_ids' in first_example:
            input_length = len(first_example['input_ids'])
            print(f"📏 İlk örnek input_ids uzunluğu: {input_length}")
            
            # İlk birkaç token'ı decode et
            if input_length > 0:
                sample_text = tokenizer.decode(first_example['input_ids'][:min(50, input_length)])
                print(f"📄 İlk 50 token örneği: {sample_text[:100]}...")
    
    # Eval dataset
    print(f"📝 Eval dataset boyutu: {len(eval_dataset)}")
    print(f"📝 Eval sütunları: {eval_dataset.column_names}")
    
    # Uzunluk dağılımı
    if len(train_dataset) > 0 and 'input_ids' in train_dataset[0]:
        lengths = [len(example['input_ids']) for example in train_dataset]
        print(f"📊 Uzunluk istatistikleri:")
        print(f"   Min: {min(lengths)}, Max: {max(lengths)}, Ortalama: {sum(lengths)/len(lengths):.1f}")

def train_understanding_model(
    base_model: str = "Qwen/Qwen2.5-3B-Instruct",
    output_dir: str = "./qwen_understanding_model",
    include_real_data: bool = False,
    max_seq_length: int = 512
):
    """Ana eğitim fonksiyonu - DÜZELTILMIŞ"""
    
    print(f"🚀 Fine-tuning başlıyor...")
    print(f"📋 Base model: {base_model}")
    print(f"📁 Output: {output_dir}")
    
    # 1. Model ve tokenizer yükle
    print("📥 Model yükleniyor...")
    hf_token = os.environ.get("HF_TOKEN")
    
    tokenizer = AutoTokenizer.from_pretrained(
        base_model, 
        use_fast=True, 
        token=hf_token,
        trust_remote_code=True
    )
    
    # Pad token ekle - QWEN için önemli
    if tokenizer.pad_token is None:
        tokenizer.add_special_tokens({'pad_token': '<|endoftext|>'})
    
    # Model yükleme
    device_map = "auto" if torch.cuda.is_available() else None
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch_dtype,
        device_map=device_map,
        token=hf_token,
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    
    # Tokenizer resize (pad token ekledik)
    if len(tokenizer) > model.config.vocab_size:
        model.resize_token_embeddings(len(tokenizer))
    
    # 2. LoRA uygula
    print("🔧 LoRA konfigürasyonu uygulanıyor...")
    lora_config = create_optimized_lora_config()
    
    # Model'i PEFT için hazırla
    if hasattr(model, 'gradient_checkpointing_enable'):
        model.gradient_checkpointing_enable()
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # 3. Eğitim verisi üret
    print("📊 Eğitim verisi üretiliyor...")
    es_client = None
    if include_real_data:
        try:
            es_client = ElasticsearchClient()
        except Exception as e:
            print(f"⚠️ Elasticsearch bağlantısı kurulamadı, sadece sentetik veri kullanılacak: {e}")
    
    generator = ImprovedUnderstandingDataGenerator(es_client)
    training_pairs = generator.generate_comprehensive_training_data()
    
    if len(training_pairs) < 5:
        print("❌ Eğitim verisi yetersiz!")
        return None
    
    # 4. Dataset hazırla
    print("🗂️ Dataset hazırlanıyor...")
    train_dataset, eval_dataset = prepare_dataset(training_pairs, tokenizer, max_seq_length)
    
    # 5. Debug bilgileri
    debug_dataset(train_dataset, eval_dataset, tokenizer)
    
    # 6. DÜZELTILMIŞ Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,  # Causal LM için
        pad_to_multiple_of=8 if torch.cuda.is_available() else None,
        return_tensors="pt"
    )
    
    # 7. Training arguments
    training_args = create_fixed_training_args(output_dir)
    
    # 8. Trainer oluştur
    print("🎯 Trainer oluşturuluyor...")
    trainer = CustomTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )
    
    # 9. Eğitimi çalıştır
    print("🏃‍♂️ Eğitim başlatılıyor...")
    try:
        trainer.train()
        print("✅ Eğitim tamamlandı!")
        
        # Model ve tokenizer'ı kaydet
        trainer.save_model()
        tokenizer.save_pretrained(output_dir)
        
        print(f"💾 Model kaydedildi: {output_dir}")
        
        # Merge edilmiş versiyonu da kaydet
        try:
            print("🔗 Model merge ediliyor...")
            merged_dir = os.path.join(output_dir, "merged")
            os.makedirs(merged_dir, exist_ok=True)
            
            # Merge ve kaydet
            merged_model = model.merge_and_unload()
            merged_model.save_pretrained(merged_dir)
            tokenizer.save_pretrained(merged_dir)
            
            print(f"✅ Merge edilmiş model kaydedildi: {merged_dir}")
            
        except Exception as merge_error:
            print(f"⚠️ Model merge edilemedi: {merge_error}")
            print("💡 LoRA adapter modeli kullanılabilir durumda.")
        
        return output_dir
        
    except Exception as training_error:
        print(f"❌ Eğitim hatası: {training_error}")
        import traceback
        traceback.print_exc()
        raise

def test_trained_model(model_path: str):
    """Eğitilmiş modeli test et"""
    print(f"\n🧪 Model testi başlıyor: {model_path}")
    
    try:
        # Test için merged model varsa onu kullan
        merged_path = os.path.join(model_path, "merged")
        test_path = merged_path if os.path.isdir(merged_path) else model_path
        
        print(f"📍 Test edilen model: {test_path}")
        
        tokenizer = AutoTokenizer.from_pretrained(test_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            test_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        )
        
        # Test soruları
        test_questions = [
            "CPU %85 yüksek mi?",
            "VPN aktif ne demek?", 
            "son 2 saatte sistem nasıldı?",
            "RAM %95 ne anlama gelir?",
            "internet hızım nasıl?"
        ]
        
        print("\n📋 Test sonuçları:")
        print("-" * 60)
        
        for i, question in enumerate(test_questions, 1):
            # Qwen format
            prompt = f"<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant\n"
            
            inputs = tokenizer(prompt, return_tensors="pt")
            if torch.cuda.is_available():
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=80,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id,
                    repetition_penalty=1.1
                )
            
            response = tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:], 
                skip_special_tokens=True
            ).strip()
            
            print(f"{i}. ❓ {question}")
            print(f"   🤖 {response}")
            print()
        
        print("✅ Model test tamamlandı!")
        return True
        
    except Exception as e:
        print(f"❌ Model test hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dependencies():
    """Gerekli kütüphaneleri kontrol et"""
    required_packages = ['torch', 'transformers', 'peft', 'datasets']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Eksik kütüphaneler bulundu: {', '.join(missing)}")
        print("💡 Kurulum için:")
        print(f"   pip install {' '.join(missing)}")
        return False
    
    print("✅ Tüm kütüphaneler yüklü.")
    return True


def main():
    """Anlama (understanding) odaklı fine-tuning'i çalıştır ve testi yap"""
    if not check_dependencies():
        return
    
    # Eğitim
    output_dir = train_understanding_model(
        base_model="Qwen/Qwen2.5-3B-Instruct",
        output_dir="./qwen_understanding_model",
        include_real_data=True,
        max_seq_length=512,
    )
    
    # Test
    if output_dir:
        test_trained_model(output_dir)


if __name__ == "__main__":
    main()