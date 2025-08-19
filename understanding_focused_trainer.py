# understanding_focused_trainer.py
import os
import random
import math
from typing import List, Dict

import datasets as hf_datasets
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
)
from peft import LoraConfig, TaskType
from trl import SFTTrainer

from elasticsearch_client_v8 import ElasticsearchClient
from understanding_focused_data_generator import (
    UnderstandingFocusedDataGenerator,
    generate_real_data_understanding,
)
from understanding_tester import run_understanding_evaluation


def create_understanding_focused_training_args(output_dir: str = "./qwen_understanding_model"):
    """Anlama odaklı eğitim parametreleri"""
    return TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=6,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=1e-5,
        warmup_steps=200,
        evaluation_strategy="steps",
        eval_steps=100,
        save_steps=200,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=10,
        save_total_limit=3,
        weight_decay=0.1,
        warmup_ratio=0.1,
        dataloader_pin_memory=False,
        fp16=True,
        dataloader_num_workers=0,
        remove_unused_columns=False,
        report_to=["none"],
    )


def create_understanding_lora_config():
    """Anlama odaklı LoRA konfigürasyonu"""
    return LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=64,
        lora_alpha=128,
        lora_dropout=0.2,
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


def format_pair_to_text(pair: Dict[str, str]) -> str:
    """Çiftleri tek bir öğretim metnine dönüştürür."""
    instruction = pair.get("instruction", "").strip()
    input_text = pair.get("input", "").strip()
    output_text = pair.get("output", "").strip()

    if input_text:
        return f"Soru: {instruction}\nVeri: {input_text}\nYanıt: {output_text}"
    return f"Soru: {instruction}\nYanıt: {output_text}"


def build_training_dataset(include_real_data: bool = True, real_limit: int = 100) -> hf_datasets.DatasetDict:
    """Generator ve opsiyonel gerçek veriden HF Dataset oluştur."""
    # ES istemcisi (gerekirse)
    es_client = None
    if include_real_data:
        try:
            es_client = ElasticsearchClient()
        except Exception:
            es_client = None

    # Sentetik anlama çiftleri
    generator = UnderstandingFocusedDataGenerator(es_client)
    synthetic_pairs = generator.generate_understanding_pairs()

    # Opsiyonel gerçek veri temelli çiftler
    real_pairs: List[Dict[str, str]] = []
    if es_client is not None:
        try:
            real_pairs = generate_real_data_understanding(es_client, limit=real_limit)
        except Exception:
            real_pairs = []

    all_pairs = synthetic_pairs + real_pairs
    random.shuffle(all_pairs)

    # Train/val böl
    split_idx = max(1, int(len(all_pairs) * 0.9))
    train_pairs = all_pairs[:split_idx]
    eval_pairs = all_pairs[split_idx:]
    if not eval_pairs:
        eval_pairs = train_pairs[-max(1, math.floor(len(train_pairs) * 0.1)) :]

    train_texts = [format_pair_to_text(p) for p in train_pairs]
    eval_texts = [format_pair_to_text(p) for p in eval_pairs]

    train_ds = hf_datasets.Dataset.from_dict({"text": train_texts})
    eval_ds = hf_datasets.Dataset.from_dict({"text": eval_texts})
    return hf_datasets.DatasetDict({"train": train_ds, "validation": eval_ds})


def train_understanding_model(
    base_model: str = None,
    output_dir: str = "./qwen_understanding_model",
    include_real_data: bool = True,
    real_limit: int = 100,
    max_seq_length: int = 2048,
):
    """LoRA SFT eğitimi çalıştır, adapter ve merge edilmiş modeli kaydet."""
    base_model = base_model or os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-3B-Instruct")

    # Tokenizer & model
    hf_token = os.environ.get("HF_TOKEN")
    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True, token=hf_token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=None,
        low_cpu_mem_usage=True,
        token=hf_token,
    )

    # Veri seti
    ds = build_training_dataset(include_real_data=include_real_data, real_limit=real_limit)

    # Argümanlar ve LoRA
    training_args = create_understanding_focused_training_args(output_dir=output_dir)
    lora_config = create_understanding_lora_config()

    # SFT Trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        peft_config=lora_config,
        train_dataset=ds["train"],
        eval_dataset=ds["validation"],
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        packing=False,
    )

    trainer.train()

    # En iyi adapter'ı kaydet
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Merge & kaydet
    try:
        merged_dir = os.path.join(output_dir, "merged")
        os.makedirs(merged_dir, exist_ok=True)
        merged_model = trainer.model.merge_and_unload()
        merged_model.save_pretrained(merged_dir)
        tokenizer.save_pretrained(merged_dir)
        print(f"✅ Merge edilmiş model kaydedildi: {merged_dir}")
    except Exception as merge_err:
        print(f"⚠️ Merge sırasında hata: {merge_err}")

    return output_dir


def main():
    """Basit CLI: Eğitim çalıştır ve test et."""
    output_dir = os.environ.get("OUT_DIR", "./qwen_understanding_model")
    base_model = os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-3B-Instruct")
    include_real = os.environ.get("INCLUDE_REAL", "1") != "0"
    real_limit = int(os.environ.get("REAL_LIMIT", "100"))
    max_seq_len = int(os.environ.get("MAX_SEQ_LEN", "2048"))

    print("🚀 Eğitim başlıyor...")
    final_dir = train_understanding_model(
        base_model=base_model,
        output_dir=output_dir,
        include_real_data=include_real,
        real_limit=real_limit,
        max_seq_length=max_seq_len,
    )

    # Öncelikle merge edilmiş varsa onu test et, yoksa adapter klasörünü test et
    merged_path = os.path.join(final_dir, "merged")
    eval_path = merged_path if os.path.isdir(merged_path) else final_dir
    print("🧪 Değerlendirme çalışıyor...")
    _ = run_understanding_evaluation(eval_path)


if __name__ == "__main__":
    main()