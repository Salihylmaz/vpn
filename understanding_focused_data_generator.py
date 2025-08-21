# understanding_focused_data_generator.py
import json
from backend.elasticsearch_client_v8 import ElasticsearchClient

class UnderstandingFocusedDataGenerator:
    """Anlama odaklı eğitim verisi üreticisi"""
    
    def __init__(self, es_client):
        self.es_client = es_client
        
    def generate_understanding_pairs(self):
        """Anlama odaklı Q&A çiftleri"""
        
        pairs = []
        
        # 1. KAVRAM TANIMLAMALARI
        pairs.extend(self._generate_concept_definitions())
        
        # 2. VERİ YAPISI ÖĞRETİMİ  
        pairs.extend(self._generate_data_structure_training())
        
        # 3. SORGU ANLAMA EĞİTİMİ
        pairs.extend(self._generate_query_understanding())
        
        # 4. BAĞLAM ANLAMA
        pairs.extend(self._generate_context_understanding())
        
        # 5. DOĞAL DİL → TEKNIK TERİM MAPPING
        pairs.extend(self._generate_language_mapping())
        
        return pairs
    
    def _generate_concept_definitions(self):
        """Sistem monitoring kavramlarını öğret"""
        pairs = []
        
        # CPU kavramları
        cpu_concepts = [
            {
                "instruction": "CPU kullanımı nedir?",
                "input": "",
                "output": "CPU kullanımı, işlemcinin ne kadar meşgul olduğunu gösteren yüzdelik bir değerdir. 0% = boş, 100% = tam yüklü. system_data.cpu.cpu_percent alanında bulunur."
            },
            {
                "instruction": "CPU %85 yüksek mi?",
                "input": "",
                "output": "Evet, CPU %85 yüksek sayılır. Genelde %80 üzeri yüksek, %50-80 orta, %50 altı düşük kabul edilir."
            },
            {
                "instruction": "sistem yavaş ne demek?",
                "input": "",
                "output": "Sistem yavaş genellikle CPU kullanımı %80+, RAM kullanımı %90+ veya disk kullanımı %95+ olduğunda ortaya çıkar."
            }
        ]
        
        # RAM kavramları  
        memory_concepts = [
            {
                "instruction": "RAM nedir?",
                "input": "",
                "output": "RAM (Bellek), bilgisayarın geçici veri depolama alanıdır. system_data.memory.virtual_memory.percent alanında yüzdelik kullanım oranı bulunur."
            },
            {
                "instruction": "Bellek dolmuş ne demek?",
                "input": "",
                "output": "Bellek dolmuş, RAM kullanımının %90+ olması demektir. Bu durumda sistem swap memory kullanmaya başlar ve yavaşlar."
            }
        ]
        
        # Ağ kavramları
        network_concepts = [
            {
                "instruction": "VPN nedir?",
                "input": "",
                "output": "VPN, internet bağlantınızı şifreleyip IP adresinizi gizler. web_data.vpn_detection.status alanında durumu kontrol edilir."
            },
            {
                "instruction": "Download speed nedir?",
                "input": "",
                "output": "İndirme hızı, internetinizin saniyede kaç megabit veri indirebileceğini gösterir. web_data.speed_test.download_speed alanında Mbps cinsinden bulunur."
            },
            {
                "instruction": "Ping yüksek ne demek?",
                "input": "",
                "output": "Ping, internet gecikme süresini milisaniye cinsinden gösterir. 50ms altı iyi, 100ms+ yüksek sayılır. web_data.speed_test.ping alanında bulunur."
            }
        ]
        
        pairs.extend(cpu_concepts)
        pairs.extend(memory_concepts)
        pairs.extend(network_concepts)
        
        return pairs
    
    def _generate_data_structure_training(self):
        """JSON veri yapısını öğret"""
        pairs = []
        
        # Örnek sistem verisi
        sample_system_data = {
            "collection_timestamp": "2024-01-15T14:30:00",
            "system_data": {
                "cpu": {"cpu_percent": 75.2},
                "memory": {"virtual_memory": {"percent": 68.5, "used": 8589934592, "total": 12589934592}},
                "disk": {"disk_usage": {"main": {"percent": 45.3}}}
            },
            "web_data": {
                "ip_address": "185.123.45.67", 
                "vpn_detection": {"status": "no_vpn", "message": "Normal ISP connection"},
                "speed_test": {"download_speed": 24.5, "upload_speed": 5.2, "ping": 18}
            }
        }
        
        structure_pairs = [
            {
                "instruction": "Bu veride CPU kullanımı nerede?",
                "input": json.dumps(sample_system_data, ensure_ascii=False),
                "output": "CPU kullanımı system_data.cpu.cpu_percent alanında bulunur. Bu örnekte %75.2."
            },
            {
                "instruction": "RAM bilgisi nasıl alınır?",
                "input": json.dumps(sample_system_data, ensure_ascii=False),
                "output": "RAM bilgisi system_data.memory.virtual_memory içinde. percent: kullanım yüzdesi, used: kullanılan bytes, total: toplam bytes."
            },
            {
                "instruction": "VPN durumu nerede görünür?",
                "input": json.dumps(sample_system_data, ensure_ascii=False),
                "output": "VPN durumu web_data.vpn_detection.status alanında. Bu örnekte 'no_vpn' yani VPN kullanılmıyor."
            },
            {
                "instruction": "İnternet hızı hangi alanda?",
                "input": json.dumps(sample_system_data, ensure_ascii=False),
                "output": "İnternet hızı web_data.speed_test içinde. download_speed: indirme, upload_speed: yükleme (Mbps), ping: gecikme (ms)."
            },
            {
                "instruction": "Bu sistem durumu nasıl?",
                "input": json.dumps(sample_system_data, ensure_ascii=False),
                "output": "CPU %75 (orta-yüksek), RAM %68 (normal), VPN yok, İnternet 24.5 Mbps (iyi). Genel olarak sistem normal çalışıyor."
            }
        ]
        
        pairs.extend(structure_pairs)
        return pairs
    
    def _generate_query_understanding(self):
        """Soru anlama eğitimi"""
        pairs = []
        
        # Zaman ifadeleri
        time_queries = [
            {
                "instruction": "'Son 2 saatte' ne anlama gelir?",
                "input": "",
                "output": "Şu andan 2 saat geriye giden zaman aralığını ifade eder. Elasticsearch'te range query ile collection_timestamp alanında arama yapılır."
            },
            {
                "instruction": "'Bugün' nasıl sorgulanır?",
                "input": "",
                "output": "Bugün = günün 00:00'ından şu ana kadar. timestamp alanında gün başlangıcından now'a kadar range query."
            },
            {
                "instruction": "'Dün akşam' ne demek?",
                "input": "",
                "output": "Önceki günün 18:00-23:59 saatleri arası. Dünün tarihi + 18:00 ile 23:59 arası range query."
            }
        ]
        
        # Karşılaştırma ifadeleri
        comparison_queries = [
            {
                "instruction": "'CPU yüksek mi?' sorusu nasıl anlaşılır?",
                "input": "",
                "output": "CPU değerini al, %80+ ise 'yüksek', %50-80 arası 'orta', %50- 'düşük' olarak değerlendir."
            },
            {
                "instruction": "'Normalden farklı mı?' ne demek?",
                "input": "",
                "output": "Geçmiş verilerle karşılaştırma yapmak gerekir. Ortalama değerlerin %20+ üzeri/altı farklı sayılır."
            },
            {
                "instruction": "'Sistem yavaş mı?' nasıl kontrol edilir?",
                "input": "",
                "output": "CPU >%80, RAM >%90 veya disk >%95 ise sistem yavaş olabilir. Birden fazla metrik yüksekse kesin yavaştır."
            }
        ]
        
        pairs.extend(time_queries)
        pairs.extend(comparison_queries)
        return pairs
    
    def _generate_context_understanding(self):
        """Bağlam anlama eğitimi"""
        pairs = []
        
        context_pairs = [
            {
                "instruction": "Kullanıcı 'bilgisayarım yavaş' diyorsa neye bakmalısın?",
                "input": "",
                "output": "1. CPU kullanımını kontrol et (%80+), 2. RAM durumunu kontrol et (%90+), 3. Disk kullanımını kontrol et (%95+), 4. Çalışan işlem sayısını kontrol et."
            },
            {
                "instruction": "Kullanıcı 'internet kesildi mi?' diyorsa ne yapmalısın?",
                "input": "",
                "output": "1. Son speed_test verisi var mı kontrol et, 2. IP adresi değişmiş mi kontrol et, 3. VPN durumu değişmiş mi kontrol et."
            },
            {
                "instruction": "Kullanıcı 'hangi ülkedeyim?' diyorsa nereye bakmalısın?",
                "input": "",
                "output": "web_data.ip_info.country alanına bak. Ayrıca city bilgisi de web_data.ip_info.city'de bulunur."
            },
            {
                "instruction": "Kullanıcı geçmiş zaman kullanıyorsa ne anlarsın?",
                "input": "",
                "output": "Elasticsearch'te geçmiş verileri sorgulamak gerektiğini anlarım. Zaman aralığı belirleyip range query yaparım."
            }
        ]
        
        pairs.extend(context_pairs)
        return pairs
    
    def _generate_language_mapping(self):
        """Doğal dil → Teknik terim mapping"""
        pairs = []
        
        language_mappings = [
            {
                "instruction": "'RAM'e başka ne denir?",
                "input": "",
                "output": "RAM = Bellek = Hafıza = Memory. Hepsi aynı şeyi ifade eder, system_data.memory alanını kontrol et."
            },
            {
                "instruction": "'İşlemci'ye başka ne denir?",
                "input": "",
                "output": "İşlemci = CPU = Processor. Hepsi aynı, system_data.cpu alanını kontrol et."
            },
            {
                "instruction": "'İnternet hızı' için hangi terimler kullanılır?",
                "input": "",
                "output": "İnternet hızı = Bağlantı hızı = Download speed = Hız testi. web_data.speed_test alanındaki download_speed değerine bak."
            },
            {
                "instruction": "'VPN açık mı?' sorusundaki eş anlamlılar neler?",
                "input": "",
                "output": "VPN açık = VPN bağlı = VPN aktif = VPN kullanıyor. web_data.vpn_detection.status 'vpn_detected' ise açık."
            },
            {
                "instruction": "Kullanıcı 'ping' yerine ne diyebilir?",
                "input": "",
                "output": "Ping = Gecikme = Latency = Gecikmesi. web_data.speed_test.ping değerini kontrol et, ms cinsinden."
            }
        ]
        
        pairs.extend(language_mappings)
        return pairs

