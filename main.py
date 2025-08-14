# system_monitor.py

import time
import socket
from datetime import datetime, timedelta
import psutil
import speedtest
# ElasticsearchClient sınıfını ayrı dosyadan import ediyoruz
from elasticsearch_client_v8 import ElasticsearchClient

# Web bilgilerini toplayan sınıf
class WebInfo:
    def __init__(self):
        self.download_speed = None
        self.upload_speed = None
        self.ping = None
        self.ip_info = None
        self.vpn_status = None
    
    def get_speed_test_info(self):
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            self.download_speed = st.download() / 1_000_000
            self.upload_speed = st.upload() / 1_000_000
            self.ping = st.results.ping
            print(f"Hız testi tamamlandı: İndirme: {self.download_speed:.2f} Mbps, Yükleme: {self.upload_speed:.2f} Mbps, Ping: {self.ping:.2f} ms")
            return {
                "download_speed": self.download_speed,
                "upload_speed": self.upload_speed,
                "ping": self.ping
            }
        except Exception as e:
            print(f"Hız testi hatası: {e}")
            return None
    
    def get_ip_info(self):
        # ipinfo.io gibi bir servisten IP bilgisi alınabilir.
        # Bu kısım için `requests` kütüphanesi gerekli olabilir.
        # 'pip install requests' ile kurmanız gerekir.
        # Ancak basit bir örnek için bu kısım mocklanabilir veya dışarıda bırakılabilir.
        return None
    
    def VPN_info(self):
        # VPN tespiti için ek kodlar gereklidir.
        # Örneğin, bilinen bir IP'den farklı bir IP'ye sahip olup olmadığını kontrol etmek.
        return "Not Implemented" # Örnek olarak bu şekilde bırakıldı

# Ana monitör sınıfı
class SystemMonitor:
    def __init__(self, es_host='localhost', es_port=9200, es_username=None, es_password=None):
        self.es_client = ElasticsearchClient(
            host=es_host,
            port=es_port,
            username=es_username,
            password=es_password
        )
        
        self.create_indices()
        self.web_info = WebInfo()
        self.hostname = socket.gethostname()
    
    def create_indices(self):
        """
        Gerekli index'leri oluşturur
        """
        web_mapping = {
            "properties": {
                "hostname": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "download_speed": {"type": "float"},
                "upload_speed": {"type": "float"},
                "ping": {"type": "float"},
                "ip_info": {
                    "properties": {
                        "ip": {"type": "ip"},
                        "hostname": {"type": "text"},
                        "city": {"type": "keyword"},
                        "region": {"type": "keyword"},
                        "country": {"type": "keyword"},
                        "loc": {"type": "keyword"},
                        "org": {"type": "text"},
                        "postal": {"type": "keyword"},
                        "timezone": {"type": "keyword"}
                    }
                },
                "vpn_status": {"type": "text"}
            }
        }
        
        system_mapping = {
            "properties": {
                "hostname": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "cpu_percent": {"type": "float"},
                "memory_percent": {"type": "float"},
                "disk_usage": {"type": "float"},
                "process_count": {"type": "integer"}
            }
        }
        
        self.es_client.create_index("web-info", web_mapping)
        self.es_client.create_index("system-info", system_mapping)
    
    def collect_web_info(self):
        """
        Web bilgilerini toplar ve Elasticsearch'e gönderir
        """
        print("Web bilgileri toplanıyor...")
        
        self.web_info.get_speed_test_info()
        ip_info = self.web_info.get_ip_info()
        vpn_status = self.web_info.VPN_info()
        
        web_data = {
            "hostname": self.hostname,
            "download_speed": self.web_info.download_speed,
            "upload_speed": self.web_info.upload_speed,
            "ping": self.web_info.ping,
            "ip_info": ip_info,
            "vpn_status": vpn_status
        }
        
        self.es_client.index_document("web-info", web_data)
        print("Web bilgileri Elasticsearch'e gönderildi.")
        
        return web_data
    
    def collect_system_info(self):
        """
        Sistem bilgilerini toplar (psutil kütüphanesi kullanır)
        """
        print("Sistem bilgileri toplanıyor...")
        
        system_data = {
            "hostname": self.hostname,
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "process_count": len(psutil.pids())
        }
        
        self.es_client.index_document("system-info", system_data)
        print("Sistem bilgileri Elasticsearch'e gönderildi.")
        
        return system_data
    
    def run_single_collection(self):
        """
        Tek seferlik veri toplama
        """
        print(f"Veri toplama başladı - {datetime.now()}")
        
        try:
            web_data = self.collect_web_info()
            system_data = self.collect_system_info()
            
            print("Tüm veriler başarıyla toplandı ve Elasticsearch'e gönderildi!")
            return web_data, system_data
            
        except Exception as e:
            print(f"Veri toplama hatası: {e}")
            return None, None
    
    def run_continuous_monitoring(self, interval=300):
        """
        Sürekli monitöring
        """
        print(f"Sürekli monitöring başladı. Aralık: {interval} saniye")
        
        while True:
            try:
                self.run_single_collection()
                print(f"Sonraki toplama: {interval} saniye sonra...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nMonitöring durduruldu.")
                break
            except Exception as e:
                print(f"Monitöring hatası: {e}")
                time.sleep(60)
    
    def search_recent_data(self, index_name="web-info", hours=24):
        """
        Son X saatteki verileri arar
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        query = {
            "range": {
                "timestamp": {
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                }
            }
        }
        
        results = self.es_client.search(index_name, query, size=100)
        print(f"Son {hours} saatte {len(results)} kayıt bulundu.")
        
        return results

def main():
    # Elasticsearch ayarları
    ES_HOST = 'localhost'
    ES_PORT = 9200
    ES_USERNAME = None
    ES_PASSWORD = None
    
    try:
        monitor = SystemMonitor(
            es_host=ES_HOST,
            es_port=ES_PORT,
            es_username=ES_USERNAME,
            es_password=ES_PASSWORD
        )
        
        while True:
            print("\n=== Sistem Monitörü ===")
            print("1. Tek seferlik veri toplama")
            print("2. Sürekli monitöring başlat")
            print("3. Son 24 saatteki web verilerini göster")
            print("4. Son 24 saatteki sistem verilerini göster")
            print("5. Çıkış")
            
            choice = input("\nSeçiminiz (1-5): ").strip()
            
            if choice == '1':
                monitor.run_single_collection()
            
            elif choice == '2':
                interval = input("Veri toplama aralığı (saniye, varsayılan 300): ").strip()
                interval = int(interval) if interval.isdigit() else 300
                monitor.run_continuous_monitoring(interval)
            
            elif choice == '3':
                results = monitor.search_recent_data("web-info", 24)
                for i, result in enumerate(results[:5]):
                    print(f"\n{i+1}. {result['_source']}")
            
            elif choice == '4':
                results = monitor.search_recent_data("system-info", 24)
                for i, result in enumerate(results[:5]):
                    print(f"\n{i+1}. {result['_source']}")
            
            elif choice == '5':
                print("Çıkılıyor...")
                break
            
            else:
                print("Geçersiz seçim!")
    
    except Exception as e:
        print(f"Ana uygulama hatası: {e}")

if __name__ == "__main__":
    main()
