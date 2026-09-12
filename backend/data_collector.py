from datetime import datetime
import time
import json
import asyncio
from elasticsearch_client_v8 import ElasticsearchClient
from system_monitor import SystemMonitor
from web import WebInfo
from config import USER_CONFIG, ELASTICSEARCH_CONFIG

class DataCollector:
	"""
	Sistem ve web verilerini toplayarak Elasticsearch'e kaydeden ana sınıf.
	"""
	
	def __init__(self, es_host=None, es_port=None, es_username=None, es_password=None, use_ssl=None):
		"""
		DataCollector başlatır.
		
		Args:
			es_host (str): Elasticsearch sunucu adresi (None ise config'den alır)
			es_port (int): Elasticsearch portu (None ise config'den alır)
			es_username (str): Kullanıcı adı (opsiyonel)
			es_password (str): Şifre (opsiyonel)
			use_ssl (bool): SSL kullanımı (None ise config'den alır)
		"""
		self.es_client = None
		self.system_monitor = SystemMonitor()
		self.web_info = WebInfo()
		
		# Config'den varsayılan değerleri al
		es_host = es_host or ELASTICSEARCH_CONFIG['host']
		es_port = es_port or ELASTICSEARCH_CONFIG['port']
		es_username = es_username or ELASTICSEARCH_CONFIG['username']
		es_password = es_password or ELASTICSEARCH_CONFIG['password']
		use_ssl = use_ssl if use_ssl is not None else ELASTICSEARCH_CONFIG['use_ssl']
		
		# Elasticsearch bağlantısını kur
		try:
			self.es_client = ElasticsearchClient(
				host=es_host,
				port=es_port,
				username=es_username,
				password=es_password,
				use_ssl=use_ssl
			)
			print("✅ DataCollector başarıyla başlatıldı!")
		except Exception as e:
			print(f"❌ DataCollector başlatılamadı: {e}")
			raise
	
	async def create_indices(self):
		"""
		Gerekli Elasticsearch indekslerini oluşturur.
		"""
		print("📋 İndeksler oluşturuluyor...")
		
		# System monitoring indeksi
		system_mapping = {
			"properties": {
				"timestamp": {"type": "date"},
				"collection_timestamp": {"type": "date"},
				"cpu": {
					"properties": {
						"cpu_percent": {"type": "float"},
						"cpu_count_logical": {"type": "integer"},
						"cpu_count_physical": {"type": "integer"}
					}
				},
				"memory": {
					"properties": {
						"virtual_memory": {
							"properties": {
								"total": {"type": "long"},
								"used": {"type": "long"},
								"available": {"type": "long"},
								"percent": {"type": "float"}
							}
						},
						"swap_memory": {
							"properties": {
								"total": {"type": "long"},
								"used": {"type": "long"},
								"percent": {"type": "float"}
							}
						}
					}
				},
				"disk": {
					"properties": {
						"disk_usage": {
							"properties": {
								"main": {
									"properties": {
										"total": {"type": "long"},
										"used": {"type": "long"},
										"free": {"type": "long"},
										"percent": {"type": "float"}
									}
								}
							}
						}
					}
				},
				"network": {
					"properties": {
						"network_io": {
							"properties": {
								"bytes_sent": {"type": "long"},
								"bytes_recv": {"type": "long"},
								"packets_sent": {"type": "long"},
								"packets_recv": {"type": "long"}
							}
						}
					}
				},
				"system": {
					"properties": {
						"platform": {
							"properties": {
								"system": {"type": "keyword"},
								"node": {"type": "keyword"},
								"release": {"type": "keyword"}
							}
						},
						"uptime": {
							"properties": {
								"total_seconds": {"type": "long"},
								"days": {"type": "integer"}
							}
						}
					}
				}
			}
		}
		
		# Web monitoring indeksi
		web_mapping = {
			"properties": {
				"timestamp": {"type": "date"},
				"collection_timestamp": {"type": "date"},
				"ip_address": {"type": "ip"},
				"ip_info": {
					"properties": {
						"city": {"type": "keyword"},
						"region": {"type": "keyword"},
						"country": {"type": "keyword"},
						"loc": {"type": "geo_point"},
						"org": {"type": "text"},
						"postal": {"type": "keyword"},
						"timezone": {"type": "keyword"}
					}
				},
				"speed_test": {
					"properties": {
						"download_speed": {"type": "float"},
						"upload_speed": {"type": "float"},
						"ping": {"type": "float"},
						"server_info": {
							"properties": {
								"name": {"type": "keyword"},
								"country": {"type": "keyword"},
								"sponsor": {"type": "keyword"}
							}
						}
					}
				},
				"vpn_detection": {
					"properties": {
						"status": {"type": "keyword"},
						"message": {"type": "text"}
					}
				}
			}
		}
		
		# Combined monitoring indeksi
		combined_mapping = {
			"properties": {
				"timestamp": {"type": "date"},
				"data_type": {"type": "keyword"},
				"system_data": system_mapping["properties"],
				"web_data": web_mapping["properties"]
			}
		}

		# Çoklu kullanıcı alanlarını tüm indekslere ekle
		for mapping in (system_mapping, web_mapping, combined_mapping):
			mapping["properties"]["user_id"] = {"type": "keyword"}
			mapping["properties"]["device_id"] = {"type": "keyword"}
		
		# İndeksleri oluştur
		await self.es_client.create_index("system-monitoring", system_mapping)
		await self.es_client.create_index("web-monitoring", web_mapping)
		await self.es_client.create_index("combined-monitoring", combined_mapping)
		
		print("✅ İndeksler başarıyla oluşturuldu!")
	
	async def check_elasticsearch_health(self):
		"""
		Elasticsearch bağlantısını kontrol eder.
		
		Returns:
			bool: Bağlantı sağlıklı mı
		"""
		try:
			return await self.es_client.ping()
		except Exception as e:
			print(f"❌ Elasticsearch sağlık kontrolü hatası: {e}")
			return False
	
	def collect_system_data(self, include_processes=True):
		"""
		Sistem verilerini toplar.
		
		Args:
			include_processes (bool): İşlem bilgileri dahil edilsin mi
			
		Returns:
			dict: Sistem verileri
		"""
		print("💻 Sistem verileri toplanıyor...")
		return self.system_monitor.get_complete_system_info(include_processes=include_processes)
	
	def collect_web_data(self, include_speed_test=True):
		"""
		Web verilerini toplar.
		
		Args:
			include_speed_test (bool): Hız testi yapılsın mı
			
		Returns:
			dict: Web verileri
		"""
		print("🌐 Web verileri toplanıyor...")
		return self.web_info.get_complete_web_info(include_speed_test=include_speed_test)
	
	def collect_all_data(self, include_processes=True, include_speed_test=True):
		"""
		Tüm verileri toplar.
		
		Args:
			include_processes (bool): İşlem bilgileri dahil edilsin mi
			include_speed_test (bool): Hız testi yapılsın mı
			
		Returns:
			dict: Tüm veriler
		"""
		print("📊 Tüm veriler toplanıyor...")
		
		# Sistem verileri
		system_data = self.collect_system_data(include_processes)
		
		# Web verileri
		web_data = self.collect_web_data(include_speed_test)
		
		# Birleştirilmiş veri
		combined_data = {
			"collection_timestamp": datetime.now().isoformat(),
			"system_data": system_data,
			"web_data": web_data
		}
		
		# Çoklu kullanıcı/cihaz etiketleri ekle
		user_id = USER_CONFIG.get('user_id', 'default_user')
		device_id = USER_CONFIG.get('device_id') or self.system_monitor.get_complete_system_info(include_processes=False).get('system', {}).get('platform', {}).get('node', 'unknown-device')

		combined_data['user_id'] = user_id
		combined_data['device_id'] = device_id
		
		# Alt veri bloklarına da etiketleri ekle (kolay filtreleme için)
		if isinstance(combined_data.get('system_data'), dict):
			combined_data['system_data']['user_id'] = user_id
			combined_data['system_data']['device_id'] = device_id
		if isinstance(combined_data.get('web_data'), dict):
			combined_data['web_data']['user_id'] = user_id
			combined_data['web_data']['device_id'] = device_id

		return combined_data
	
	async def save_to_elasticsearch(self, data, index_name="combined-monitoring"):
		"""
		Verileri Elasticsearch'e kaydeder.
		
		Args:
			data (dict): Kaydedilecek veriler
			index_name (str): İndeks adı
			
		Returns:
			bool: Kaydetme başarılı mı
		"""
		try:
			result = await self.es_client.index_document(index_name, data)
			if result:
				print(f"✅ Veriler '{index_name}' indeksine kaydedildi!")
				return True
			else:
				print(f"❌ Veriler '{index_name}' indeksine kaydedilemedi!")
				return False
		except Exception as e:
			print(f"❌ Elasticsearch kaydetme hatası: {e}")
			return False
	
	async def save_system_data(self, system_data):
		"""Sistem verilerini kaydeder."""
		return await self.save_to_elasticsearch(system_data, "system-monitoring")
	
	async def save_web_data(self, web_data):
		"""Web verilerini kaydeder."""
		return await self.save_to_elasticsearch(web_data, "web-monitoring")
	
	async def save_combined_data(self, combined_data):
		"""Birleştirilmiş verileri kaydeder."""
		return await self.save_to_elasticsearch(combined_data, "combined-monitoring")
	
	async def get_latest_data(self, limit=100):
		"""
		En son toplanan verileri getirir.
		
		Args:
			limit (int): Kaç kayıt getirilecek
			
		Returns:
			list: Veri listesi
		"""
		try:
			return await self.es_client.search_documents("combined-monitoring", limit=limit)
		except Exception as e:
			print(f"❌ Veri getirme hatası: {e}")
			return []
	
	def run_single_collection(self, include_processes=True, include_speed_test=True, save_separate=False):
		"""
		Tek seferlik veri toplama ve kaydetme işlemi.
		
		Args:
			include_processes (bool): İşlem bilgileri dahil edilsin mi
			include_speed_test (bool): Hız testi yapılsın mı
			save_separate (bool): Veriler ayrı indekslere de kaydedilsin mi
			
		Returns:
			dict: Toplanan veriler
		"""
		print("\n🚀 Tek seferlik veri toplama başlatılıyor...")
		print("="*60)
		
		# Verileri topla
		combined_data = self.collect_all_data(include_processes, include_speed_test)
		
		if combined_data:
			# Ana combined indeksine kaydet
			success = self.save_combined_data(combined_data)
			
			# İsteğe bağlı olarak ayrı indekslere de kaydet
			if save_separate and success:
				if combined_data.get('system_data'):
					self.save_system_data(combined_data['system_data'])
				if combined_data.get('web_data'):
					self.save_web_data(combined_data['web_data'])
			
			if success:
				print("\n✅ Veri toplama ve kaydetme işlemi tamamlandı!")
				self.print_collection_summary(combined_data)
			else:
				print("\n❌ Veri kaydetme işlemi başarısız!")
				
		else:
			print("\n❌ Veri toplama işlemi başarısız!")
		
		return combined_data
	
	def run_continuous_collection(self, interval=300, include_processes=True, include_speed_test_interval=4):
		"""
		Sürekli veri toplama işlemi.
		
		Args:
			interval (int): Toplama aralığı (saniye)
			include_processes (bool): İşlem bilgileri dahil edilsin mi
			include_speed_test_interval (int): Kaç döngüde bir hız testi yapılsın
		"""
		print(f"\n🔄 Sürekli monitoring başlatılıyor...")
		print(f"⏰ Toplama aralığı: {interval} saniye")
		print(f"⚡ Hız testi aralığı: Her {include_speed_test_interval} döngüde bir")
		print("🛑 Durdurmak için Ctrl+C tuşlayın")
		print("="*60)
		
		collection_count = 0
		
		try:
			while True:
				collection_count += 1
				
				print(f"\n📊 Veri toplama #{collection_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
				print("-" * 40)
				
				# Hız testinin yapılıp yapılmayacağını belirle
				do_speed_test = (collection_count % include_speed_test_interval == 1)
				
				# Verileri topla ve kaydet
				combined_data = self.collect_all_data(include_processes, do_speed_test)
				
				if combined_data:
					success = self.save_combined_data(combined_data)
					if success:
						print(f"✅ Döngü #{collection_count} tamamlandı!")
						self.print_brief_summary(combined_data)
					else:
						print(f"❌ Döngü #{collection_count} kaydetme hatası!")
				else:
					print(f"❌ Döngü #{collection_count} veri toplama hatası!")
				
				# Bekleme
				print(f"⏳ {interval} saniye bekleniyor...")
				time.sleep(interval)
				
		except KeyboardInterrupt:
			print(f"\n\n🛑 Monitoring durduruldu. Toplam {collection_count} döngü tamamlandı.")
		except Exception as e:
			print(f"\n❌ Monitoring hatası: {e}")
	
	def print_collection_summary(self, data):
		"""Toplanan verilerin özetini yazdırır."""
		print("\n📈 TOPLANAN VERİLER ÖZETİ")
		print("="*50)
		
		# Sistem özeti
		if data.get('system_data'):
			system_summary = self.system_monitor.get_summary()
			print("💻 SİSTEM BİLGİLERİ:")
			for key, value in system_summary.items():
				print(f"   {key.replace('_', ' ').title()}: {value}")
		
		# Web özeti
		if data.get('web_data'):
			web_summary = self.web_info.get_summary()
			print("\n🌐 WEB BİLGİLERİ:")
			for key, value in web_summary.items():
				print(f"   {key.replace('_', ' ').title()}: {value}")
		
		print("="*50)
	
	def print_brief_summary(self, data):
		"""Kısa özet yazdırır."""
		if data.get('system_data', {}).get('cpu'):
			cpu_percent = data['system_data']['cpu'].get('cpu_percent', 'N/A')
			memory_percent = data['system_data']['memory']['virtual_memory'].get('percent', 'N/A') if data['system_data'].get('memory') else 'N/A'
			print(f"   💻 CPU: {cpu_percent}% | RAM: {memory_percent}%")
		
		if data.get('web_data', {}).get('ip_address'):
			ip_addr = data['web_data']['ip_address']
			vpn_status = data['web_data']['vpn_detection']['status'] if data['web_data'].get('vpn_detection') else 'N/A'
			print(f"   🌐 IP: {ip_addr} | VPN: {vpn_status}")
	
	def get_elasticsearch_stats(self):
		"""Elasticsearch istatistiklerini alır."""
		try:
			# Cluster health
			health = self.es_client.get_cluster_health()
			
			# Index stats
			indices = ["system-monitoring", "web-monitoring", "combined-monitoring"]
			stats_info = {}
			
			for index in indices:
				try:
					stats = self.es_client.get_index_stats(index)
					if stats:
						# ES 8.x tek indeks stats yapısı: stats['total'] içinde docs/store bilgileri
						# Alternatif olarak stats['primaries'] olabilir; ikisini de destekle
						total_section = stats.get('total', {})
						primaries_section = stats.get('primaries', {})

						doc_count = (
							total_section.get('docs', {}).get('count')
							if total_section.get('docs') is not None
							else primaries_section.get('docs', {}).get('count', 0)
						)

						size_bytes = (
							total_section.get('store', {}).get('size_in_bytes')
							if total_section.get('store') is not None
							else primaries_section.get('store', {}).get('size_in_bytes', 0)
						)

						size_mb = (size_bytes or 0) / (1024 * 1024)

						stats_info[index] = {
							"document_count": doc_count or 0,
							"size_mb": round(size_mb, 2)
						}
				except:
					stats_info[index] = {"document_count": 0, "size_mb": 0}
			
			return {
				"cluster_health": health,
				"index_stats": stats_info
			}
			
		except Exception as e:
			print(f"❌ Elasticsearch istatistikleri alınamadı: {e}")
			return None
	
	def print_elasticsearch_stats(self):
		"""Elasticsearch istatistiklerini yazdırır."""
		stats = self.get_elasticsearch_stats()
		if stats:
			print("\n📊 ELASTICSEARCH İSTATİSTİKLERİ")
			print("="*50)
			
			if stats['cluster_health']:
				health = stats['cluster_health']
				print(f"Cluster Durumu: {health.get('status', 'N/A')}")
				print(f"Toplam Node: {health.get('number_of_nodes', 'N/A')}")
				print(f"Aktif Shard: {health.get('active_shards', 'N/A')}")
			
			print("\nİndeks İstatistikleri:")
			for index, info in stats['index_stats'].items():
				print(f"  {index}:")
				print(f"    Doküman Sayısı: {info['document_count']}")
				print(f"    Boyut: {info['size_mb']} MB")
			
			print("="*50)
