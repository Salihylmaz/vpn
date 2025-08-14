import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from elasticsearch_client_v8 import ElasticsearchClient
from datetime import datetime, timedelta
import json
import re

class QuerySystem:
    """
    DialoGPT-medium modelini kullanarak Elasticsearch'ten veri sorgulayan sistem.
    """
    
    def __init__(self, es_host='localhost', es_port=9200, es_username=None, es_password=None, use_ssl=False):
        print("🤖 DialoGPT Query System başlatılıyor...")
        
        # Elasticsearch bağlantısı
        self.es_client = ElasticsearchClient(
            host=es_host,
            port=es_port,
            username=es_username,
            password=es_password,
            use_ssl=use_ssl
        )
        
        # Model ve tokenizer'ı yükle
        print("📥 DialoGPT-medium modeli yükleniyor...")
        try:
            self.tokenizer = AutoTokenizer.from_pretrained("microsoft/DialoGPT-medium")
            self.model = AutoModelForCausalLM.from_pretrained("microsoft/DialoGPT-medium")
            
            # Pad token ekle (DialoGPT için gerekli)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print("✅ Model başarıyla yüklendi!")
            
        except Exception as e:
            print(f"❌ Model yüklenirken hata: {e}")
            raise
        
        # Cevap şablonları
        self.response_templates = {
            "vpn_status": "VPN durumu: {status}. {message}",
            "speed_info": "Hız bilgisi - İndirme: {download} Mbps, Yükleme: {upload} Mbps, Ping: {ping} ms",
            "system_info": "Sistem durumu - CPU: {cpu}%, RAM: {memory}%, Disk: {disk}%",
            "location_info": "Konum bilgisi: {city}, {country} ({ip})",
            "time_based": "{time} tarihinde {info}",
            "not_found": "Belirtilen zamanda/kriterde veri bulunamadı.",
            "error": "Sorgu işlenirken hata oluştu: {error}"
        }
    
    def parse_time_query(self, query):
        """
        Doğal dil sorgudan zaman bilgisini çıkarır.
        
        Args:
            query (str): Kullanıcı sorgusu
            
        Returns:
            dict: Zaman aralığı bilgisi
        """
        query = query.lower()
        now = datetime.now()
        
        # Zaman kalıpları
        time_patterns = {
            r'son (\d+) (dakika|saat|gün)': lambda m: {
                'minutes': int(m.group(1)) if m.group(2) == 'dakika' else 0,
                'hours': int(m.group(1)) if m.group(2) == 'saat' else 0,
                'days': int(m.group(1)) if m.group(2) == 'gün' else 0
            },
            r'(\d{1,2}):(\d{2})': lambda m: {
                'specific_time': f"{m.group(1).zfill(2)}:{m.group(2)}"
            },
            r'bugün': lambda m: {'days': 0, 'specific_day': 'today'},
            r'dün': lambda m: {'days': 1, 'specific_day': 'yesterday'},
            r'bu sabah': lambda m: {'hours': 12, 'specific_period': 'morning'},
            r'bu akşam': lambda m: {'hours': 6, 'specific_period': 'evening'}
        }
        
        for pattern, handler in time_patterns.items():
            match = re.search(pattern, query)
            if match:
                time_info = handler(match)
                
                # Başlangıç ve bitiş zamanını hesapla
                if 'specific_time' in time_info:
                    # Belirli saat
                    time_parts = time_info['specific_time'].split(':')
                    target_time = now.replace(hour=int(time_parts[0]), minute=int(time_parts[1]), second=0, microsecond=0)
                    start_time = target_time - timedelta(minutes=30)  # ±30 dakika aralık
                    end_time = target_time + timedelta(minutes=30)
                else:
                    # Süre bazlı
                    delta = timedelta(
                        minutes=time_info.get('minutes', 0),
                        hours=time_info.get('hours', 0),
                        days=time_info.get('days', 0)
                    )
                    start_time = now - delta
                    end_time = now
                
                return {
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'found_pattern': pattern
                }
        
        # Varsayılan: son 24 saat
        return {
            'start_time': (now - timedelta(days=1)).isoformat(),
            'end_time': now.isoformat(),
            'found_pattern': 'default_24h'
        }
    
    def parse_query_intent(self, query):
        """
        Sorgunun amacını belirler.
        
        Args:
            query (str): Kullanıcı sorgusu
            
        Returns:
            dict: Sorgu amacı ve parametreler
        """
        query = query.lower()
        
        # Amaç kalıpları
        intent_patterns = {
            'vpn_status': [
                r'vpn.*bağlı', r'vpn.*kullan', r'vpn.*aktif', r'vpn.*durum',
                r'proxy.*kullan', r'bağlantı.*güvenli'
            ],
            'speed_info': [
                r'hız.*test', r'internet.*hız', r'download.*speed', r'upload.*speed',
                r'ping', r'bant.*genişlik', r'mbps'
            ],
            'system_info': [
                r'sistem.*durum', r'cpu.*kullan', r'ram.*kullan', r'bellek.*kullan',
                r'disk.*kullan', r'performans'
            ],
            'location_info': [
                r'ip.*adres', r'konum', r'nerde', r'hangi.*şehir', r'hangi.*ülke'
            ],
            'general_status': [
                r'durum.*nedir', r'ne.*olmuş', r'bilgi.*ver', r'özet'
            ]
        }
        
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return {
                        'intent': intent,
                        'confidence': 0.8,
                        'matched_pattern': pattern
                    }
        
        return {
            'intent': 'general_status',
            'confidence': 0.5,
            'matched_pattern': 'default'
        }
    
    def build_elasticsearch_query(self, intent, time_range):
        """
        Elasticsearch sorgusu oluşturur.
        
        Args:
            intent (dict): Sorgu amacı
            time_range (dict): Zaman aralığı
            
        Returns:
            dict: Elasticsearch sorgu objesi
        """
        base_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "collection_timestamp": {
                                    "gte": time_range['start_time'],
                                    "lte": time_range['end_time']
                                }
                            }
                        }
                    ]
                }
            },
            "sort": [{"collection_timestamp": {"order": "desc"}}],
            "size": 10
        }
        
        # Amaca göre ek filtreler
        if intent['intent'] == 'vpn_status':
            base_query["query"]["bool"]["must"].append({
                "exists": {"field": "web_data.vpn_detection"}
            })
        
        return base_query
    
    def search_data(self, intent, time_range):
        """
        Elasticsearch'te veri arar.
        
        Args:
            intent (dict): Sorgu amacı
            time_range (dict): Zaman aralığı
            
        Returns:
            list: Bulunan veriler
        """
        try:
            query = self.build_elasticsearch_query(intent, time_range)
            results = self.es_client.search("combined-monitoring", query.get("query"), query.get("size", 10))
            
            return [hit['_source'] for hit in results]
            
        except Exception as e:
            print(f"❌ Elasticsearch sorgu hatası: {e}")
            return []
    
    def format_response(self, intent, data, time_range):
        """
        Veriyi doğal dil yanıtına dönüştürür.
        
        Args:
            intent (dict): Sorgu amacı
            data (list): Elasticsearch'ten gelen veriler
            time_range (dict): Zaman aralığı
            
        Returns:
            str: Formatlanmış yanıt
        """
        if not data:
            return self.response_templates["not_found"]
        
        latest_data = data[0]  # En son veri
        
        try:
            if intent['intent'] == 'vpn_status':
                vpn_info = latest_data.get('web_data', {}).get('vpn_detection', {})
                if vpn_info:
                    return self.response_templates["vpn_status"].format(
                        status=vpn_info.get('status', 'bilinmiyor'),
                        message=vpn_info.get('message', 'Detay yok.')
                    )
            
            elif intent['intent'] == 'speed_info':
                speed_info = latest_data.get('web_data', {}).get('speed_test', {})
                if speed_info:
                    return self.response_templates["speed_info"].format(
                        download=speed_info.get('download_speed', 'N/A'),
                        upload=speed_info.get('upload_speed', 'N/A'),
                        ping=speed_info.get('ping', 'N/A')
                    )
            
            elif intent['intent'] == 'system_info':
                system_data = latest_data.get('system_data', {})
                cpu = system_data.get('cpu', {}).get('cpu_percent', 'N/A')
                memory = system_data.get('memory', {}).get('virtual_memory', {}).get('percent', 'N/A')
                disk = system_data.get('disk', {}).get('disk_usage', {}).get('main', {}).get('percent', 'N/A')
                
                return self.response_templates["system_info"].format(
                    cpu=cpu, memory=memory, disk=disk
                )
            
            elif intent['intent'] == 'location_info':
                ip_info = latest_data.get('web_data', {}).get('ip_info', {})
                if ip_info:
                    return self.response_templates["location_info"].format(
                        city=ip_info.get('city', 'N/A'),
                        country=ip_info.get('country', 'N/A'),
                        ip=latest_data.get('web_data', {}).get('ip_address', 'N/A')
                    )
            
            # Genel durum
            response_parts = []
            
            # VPN durumu
            vpn_info = latest_data.get('web_data', {}).get('vpn_detection', {})
            if vpn_info:
                response_parts.append(f"VPN: {vpn_info.get('status', 'bilinmiyor')}")
            
            # Sistem durumu
            system_data = latest_data.get('system_data', {})
            if system_data:
                cpu = system_data.get('cpu', {}).get('cpu_percent', 'N/A')
                memory = system_data.get('memory', {}).get('virtual_memory', {}).get('percent', 'N/A')
                response_parts.append(f"CPU: {cpu}%, RAM: {memory}%")
            
            # Konum
            ip_info = latest_data.get('web_data', {}).get('ip_info', {})
            if ip_info:
                response_parts.append(f"Konum: {ip_info.get('city', 'N/A')}, {ip_info.get('country', 'N/A')}")
            
            return " | ".join(response_parts) if response_parts else "Veri bulunamadı."
            
        except Exception as e:
            return self.response_templates["error"].format(error=str(e))
    
    def generate_response_with_dialogpt(self, context, max_length=100):
        """
        DialoGPT ile yanıt üretir.
        
        Args:
            context (str): Kontext bilgisi
            max_length (int): Maksimum yanıt uzunluğu
            
        Returns:
            str: Üretilen yanıt
        """
        try:
            # Tokenize et
            inputs = self.tokenizer.encode(context + self.tokenizer.eos_token, return_tensors='pt')
            
            # Yanıt üret
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + max_length,
                    num_beams=3,
                    do_sample=True,
                    temperature=0.7,
                    pad_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=2
                )
            
            # Decode et
            response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            return response.strip()
            
        except Exception as e:
            print(f"❌ DialoGPT yanıt üretme hatası: {e}")
            return "Yanıt üretemedim, teknik bir sorun oluştu."
    
    def process_query(self, user_query):
        """
        Kullanıcı sorgusunu işler ve yanıt döner.
        
        Args:
            user_query (str): Kullanıcı sorgusu
            
        Returns:
            dict: İşlenmiş yanıt ve meta bilgiler
        """
        print(f"\n🔍 Sorgu işleniyor: '{user_query}'")
        
        # 1. Zaman bilgisini çıkar
        time_range = self.parse_time_query(user_query)
        print(f"⏰ Zaman aralığı: {time_range['start_time']} - {time_range['end_time']}")
        
        # 2. Sorgu amacını belirle
        intent = self.parse_query_intent(user_query)
        print(f"🎯 Tespit edilen amaç: {intent['intent']} (güven: {intent['confidence']})")
        
        # 3. Elasticsearch'te veri ara
        print("📊 Veriler sorgulanıyor...")
        data = self.search_data(intent, time_range)
        print(f"📋 {len(data)} kayıt bulundu")
        
        # 4. Yanıtı formatla
        structured_response = self.format_response(intent, data, time_range)
        
        # 5. DialoGPT ile doğal yanıt üret
        context = f"Kullanıcı sorusu: {user_query}\nBulunan bilgi: {structured_response}\nYanıt:"
        natural_response = self.generate_response_with_dialogpt(context)
        
        result = {
            "query": user_query,
            "intent": intent,
            "time_range": time_range,
            "data_found": len(data),
            "structured_response": structured_response,
            "natural_response": natural_response,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✅ Sorgu işlendi!")
        return result
    
    def interactive_mode(self):
        """
        Etkileşimli soru-cevap modu.
        """
        print("\n" + "="*60)
        print("🤖 DialoGPT Query System - Etkileşimli Mod")
        print("="*60)
        print("Sistem ve ağ verileriniz hakkında soru sorabilirsiniz!")
        print("Örnek sorular:")
        print("- 'Son 2 saatte VPN bağlı mıydı?'")
        print("- '14:30'da internet hızı nasıldı?'")
        print("- 'Bugün sistem performansı nasıl?'")
        print("- 'Dün akşam hangi ülkede görünüyordum?'")
        print("Çıkmak için 'quit' yazın.")
        print("="*60)
        
        while True:
            try:
                user_input = input("\n💬 Sorunuz: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'çık', 'q']:
                    print("👋 Görüşürüz!")
                    break
                
                if not user_input:
                    print("⚠️ Lütfen bir soru sorun.")
                    continue
                
                # Sorguyu işle
                result = self.process_query(user_input)
                
                # Sonucu göster
                print(f"\n🤖 Yanıt: {result['natural_response']}")
                print(f"📊 Detay: {result['structured_response']}")
                print(f"📈 {result['data_found']} kayıt incelendi")
                
            except KeyboardInterrupt:
                print("\n👋 Görüşürüz!")
                break
            except Exception as e:
                print(f"❌ Hata oluştu: {e}")

def main():
    """
    Ana fonksiyon - Query System'i test eder.
    """
    try:
        # Query System'i başlat
        query_system = QuerySystem()
        
        print("\n🎯 Sistem hazır! Test sorguları:")
        
        # Test sorguları
        test_queries = [
            "Son 1 saatte VPN bağlı mıydı?",
            "Bugün internet hızı nasıl?",
            "Sistem durumu nedir?",
            "Hangi ülkede görünüyorum?"
        ]
        
        for query in test_queries:
            print(f"\n{'='*50}")
            result = query_system.process_query(query)
            print(f"Soru: {query}")
            print(f"Yanıt: {result['natural_response']}")
            print(f"Detay: {result['structured_response']}")
        
        # Etkileşimli mod
        query_system.interactive_mode()
        
    except Exception as e:
        print(f"❌ Sistem başlatılamadı: {e}")

if __name__ == "__main__":
    main()