# Gerçek veriden anlama örnekleri üret
def generate_real_data_understanding(es_client, limit=100):
    """Gerçek Elasticsearch verisinden anlama örnekleri"""
    
    query = {"query": {"match_all": {}}, "size": limit}
    results = es_client.search("combined-monitoring", query["query"], size=limit)
    
    understanding_pairs = []
    
    for hit in results[:20]:  # İlk 20 gerçek veri
        data = hit['_source']
        
        # Her gerçek veri için anlama soruları
        pairs = create_understanding_questions_from_real_data(data)
        understanding_pairs.extend(pairs)
    
    return understanding_pairs

def create_understanding_questions_from_real_data(real_data):
    """Gerçek veriden anlama soruları oluştur"""
    pairs = []
    
    # CPU anlama
    if real_data.get('system_data', {}).get('cpu'):
        cpu_val = real_data['system_data']['cpu'].get('cpu_percent', 0)
        
        pairs.append({
            "instruction": "Bu veride CPU bilgisi nasıl yorumlanır?",
            "input": json.dumps(real_data['system_data']['cpu'], ensure_ascii=False),
            "output": f"CPU kullanımı %{cpu_val}. " + 
                     ("Yüksek seviye, sistem yoğun." if cpu_val > 80 else
                      "Orta seviye, normal kullanım." if cpu_val > 50 else 
                      "Düşük seviye, sistem rahat.")
        })
    
    # Memory anlama
    if real_data.get('system_data', {}).get('memory', {}).get('virtual_memory'):
        mem = real_data['system_data']['memory']['virtual_memory']
        mem_percent = mem.get('percent', 0)
        mem_used_gb = round(mem.get('used', 0) / (1024**3), 1)
        mem_total_gb = round(mem.get('total', 0) / (1024**3), 1)
        
        pairs.append({
            "instruction": "Bu bellek verisi ne anlama geliyor?",
            "input": json.dumps(mem, ensure_ascii=False),
            "output": f"RAM %{mem_percent} dolu ({mem_used_gb}/{mem_total_gb} GB). " +
                     ("Yüksek kullanım, yavaşlayabilir." if mem_percent > 85 else
                      "Normal kullanım seviyesi." if mem_percent > 60 else
                      "Düşük kullanım, bol bellek var.")
        })
    
    # VPN anlama
    if real_data.get('web_data', {}).get('vpn_detection'):
        vpn = real_data['web_data']['vpn_detection']
        status = vpn.get('status', 'unknown')
        
        pairs.append({
            "instruction": "Bu VPN verisi ne gösteriyor?",
            "input": json.dumps(vpn, ensure_ascii=False),
            "output": f"VPN durumu: {status}. " +
                     ("VPN aktif, IP gizli." if status == "vpn_detected" else
                      "VPN yok, gerçek IP görünür." if status == "no_vpn" else
                      "VPN durumu belirsiz.")
        })
    
    return pairs