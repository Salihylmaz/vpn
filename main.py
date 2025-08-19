#!/usr/bin/env python3
"""
Ana Monitoring ve Query Sistemi
- Sistem ve web verilerini 2 dakikada bir toplar
- Elasticsearch'e kaydeder  
- DialoGPT ile sorgulama yapar
"""

import time
import threading
from datetime import datetime
from data_collector import DataCollector
from query_system import QuerySystem
from config import ELASTICSEARCH_CONFIG, MONITORING_CONFIG

class MonitoringApp:
    """
    Ana monitoring uygulaması.
    Veri toplama ve sorgu sistemini yönetir.
    """
    
    def __init__(self):
        print("🚀 Monitoring Uygulaması başlatılıyor...")
        
        # Veri toplayıcıyı başlat
        try:
            self.data_collector = DataCollector(
                es_host=ELASTICSEARCH_CONFIG['host'],
                es_port=ELASTICSEARCH_CONFIG['port'],
                es_username=ELASTICSEARCH_CONFIG['username'],
                es_password=ELASTICSEARCH_CONFIG['password'],
                use_ssl=ELASTICSEARCH_CONFIG['use_ssl']
            )
            print("✅ Data Collector başlatıldı")
            
        except Exception as e:
            print(f"❌ Data Collector başlatılamadı: {e}")
            raise
        
        # Query sistemini başlat (lazy loading)
        self.query_system = None
        
        # Monitoring durumu
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # İndeksleri oluştur
        self.setup_elasticsearch()
    
    def setup_elasticsearch(self):
        """
        Elasticsearch indekslerini hazırlar.
        """
        print("📋 Elasticsearch indeksleri kontrol ediliyor...")
        try:
            self.data_collector.create_indices()
        except Exception as e:
            print(f"⚠️ İndeks oluşturma uyarısı: {e}")
    
    def start_query_system(self):
        """
        Query sistemini lazy loading ile başlatır.
        """
        if self.query_system is None:
            print("🤖 Query System başlatılıyor (bu birkaç dakika sürebilir)...")
            try:
                self.query_system = QuerySystem(
                    es_host=ELASTICSEARCH_CONFIG['host'],
                    es_port=ELASTICSEARCH_CONFIG['port'],
                    es_username=ELASTICSEARCH_CONFIG['username'],
                    es_password=ELASTICSEARCH_CONFIG['password'],
                    use_ssl=ELASTICSEARCH_CONFIG['use_ssl']
                )
                print("✅ Query System hazır!")
            except Exception as e:
                print(f"❌ Query System başlatılamadı: {e}")
                return False
        return True
    
    def collect_single_data(self, include_speed_test=True, save_separate=True):
        """
        Tek seferlik veri toplama.
        
        Args:
            include_speed_test (bool): Hız testi yapılsın mı
            save_separate (bool): Sistem ve web verilerini ayrı indekslere de kaydet
            
        Returns:
            bool: Başarılı olup olmadığı
        """
        try:
            print(f"\n📊 Veri toplama başlatıldı - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 50)
            
            # Verileri topla
            combined_data = self.data_collector.collect_all_data(
                include_processes=True,
                include_speed_test=include_speed_test
            )
            
            if combined_data:
                # Elasticsearch'e kaydet (birleşik)
                success = self.data_collector.save_combined_data(combined_data)
                
                # İsteğe bağlı: Ayrı indekslere de kaydet
                if success and save_separate:
                    if combined_data.get('system_data'):
                        self.data_collector.save_system_data(combined_data['system_data'])
                    if combined_data.get('web_data'):
                        self.data_collector.save_web_data(combined_data['web_data'])
                
                if success:
                    print("✅ Veri toplama ve kaydetme başarılı!")
                    self.data_collector.print_brief_summary(combined_data)
                    return True
                else:
                    print("❌ Veri kaydetme başarısız!")
                    return False
            else:
                print("❌ Veri toplama başarısız!")
                return False
                
        except Exception as e:
            print(f"❌ Veri toplama hatası: {e}")
            return False
    
    def monitoring_worker(self, interval=120, speed_test_interval=5, save_separate=True):
        """
        Arka planda çalışan monitoring işlemi.
        
        Args:
            interval (int): Toplama aralığı (saniye, varsayılan: 120 = 2 dakika)
            speed_test_interval (int): Kaç döngüde bir hız testi yapılsın
        """
        print(f"🔄 Monitoring başlatıldı:")
        print(f"   ⏰ Aralık: {interval} saniye ({interval//60} dakika)")
        print(f"   ⚡ Hız testi: Her {speed_test_interval} döngüde bir")
        
        cycle_count = 0
        
        while self.monitoring_active:
            try:
                cycle_count += 1
                
                # Hız testi yapılacak mı?
                do_speed_test = (cycle_count % speed_test_interval == 1)
                
                print(f"\n🔄 Döngü #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                if do_speed_test:
                    print("   ⚡ Bu döngüde hız testi de yapılacak")
                
                # Veri topla
                success = self.collect_single_data(include_speed_test=do_speed_test, save_separate=save_separate)
                
                if success:
                    print(f"✅ Döngü #{cycle_count} tamamlandı")
                else:
                    print(f"❌ Döngü #{cycle_count} başarısız")
                
                # Sonraki döngüye kadar bekle
                if self.monitoring_active:
                    print(f"⏳ Sonraki döngü: {interval} saniye sonra...")
                    
                    # Kesintiye karşı bölümlü bekleme
                    for _ in range(interval):
                        if not self.monitoring_active:
                            break
                        time.sleep(1)
                        
            except Exception as e:
                print(f"❌ Monitoring döngüsü hatası: {e}")
                if self.monitoring_active:
                    print("⏳ 30 saniye bekleyip devam ediliyor...")
                    time.sleep(30)
        
        print("🛑 Monitoring durduruldu")
    
    def start_monitoring(self, interval=120, speed_test_interval=5, save_separate=True):
        """
        Monitoring'i başlatır.
        
        Args:
            interval (int): Toplama aralığı (saniye)
            speed_test_interval (int): Hız testi aralığı (döngü sayısı)
        """
        if self.monitoring_active:
            print("⚠️ Monitoring zaten aktif!")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self.monitoring_worker,
            args=(interval, speed_test_interval, save_separate),
            daemon=True
        )
        self.monitoring_thread.start()
        print("✅ Monitoring arka planda başlatıldı!")
    
    def stop_monitoring(self):
        """
        Monitoring'i durdurur.
        """
        if not self.monitoring_active:
            print("⚠️ Monitoring zaten durmuş!")
            return
        
        print("🛑 Monitoring durduruluyor...")
        self.monitoring_active = False
        
        # Thread'in bitmesini bekle
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        print("✅ Monitoring durduruldu!")
    
    def show_elasticsearch_stats(self):
        """
        Elasticsearch istatistiklerini gösterir.
        """
        self.data_collector.print_elasticsearch_stats()
    
    def query_mode(self):
        """
        Query moduna geçer.
        """
        if not self.start_query_system():
            return
        
        print("\n🤖 Query moduna geçiliyor...")
        self.query_system.interactive_mode()
    
    def main_menu(self):
        """
        Ana menüyü görüntüler ve kullanıcı seçimlerini işler.
        """
        while True:
            print("\n" + "="*60)
            print("🖥️  SİSTEM VE AĞ MONİTORİNG UYGULAMASI")
            print("="*60)
            print("1. 📊 Tek seferlik veri toplama")
            print("2. 🔄 Sürekli monitoring başlat (2 dakika aralık)")
            print("3. 🛑 Monitoring durdur")
            print("4. 📈 Elasticsearch istatistikleri")
            print("5. 🤖 AI Query sistemi (Qwen)")
            print("6. ⚙️  Ayarlar")
            print("7. 🚪 Çıkış")
            
            # Monitoring durumu
            status = "🟢 Aktif" if self.monitoring_active else "🔴 Durmuş"
            print(f"\nMonitoring Durumu: {status}")
            
            try:
                choice = input("\nSeçiminiz (1-7): ").strip()
                
                if choice == '1':
                    print("\n📊 TEK SEFERLİK VERİ TOPLAMA")
                    print("-" * 30)
                    speed_test = input("Hız testi yapılsın mı? (y/n, varsayılan: y): ").strip().lower()
                    include_speed = speed_test != 'n'
                    self.collect_single_data(include_speed_test=include_speed)
                
                elif choice == '2':
                    print("\n🔄 SÜREKLİ MONİTORİNG")
                    print("-" * 20)
                    
                    # Aralık ayarı
                    interval_input = input("Toplama aralığı (dakika, varsayılan: 2): ").strip()
                    try:
                        interval_minutes = int(interval_input) if interval_input else 2
                        interval_seconds = interval_minutes * 60
                    except ValueError:
                        interval_seconds = 120  # 2 dakika varsayılan
                    
                    # Hız testi aralığı
                    speed_interval_input = input("Kaç döngüde bir hız testi? (varsayılan: 5): ").strip()
                    try:
                        speed_interval = int(speed_interval_input) if speed_interval_input else 5
                    except ValueError:
                        speed_interval = 5
                    
                    self.start_monitoring(interval_seconds, speed_interval)
                
                elif choice == '3':
                    self.stop_monitoring()
                
                elif choice == '4':
                    print("\n📈 ELASTICSEARCH İSTATİSTİKLERİ")
                    print("-" * 30)
                    self.show_elasticsearch_stats()
                
                elif choice == '5':
                    print("\n🤖 AI QUERY SİSTEMİ")
                    print("-" * 20)
                    self.query_mode()
                
                elif choice == '6':
                    self.settings_menu()
                
                elif choice == '7':
                    print("\n🚪 Çıkış yapılıyor...")
                    self.stop_monitoring()  # Monitoring varsa durdur
                    print("👋 Görüşürüz!")
                    break
                
                else:
                    print("⚠️ Geçersiz seçim! Lütfen 1-7 arası bir sayı girin.")
                    
            except KeyboardInterrupt:
                print("\n\n🛑 Uygulama kesintiye uğradı...")
                self.stop_monitoring()
                print("👋 Görüşürüz!")
                break
            except Exception as e:
                print(f"❌ Menü hatası: {e}")
    
    def settings_menu(self):
        """
        Ayarlar menüsü.
        """
        while True:
            print("\n" + "="*40)
            print("⚙️  AYARLAR")
            print("="*40)
            print("1. 📊 Elasticsearch bağlantı testi")
            print("2. 🌐 Web bağlantı testi")
            print("3. 💻 Sistem bilgilerini göster")
            print("4. 🔙 Ana menüye dön")
            
            choice = input("\nSeçiminiz (1-4): ").strip()
            
            if choice == '1':
                print("\n📊 ELASTICSEARCH BAĞLANTI TESTİ")
                print("-" * 30)
                try:
                    stats = self.data_collector.get_elasticsearch_stats()
                    if stats:
                        print("✅ Elasticsearch bağlantısı başarılı!")
                        print(f"Cluster durumu: {stats['cluster_health'].get('status', 'N/A')}")
                    else:
                        print("❌ Elasticsearch bağlantısı başarısız!")
                except Exception as e:
                    print(f"❌ Bağlantı testi hatası: {e}")
            
            elif choice == '2':
                print("\n🌐 WEB BAĞLANTI TESTİ")
                print("-" * 20)
                from web import WebInfo
                web_info = WebInfo()
                ip_result = web_info.get_ip_info()
                if ip_result:
                    print("✅ İnternet bağlantısı başarılı!")
                    web_info.print_summary()
                else:
                    print("❌ İnternet bağlantısı başarısız!")
            
            elif choice == '3':
                print("\n💻 SİSTEM BİLGİLERİ")
                print("-" * 20)
                from system_monitor import SystemMonitor
                system_monitor = SystemMonitor()
                system_monitor.print_summary()
            
            elif choice == '4':
                break
            
            else:
                print("⚠️ Geçersiz seçim!")

def main():
    """
    Ana fonksiyon.
    """
    print("🎯 Monitoring Uygulaması Başlatılıyor...")
    print("="*60)
    
    try:
        app = MonitoringApp()
        app.main_menu()
        
    except KeyboardInterrupt:
        print("\n👋 Uygulama kapatılıyor...")
    except Exception as e:
        print(f"❌ Kritik hata: {e}")
        print("Lütfen Elasticsearch'in çalıştığından emin olun.")

if __name__ == "__main__":
    main()