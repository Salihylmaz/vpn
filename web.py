import psutil, platform, subprocess, requests, speedtest


class WebInfo:
    def __init__(self):
        self.download_speed = None
        self.upload_speed = None
        self.ping = None
        self.current_ip = None
        self.ip_info = None
        self.expected_country = "TR"  # Beklenen ülke kodu

    def get_speed_test_info(self):
        try:    
            st = speedtest.Speedtest()
            st.get_best_server()
            self.download_speed = round(st.download() / 1_000_000, 2)  # Mbps
            self.upload_speed = round(st.upload() / 1_000_000, 2)   # Mbps
            self.ping = st.results.ping

            return {
                "download_speed": self.download_speed,
                "upload_speed": self.upload_speed,
                "ping": self.ping
            }
        
        except Exception as e:
            return f"Speed test failed: {e}"
    
    def get_ip_info(self):
        try:
            self.current_ip = requests.get("https://api.ipify.org").text
            response = requests.get(f"https://ipinfo.io/{self.current_ip}/json") #https://ipinfo.io/88.239.131.208/json olmalı
            if response.status_code == 200:
                self.ip_info = response.json()
                return self.ip_info
            else:
                print("[!] IP info retrieval failed.")
                return None

        except requests.RequestException as e:
            print(f"IP info retrieval failed: {e}")
            return None
    
    def VPN_info(self):
        """
            Ülke, IP ve ISP farkına göre VPN tespiti yapar.
            Beklenen ülke kodu 'TR' olarak ayarlanmıştır.
            Eğer IP bilgisi alınamazsa veya beklenen ülke ile uyuşmuyorsa VPN kullanılıyor olabilir.
            Ayrıca, IP sağlayıcısının organizasyon bilgisi üzerinden VPN veya proxy kullanımı tespit edilir.

        """
        
        try:
            if not self.ip_info:
                return "IP bilgisi alınamadı"
            
            country = self.ip_info.get('country', '').upper()
            city = self.ip_info.get('city', '')
            org = self.ip_info.get('org', '').lower()

            if country != self.expected_country:
                return f"VPN bağlı olabilir: IP{city} {country} olarak görünüyor, beklenen ülke {self.expected_country}."
            
            if any(vpn_kw in org for vpn_kw in ['vpn', 'hosting','datacenter', 'proxy','cloud', 'tor']):
                return f"VPN veya proxy kullanılıyor: {org}."
            
            return "VPN veya proxy kullanılmıyor."
        except requests.RequestException as e:
            return f"VPN info retrieval failed: {e}"
        
    def get_web_info(self):
        return {
            "download_speed": self.download_speed,
            "upload_speed": self.upload_speed,
            "ping": self.ping,
            "ip_info": self.ip_info,
            "vpn_status": self.VPN_info()
        }