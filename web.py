import psutil, platform, subprocess, requests, speedtest
from datetime import datetime
import time

class WebInfo:
    """
    Web ve ağ bilgilerini toplayan sınıf.
    IP bilgisi, hız testi ve VPN tespiti yapar.
    """
    
    def __init__(self, expected_country="TR"):
        self.download_speed = None
        self.upload_speed = None
        self.ping = None
        self.server_info = None
        self.current_ip = None
        self.ip_info = None
        self.vpn_detection = None
        self.expected_country = expected_country
        self.last_speed_test = None

    def get_speed_test_info(self, max_attempts=3):
        """
        İnternet hız testini yapar.
        
        Args:
            max_attempts (int): Maksimum deneme sayısı
            
        Returns:
            dict: Hız testi sonuçları
        """
        print("⚡ İnternet hız testi yapılıyor...")
        
        for attempt in range(max_attempts):
            try:
                st = speedtest.Speedtest()
                print(f"   Sunucu seçiliyor... (Deneme {attempt + 1}/{max_attempts})")
                st.get_best_server()
                
                server_info = st.get_best_server()
                self.server_info = {
                    "name": server_info.get("name", "N/A"),
                    "country": server_info.get("country", "N/A"),
                    "sponsor": server_info.get("sponsor", "N/A"),
                    "host": server_info.get("host", "N/A"),
                    "distance": round(server_info.get("d", 0), 2)
                }
                
                print("   İndirme hızı ölçülüyor...")
                download_bps = st.download()
                self.download_speed = round(download_bps / 1_000_000, 2)  # Mbps
                
                print("   Yükleme hızı ölçülüyor...")
                upload_bps = st.upload()
                self.upload_speed = round(upload_bps / 1_000_000, 2)   # Mbps
                
                self.ping = round(st.results.ping, 2)
                self.last_speed_test = datetime.now().isoformat()
                
                speed_result = {
                    "download_speed": self.download_speed,
                    "upload_speed": self.upload_speed,
                    "ping": self.ping,
                    "server_info": self.server_info,
                    "test_timestamp": self.last_speed_test,
                    "units": "Mbps"
                }
                
                print(f"✅ Hız testi tamamlandı: ↓{self.download_speed} Mbps ↑{self.upload_speed} Mbps 🏓{self.ping} ms")
                return speed_result
                
            except Exception as e:
                print(f"❌ Hız testi hatası (Deneme {attempt + 1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    print("   2 saniye bekleyip tekrar deneniyor...")
                    time.sleep(2)
                else:
                    print("❌ Hız testi başarısız oldu!")
                    return None
        
        return None
    
    def get_ip_info(self):
        """
        IP bilgisini ve konum verilerini alır.
        
        Returns:
            dict: IP bilgileri
        """
        print("🌐 IP bilgisi alınıyor...")
        
        try:
            # Önce IP adresini al
            print("   IP adresi sorgulanıyor...")
            ip_response = requests.get("https://api.ipify.org", timeout=10)
            if ip_response.status_code == 200:
                self.current_ip = ip_response.text.strip()
                print(f"   IP Adresi: {self.current_ip}")
            else:
                print("❌ IP adresi alınamadı!")
                return None
            
            # IP bilgilerini al
            print("   IP detayları sorgulanıyor...")
            info_response = requests.get(f"https://ipinfo.io/{self.current_ip}/json", timeout=10)
            if info_response.status_code == 200:
                self.ip_info = info_response.json()
                
                # Konum bilgisini geo_point formatına çevir
                if 'loc' in self.ip_info and self.ip_info['loc']:
                    lat, lon = self.ip_info['loc'].split(',')
                    self.ip_info['location'] = {
                        "lat": float(lat),
                        "lon": float(lon)
                    }
                
                print(f"✅ IP bilgisi alındı: {self.ip_info.get('city', 'N/A')}, {self.ip_info.get('country', 'N/A')}")
                return self.ip_info
            else:
                print(f"❌ IP bilgisi alınamadı! HTTP {info_response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"❌ IP bilgisi alma hatası: {e}")
            return None
        except Exception as e:
            print(f"❌ Beklenmeyen hata: {e}")
            return None
    
    def detect_vpn(self):
        """
        VPN kullanımını tespit eder.
        
        Returns:
            dict: VPN tespit sonucu
        """
        print("🔍 VPN tespiti yapılıyor...")
        
        try:
            if not self.ip_info:
                self.vpn_detection = {
                    "status": "unknown",
                    "message": "IP bilgisi alınamadığı için VPN tespiti yapılamadı."
                }
                return self.vpn_detection
            
            country = self.ip_info.get('country', '').upper()
            city = self.ip_info.get('city', 'N/A')
            org = self.ip_info.get('org', '').lower()
            
            # Ülke kontrolü
            if country != self.expected_country:
                self.vpn_detection = {
                    "status": "possible_vpn",
                    "message": f"IP farklı ülkede ({city}, {country}). Beklenen: {self.expected_country}",
                    "reason": "country_mismatch",
                    "detected_country": country,
                    "expected_country": self.expected_country
                }
                print(f"⚠️ VPN olası: IP {country} ülkesinde görünüyor")
                return self.vpn_detection
            
            # Organizasyon kontrolü (VPN/Proxy sağlayıcıları)
            vpn_keywords = ['vpn', 'hosting', 'datacenter', 'data center', 'proxy', 'cloud', 'tor', 'relay', 'tunnel']
            detected_keywords = [keyword for keyword in vpn_keywords if keyword in org]
            
            if detected_keywords:
                self.vpn_detection = {
                    "status": "vpn_detected",
                    "message": f"VPN/Proxy tespit edildi: {org}",
                    "reason": "organization_analysis",
                    "detected_keywords": detected_keywords,
                    "organization": self.ip_info.get('org', 'N/A')
                }
                print(f"🚫 VPN tespit edildi: {org}")
                return self.vpn_detection
            
            # Normal durum
            self.vpn_detection = {
                "status": "no_vpn",
                "message": f"VPN tespit edilmedi. IP normal ISP üzerinden: {org}",
                "reason": "normal_connection",
                "organization": self.ip_info.get('org', 'N/A')
            }
            print(f"✅ VPN tespit edilmedi: Normal bağlantı ({org})")
            return self.vpn_detection
            
        except Exception as e:
            self.vpn_detection = {
                "status": "error",
                "message": f"VPN tespiti hatası: {str(e)}"
            }
            print(f"❌ VPN tespiti hatası: {e}")
            return self.vpn_detection
    
    def get_complete_web_info(self, include_speed_test=True):
        """
        Tüm web bilgilerini toplar.
        
        Args:
            include_speed_test (bool): Hız testi yapılsın mı
            
        Returns:
            dict: Tüm web bilgileri
        """
        print("🌐 Web bilgileri toplanıyor...")
        
        web_data = {
            "collection_timestamp": datetime.now().isoformat(),
            "ip_address": None,
            "ip_info": None,
            "speed_test": None,
            "vpn_detection": None
        }
        
        # IP bilgisini al
        ip_info = self.get_ip_info()
        if ip_info:
            web_data["ip_address"] = self.current_ip
            web_data["ip_info"] = ip_info
        
        # VPN tespiti yap
        vpn_result = self.detect_vpn()
        web_data["vpn_detection"] = vpn_result
        
        # Hız testi (opsiyonel)
        if include_speed_test:
            speed_result = self.get_speed_test_info()
            web_data["speed_test"] = speed_result
        
        return web_data
    
    def get_summary(self):
        """
        Web bilgilerinin özetini döndürür.
        
        Returns:
            dict: Özet bilgiler
        """
        summary = {
            "ip_address": self.current_ip or "N/A",
            "location": f"{self.ip_info.get('city', 'N/A')}, {self.ip_info.get('country', 'N/A')}" if self.ip_info else "N/A",
            "isp": self.ip_info.get('org', 'N/A') if self.ip_info else "N/A",
            "vpn_status": self.vpn_detection.get('status', 'N/A') if self.vpn_detection else "N/A",
            "download_speed": f"{self.download_speed} Mbps" if self.download_speed else "N/A",
            "upload_speed": f"{self.upload_speed} Mbps" if self.upload_speed else "N/A",
            "ping": f"{self.ping} ms" if self.ping else "N/A"
        }
        
        return summary
    
    def print_summary(self):
        """Web özetini konsola yazdırır."""
        summary = self.get_summary()
        
        print("\n" + "="*50)
        print("🌐 WEB BİLGİLERİ ÖZETİ")
        print("="*50)
        print(f"🌍 IP Adresi: {summary['ip_address']}")
        print(f"📍 Konum: {summary['location']}")
        print(f"🏢 ISP: {summary['isp']}")
        print(f"🔒 VPN Durumu: {summary['vpn_status']}")
        if summary['download_speed'] != "N/A":
            print(f"⬇️  İndirme: {summary['download_speed']}")
            print(f"⬆️  Yükleme: {summary['upload_speed']}")
            print(f"🏓 Ping: {summary['ping']}")
        print("="*50)