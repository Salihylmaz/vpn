import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
# understanding_tester.py
class UnderstandingTester:
    """Modelin anlayıp anlamadığını test et"""
    
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
    
    def test_concept_understanding(self):
        """Kavram anlama testi"""
        
        concept_tests = [
            {
                "question": "CPU %90 nasıl yorumlanır?",
                "expected_keywords": ["yüksek", "yoğun", "yavaş"],
                "unexpected_keywords": ["düşük", "normal", "rahat"]
            },
            {
                "question": "RAM %30 ne anlama gelir?",
                "expected_keywords": ["düşük", "normal", "bol"],
                "unexpected_keywords": ["yüksek", "dolu", "yavaş"]
            },
            {
                "question": "VPN detected ne demek?",
                "expected_keywords": ["vpn", "aktif", "gizli"],
                "unexpected_keywords": ["normal", "açık değil"]
            }
        ]
        
        results = []
        for test in concept_tests:
            response = self.generate_response(test["question"])
            
            # Beklenen kelimeleri içeriyor mu?
            expected_found = any(keyword in response.lower() for keyword in test["expected_keywords"])
            unexpected_found = any(keyword in response.lower() for keyword in test["unexpected_keywords"])
            
            results.append({
                "question": test["question"],
                "response": response,
                "expected_found": expected_found,
                "unexpected_found": unexpected_found,
                "score": 1 if expected_found and not unexpected_found else 0
            })
        
        return results
    
    def test_data_structure_understanding(self):
        """Veri yapısı anlama testi"""
        
        sample_data = {
            "system_data": {
                "cpu": {"cpu_percent": 85.3},
                "memory": {"virtual_memory": {"percent": 72.1}}
            },
            "web_data": {
                "vpn_detection": {"status": "no_vpn"}
            }
        }
        
        structure_tests = [
            {
                "question": "Bu veride CPU kullanımı nerede?",
                "data": sample_data,
                "expected_location": "system_data.cpu.cpu_percent"
            },
            {
                "question": "VPN durumu hangi alanda?",
                "data": sample_data,
                "expected_location": "web_data.vpn_detection.status"
            }
        ]
        
        results = []
        for test in structure_tests:
            prompt = f"Soru: {test['question']}\nVeri: {json.dumps(test['data'])}\nYanıt:"
            response = self.generate_response(prompt)
            
            # Doğru lokasyonu belirtti mi?
            location_mentioned = test["expected_location"].replace(".", "") in response.replace(".", "")
            
            results.append({
                "question": test["question"],
                "response": response,
                "correct_location": location_mentioned,
                "expected": test["expected_location"]
            })
        
        return results
    
    def generate_response(self, prompt):
        """Test yanıtı üret"""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.1,  # Test için deterministik
                do_sample=False
            )
        
        response = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:], 
            skip_special_tokens=True
        )
        return response.strip()

def run_understanding_evaluation(model_path):
    """Anlama değerlendirmesi çalıştır"""
    
    # Model yükle
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path)
    
    # Test et
    tester = UnderstandingTester(model, tokenizer)
    
    print("🧠 Kavram anlama testi...")
    concept_results = tester.test_concept_understanding()
    
    print("🏗️ Veri yapısı anlama testi...")
    structure_results = tester.test_data_structure_understanding()
    
    # Sonuçları değerlendir
    concept_score = sum(r["score"] for r in concept_results) / len(concept_results)
    structure_score = sum(r["correct_location"] for r in structure_results) / len(structure_results)
    
    print(f"📊 Kavram anlama skoru: {concept_score:.2f}")
    print(f"📊 Veri yapısı anlama skoru: {structure_score:.2f}")
    print(f"🎯 Genel anlama skoru: {(concept_score + structure_score) / 2:.2f}")
    
    return {
        "concept_score": concept_score,
        "structure_score": structure_score,
        "overall_score": (concept_score + structure_score) / 2
    }