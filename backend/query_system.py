import torch
import sys
import os
from transformers import AutoTokenizer, AutoModelForCausalLM
from elasticsearch_client_v8 import ElasticsearchClient
from config import USER_CONFIG, ELASTICSEARCH_CONFIG, MODEL_CONFIG
from datetime import datetime, timedelta
import re
import json
import asyncio
import signal
import time

class ModelManager:
	"""
	HuggingFace modellerini yöneten sınıf.
	"""
	
	def __init__(self):
		self.current_model = None
		self.current_tokenizer = None
		self.current_model_id = None
		self.model_cache = {}
		self.available_models = MODEL_CONFIG['available_models']
		
	def get_available_models(self):
		"""Mevcut modellerin listesini döner."""
		return self.available_models
	
	def get_model_by_id(self, model_id):
		"""Model ID'sine göre model bilgisini döner."""
		for model in self.available_models:
			if model['id'] == model_id:
				return model
		return None
	
	def get_current_model_info(self):
		"""Şu anda yüklü olan model bilgisini döner."""
		if self.current_model_id:
			return self.get_model_by_id(self.current_model_id)
		return None
	
	def load_model(self, model_id=None, force_reload=False):
		"""
		Belirtilen modeli yükler.
		
		Args:
			model_id (str): Yüklenecek model ID'si
			force_reload (bool): Zaten yüklüyse tekrar yükle
			
		Returns:
			tuple: (model, tokenizer) veya None
		"""
		# Varsayılan model
		if not model_id:
			model_id = os.environ.get("MODEL_ID", "dialogpt-small")  # Changed to causal LM
		
		# Zaten yüklüyse ve force_reload değilse mevcut modeli döner
		if not force_reload and self.current_model_id == model_id and self.current_model:
			print(f"✅ Model zaten yüklü: {model_id}")
			return self.current_model, self.current_tokenizer
		
		# Model bilgisini al
		model_info = self.get_model_by_id(model_id)
		if not model_info:
			print(f"❌ Model bulunamadı: {model_id}")
			# Auto fallback to smallest model
			if MODEL_CONFIG.get('auto_fallback'):
				print("🔄 En küçük modele geçiliyor...")
				return self.load_model('tiny-model', force_reload=True)
			return None, None
		
		model_name = model_info['name']
		print(f"📥 Model yükleniyor: {model_info['display_name']} ({model_name})")
		
		# Timeout handler
		def timeout_handler(signum, frame):
			raise TimeoutError("Model loading timeout")
		
		try:
			# Set timeout for model loading (5 minutes)
			signal.signal(signal.SIGALRM, timeout_handler)
			signal.alarm(300)  # 5 minutes timeout
			
			start_time = time.time()
			
			# Performans ayarları
			configured_threads = int(os.environ.get("TORCH_NUM_THREADS", "0"))
			if configured_threads <= 0:
				cpu_count = os.cpu_count() or 4
				configured_threads = min(2, cpu_count)
			torch.set_num_threads(configured_threads)
			print(f"🧵 Torch threads: {configured_threads}")
			
			# HuggingFace token
			hf_token = os.environ.get("HF_TOKEN")
			
			# Tokenizer yükle
			tokenizer = AutoTokenizer.from_pretrained(
				model_name,
				use_fast=True,
				token=hf_token
			)
			
			# Cihaz ve dtype seçimi
			use_cuda = torch.cuda.is_available()
			model_kwargs = {
				"low_cpu_mem_usage": True,  # Always use low CPU memory
				"trust_remote_code": True,
			}
			
			if use_cuda:
				model_kwargs.update({
					"torch_dtype": torch.float16,
					"device_map": "auto"
				})
				print("🟢 CUDA bulundu, model GPU'da yüklenecek (fp16)")
			else:
				# CPU için memory optimizasyonları
				model_kwargs.update({
					"torch_dtype": torch.float16,  # fp16 kullan, fp32 yerine
					"load_in_8bit": False,  # 8-bit quantization devre dışı (CPU'da desteklenmiyor)
					"load_in_4bit": False,  # 4-bit quantization devre dışı (CPU'da desteklenmiyor)
				})
				print("🟠 CUDA yok, model CPU'da yüklenecek (fp16 - memory optimized)")
			
			# Model yükle
			model = AutoModelForCausalLM.from_pretrained(
				model_name,
				token=hf_token,
				**model_kwargs
			)
			
			# Memory optimization for CPU
			if not use_cuda:
				# Gradient checkpointing'i etkinleştir (memory tasarrufu için)
				if hasattr(model, 'gradient_checkpointing_enable'):
					model.gradient_checkpointing_enable()
				
				# Model'i CPU'ya taşı ve optimize et
				model = model.to('cpu')
				
			model.eval()
			
			# Clear timeout
			signal.alarm(0)
			
			# Pad token ekle
			if tokenizer.pad_token is None:
				tokenizer.pad_token = tokenizer.eos_token
			
			# Eski modeli temizle
			if self.current_model:
				del self.current_model
				del self.current_tokenizer
				torch.cuda.empty_cache() if torch.cuda.is_available() else None
			
			# Yeni modeli kaydet
			self.current_model = model
			self.current_tokenizer = tokenizer
			self.current_model_id = model_id
			
			load_time = time.time() - start_time
			print(f"✅ Model başarıyla yüklendi: {model_info['display_name']} ({load_time:.1f}s)")
			return model, tokenizer
			
		except (Exception, TimeoutError) as e:
			# Clear timeout
			signal.alarm(0)
			
			print(f"❌ Model yükleme hatası ({model_name}): {e}")
			
			# Auto fallback
			if MODEL_CONFIG.get('auto_fallback') and model_id not in MODEL_CONFIG['fallback_order']:
				print("🔄 Fallback modeli deneniyor...")
				for fallback_id in MODEL_CONFIG['fallback_order']:
					if fallback_id != model_id:
						try:
							return self.load_model(fallback_id, force_reload=True)
						except Exception as fallback_error:
							print(f"❌ Fallback model hatası ({fallback_id}): {fallback_error}")
							continue
			
			return None, None

class QuerySystem:
	"""
	Dinamik model seçimi ile Elasticsearch'ten veri sorgulayan sistem.
	"""
	
	def __init__(self, es_host=None, es_port=None, es_username=None, es_password=None, use_ssl=None, model_id=None):
		print("🤖 Query System başlatılıyor...")
		
		# Config'den varsayılan değerleri al
		es_host = es_host or ELASTICSEARCH_CONFIG['host']
		es_port = es_port or ELASTICSEARCH_CONFIG['port']
		es_username = es_username or ELASTICSEARCH_CONFIG['username']
		es_password = es_password or ELASTICSEARCH_CONFIG['password']
		use_ssl = use_ssl if use_ssl is not None else ELASTICSEARCH_CONFIG['use_ssl']
		
		# Elasticsearch bağlantısı
		self.es_client = ElasticsearchClient(
			host=es_host,
			port=es_port,
			username=es_username,
			password=es_password,
			use_ssl=use_ssl
		)
		
		# Model manager'ı başlat
		self.model_manager = ModelManager()
		
		# İlk modeli yükle
		self.model, self.tokenizer = self.model_manager.load_model(model_id)
		
		if not self.model or not self.tokenizer:
			raise Exception("Model yüklenemedi!")
		
		# Model ayarları
		self.model_settings = MODEL_CONFIG['model_settings'].copy()
		
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
			r'(\d+) hafta önce': lambda m: {
				'days_ago': int(m.group(1)) * 7,
				'period': 'week'
			},
			r'(\d+) gün önce': lambda m: {
				'days_ago': int(m.group(1)),
				'period': 'day'
			},
			r'(\d+) ay önce': lambda m: {
				'days_ago': int(m.group(1)) * 30,
				'period': 'month'
			},
			r'(\d{1,2}):(\d{2})': lambda m: {
				'specific_time': f"{m.group(1).zfill(2)}:{m.group(2)}"
			},
			r'bugün': lambda m: {'days': 0, 'specific_day': 'today'},
			r'dün': lambda m: {'days': 1, 'specific_day': 'yesterday'},
			r'bu sabah': lambda m: {'hours': 12, 'specific_period': 'morning'},
			r'bu akşam': lambda m: {'hours': 6, 'specific_period': 'evening'},
			r'bu hafta': lambda m: {'days': 7, 'specific_period': 'week'},
			r'bu ay': lambda m: {'days': 30, 'specific_period': 'month'}
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
				elif 'specific_day' in time_info:
					# Belirli gün
					if time_info['specific_day'] == 'today':
						# Bugün: günün başından şu ana kadar
						start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
						end_time = now
					elif time_info['specific_day'] == 'yesterday':
						# Dün: dünün başından sonuna kadar
						yesterday = now - timedelta(days=1)
						start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
						end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
				elif 'days_ago' in time_info:
					# N gün/hafta/ay önceki günün tamamı
					target_day = now - timedelta(days=time_info['days_ago'])
					start_time = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
					end_time = target_day.replace(hour=23, minute=59, second=59, microsecond=999999)
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
		
		# Gelişmiş amaç kalıpları - daha detaylı ve esnek
		intent_patterns = {
			'vpn_status': [
				r'vpn.*bağlı', r'vpn.*kullan', r'vpn.*aktif', r'vpn.*durum',
				r'proxy.*kullan', r'bağlantı.*güvenli', r'vpn.*çalış'
			],
			'speed_info': [
				r'hız.*test', r'internet.*hız', r'download.*speed', r'upload.*speed',
				r'ping', r'bant.*genişlik', r'mbps', r'bağlantı.*hız'
			],
			'system_info': [
				r'sistem.*durum', r'cpu.*kullan', r'ram.*kullan', r'bellek.*kullan',
				r'disk.*kullan', r'performans', r'bilgisayar.*durum'
			],
			'location_info': [
				r'ip.*adres', r'konum', r'nerde', r'hangi.*şehir', r'hangi.*ülke',
				r'ülke.*nerde', r'şehir.*nerde'
			],
			'device_listing': [
				r'hangi.*bilgisayar', r'kaç.*bilgisayar', r'cihaz.*listesi', r'bilgisayar.*listesi',
				r'cihaz.*var', r'bilgisayar.*var', r'device.*list', r'computer.*list'
			],
			'time_analysis': [
				r'hangi.*saat', r'kaç.*saat', r'saat.*aralık', r'zaman.*aralık',
				r'ne.*zaman', r'zaman.*bilgi', r'time.*range', r'hour.*range'
			],
			'data_coverage': [
				r'veri.*var', r'bilgi.*var', r'kayıt.*var', r'data.*available',
				r'coverage', r'kapsam', r'mevcut.*veri'
			],
			'general_status': [
				r'durum.*nedir', r'ne.*olmuş', r'bilgi.*ver', r'özet', r'genel.*durum'
			]
		}
		
		for intent, patterns in intent_patterns.items():
			for pattern in patterns:
				match = re.search(pattern, query)
				if match:
					return {
						'intent': intent,
						'confidence': 0.9,
						'matched_pattern': pattern
					}
		
		# Eğer hiçbir kalıp eşleşmezse, daha akıllı tahmin yap
		query_words = query.split()
		if any(word in query_words for word in ['bilgisayar', 'cihaz', 'computer', 'device']):
			return {'intent': 'device_listing', 'confidence': 0.7, 'matched_pattern': 'word_based'}
		elif any(word in query_words for word in ['saat', 'zaman', 'time', 'hour']):
			return {'intent': 'time_analysis', 'confidence': 0.7, 'matched_pattern': 'word_based'}
		elif any(word in query_words for word in ['veri', 'bilgi', 'data', 'kayıt']):
			return {'intent': 'data_coverage', 'confidence': 0.7, 'matched_pattern': 'word_based'}
		
		return {
			'intent': 'general_status',
			'confidence': 0.6,
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
		# Kullanıcı/cihaz filtresi - sadece gerekirse ekle
		user_id = USER_CONFIG.get('user_id', 'default_user')
		device_id = USER_CONFIG.get('device_id')

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
		
		# Kullanıcı filtresi sadece gerekirse ekle (veri varsa)
		if user_id and user_id != 'default_user':
			base_query["query"]["bool"]["must"].append({"term": {"user_id": user_id}})
		
		if device_id:
			base_query["query"]["bool"]["must"].append({"term": {"device_id": device_id}})
		
		# Amaca göre ek filtreler
		if intent['intent'] == 'vpn_status':
			base_query["query"]["bool"]["must"].append({
				"exists": {"field": "web_data.vpn_detection"}
			})
		
		return base_query
	
	async def search_data(self, intent, time_range):
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
			results = await self.es_client.search_documents("combined-monitoring", query.get("query"), query.get("size", 10))
			
			return results
			
		except Exception as e:
			print(f"❌ Elasticsearch sorgu hatası: {e}")
			return []

	async def count_records(self, time_range):
		"""Belirli zaman aralığında toplam kayıt sayısı."""
		try:
			query = {
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
			}
			# Async count_documents metodunu çağır
			result = await self.es_client.count_documents("combined-monitoring", query)
			return result
		except Exception as e:
			print(f"❌ Count hatası: {e}")
			return 0

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
			return "Belirtilen zamanda/kriterde veri bulunamadı."
		
		try:
			if intent['intent'] == 'vpn_status':
				# VPN durumu için daha okunaklı format
				vpn_records = []
				for item in data:
					vpn_info = item.get('web_data', {}).get('vpn_detection', {})
					if vpn_info:
						timestamp = item.get('collection_timestamp', 'Bilinmiyor')[:16]  # YYYY-MM-DD HH:MM
						status = vpn_info.get('status', 'bilinmiyor')
						message = vpn_info.get('message', 'Detay yok')
						vpn_records.append(f"🕐 {timestamp} → {status} ({message})")
				
				if vpn_records:
					records_text = "\n".join(vpn_records[:10])  # Son 10 kayıt
					summary = f"\n\n📊 Toplam {len(vpn_records)} kayıt bulundu"
					if len(vpn_records) > 10:
						summary += f" (son 10 tanesi gösteriliyor)"
					return f"VPN Durum Geçmişi:\n\n{records_text}{summary}"
				else:
					return "VPN durum bilgisi bulunamadı."
			
			elif intent['intent'] == 'speed_info':
				latest_data = data[0]  # En son veri
				speed_info = latest_data.get('web_data', {}).get('speed_test', {})
				if speed_info:
					return f"Hız bilgisi - İndirme: {speed_info.get('download_speed', 'N/A')} Mbps, Yükleme: {speed_info.get('upload_speed', 'N/A')} Mbps, Ping: {speed_info.get('ping', 'N/A')} ms"
			
			elif intent['intent'] == 'system_info':
				latest_data = data[0]  # En son veri
				system_data = latest_data.get('system_data', {})
				cpu = system_data.get('cpu', {}).get('cpu_percent', 'N/A')
				memory = system_data.get('memory', {}).get('virtual_memory', {}).get('percent', 'N/A')
				disk = system_data.get('disk', {}).get('disk_usage', {}).get('main', {}).get('percent', 'N/A')
				
				return f"Sistem durumu - CPU: {cpu}%, RAM: {memory}%, Disk: {disk}%"
			
			elif intent['intent'] == 'location_info':
				latest_data = data[0]  # En son veri
				ip_info = latest_data.get('web_data', {}).get('ip_info', {})
				if ip_info:
					return f"Konum bilgisi: {ip_info.get('city', 'N/A')}, {ip_info.get('country', 'N/A')} ({latest_data.get('web_data', {}).get('ip_address', 'N/A')})"
			
			elif intent['intent'] == 'device_listing':
				# Tüm verilerdeki benzersiz cihazları bul
				devices = set()
				for data_item in data:
					device_id = data_item.get('device_id', 'Bilinmeyen Cihaz')
					user_id = data_item.get('user_id', 'Bilinmeyen Kullanıcı')
					devices.add(f"{user_id}@{device_id}")
				
				if devices:
					device_list = ", ".join(sorted(devices))
					return f"Cihaz listesi ({len(devices)} adet): {device_list}"
				else:
					return "Cihaz bilgisi bulunamadı."
			
			elif intent['intent'] == 'time_analysis':
				# Zaman aralığındaki veri dağılımını analiz et
				if not data:
					return "Zaman analizi için veri bulunamadı."
				
				# Zaman aralığını parse et
				start_time = time_range['start_time']
				end_time = time_range['end_time']
				
				# Veri sayısını hesapla
				data_count = len(data)
				
				# İlk ve son kayıt zamanını bul
				timestamps = [item.get('collection_timestamp') for item in data if item.get('collection_timestamp')]
				if timestamps:
					timestamps.sort()
					first_time = timestamps[0][:16]  # YYYY-MM-DD HH:MM formatında
					last_time = timestamps[-1][:16]
					
					return f"Zaman analizi: {start_time[:10]} tarihinde {data_count} kayıt var. İlk kayıt: {first_time}, Son kayıt: {last_time}"
				else:
					return f"Zaman analizi: {start_time[:10]} tarihinde {data_count} kayıt var."
			
			elif intent['intent'] == 'data_coverage':
				# Veri kapsamını analiz et
				if not data:
					return "Veri kapsamı analizi için veri bulunamadı."
				
				# Veri türlerini say
				data_types = {}
				for item in data:
					if item.get('system_data'):
						data_types['system'] = data_types.get('system', 0) + 1
					if item.get('web_data'):
						data_types['web'] = data_types.get('web', 0) + 1
				
				coverage_info = []
				if data_types.get('system'):
					coverage_info.append(f"Sistem verisi: {data_types['system']} kayıt")
				if data_types.get('web'):
					coverage_info.append(f"Web verisi: {data_types['web']} kayıt")
				
				total_records = len(data)
				coverage_summary = f"Toplam {total_records} kayıt. " + " | ".join(coverage_info)
				
				return coverage_summary
			
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
			return f"Sorgu işlenirken hata oluştu: {str(e)}"
	
	def change_model(self, model_id):
		"""
		Aktif modeli değiştirir.
		
		Args:
			model_id (str): Yeni model ID'si
			
		Returns:
			bool: Başarılı ise True
		"""
		print(f"🔄 Model değiştiriliyor: {model_id}")
		
		model, tokenizer = self.model_manager.load_model(model_id, force_reload=True)
		
		if model and tokenizer:
			self.model = model
			self.tokenizer = tokenizer
			print(f"✅ Model başarıyla değiştirildi: {model_id}")
			return True
		else:
			print(f"❌ Model değiştirilemedi: {model_id}")
			return False
	
	def get_model_status(self):
		"""
		Mevcut model durumunu döner.
		
		Returns:
			dict: Model durum bilgileri
		"""
		current_model = self.model_manager.get_current_model_info()
		
		return {
			'current_model': current_model,
			'available_models': self.model_manager.get_available_models(),
			'model_settings': self.model_settings,
			'cuda_available': torch.cuda.is_available(),
			'torch_threads': torch.get_num_threads()
		}
	
	def update_model_settings(self, settings):
		"""
		Model üretim ayarlarını günceller.
		
		Args:
			settings (dict): Yeni ayarlar
		"""
		self.model_settings.update(settings)
		print(f"⚙️ Model ayarları güncellendi: {settings}")
	
	def generate_response_with_qwen(self, context, max_new_tokens=None):
		"""
		Aktif model ile yanıt üretir.
		
		Args:
			context (str): Bağlam + yapılandırılmış çıktı içeren metin
			max_new_tokens (int): Üretilecek yeni token sayısı
			
		Returns:
			str: Üretilen yanıt
		"""
		if not self.model or not self.tokenizer:
			return "Model yüklü değil."
		
		# Ayarları al
		max_new_tokens = max_new_tokens or self.model_settings.get('max_new_tokens', 256)
		temperature = self.model_settings.get('temperature', 0.7)
		top_p = self.model_settings.get('top_p', 0.9)
		repetition_penalty = self.model_settings.get('repetition_penalty', 1.1)
		no_repeat_ngram_size = self.model_settings.get('no_repeat_ngram_size', 2)
		max_time = self.model_settings.get('max_generation_time', 30.0)
		
		try:
			# Model bilgisini al
			current_model_info = self.model_manager.get_current_model_info()
			model_name = current_model_info['display_name'] if current_model_info else "Bilinmeyen Model"
			
			# System prompt
			system_prompt = f"""
Sen bir Türkçe konuşan akıllı asistanısın ({model_name}). 
Görevin: kullanıcının sorusunu anlamak, bağlamı dikkat et ve kısa, net, anlaşılır şekilde cevap vermek. 
Yanıtlarında:
- Gereksiz tekrar yapma.
- Türkçe dil bilgisine dikkat et.
- Eğer bağlam yeterli değilse, kullanıcıya açıklama sor.
- Yanıtlarda doğrudan, samimi ve profesyonel ol.
"""
			
			# Chat template varsa kullan
			if hasattr(self.tokenizer, "apply_chat_template") and callable(getattr(self.tokenizer, "apply_chat_template")):
				messages = [
					{"role": "system", "content": system_prompt},
					{"role": "user", "content": context},
				]
				prompt_ids = self.tokenizer.apply_chat_template(
					messages,
					add_generation_prompt=True,
					return_tensors="pt"
				)
				inputs = {"input_ids": prompt_ids}
			else:
				prompt = f"System: {system_prompt}\nUser: {context}\nAssistant:"
				inputs = self.tokenizer(prompt, return_tensors="pt")

			# Attention mask
			if "attention_mask" in inputs:
				attention_mask = inputs["attention_mask"]
			else:
				attention_mask = torch.ones_like(inputs["input_ids"])
			
			# Üretim
			with torch.no_grad():
				outputs = self.model.generate(
					**inputs,
					attention_mask=attention_mask,
					max_new_tokens=max_new_tokens,
					do_sample=True,
					temperature=temperature,
					top_p=top_p,
					eos_token_id=self.tokenizer.eos_token_id,
					pad_token_id=self.tokenizer.eos_token_id,
					repetition_penalty=repetition_penalty,
					no_repeat_ngram_size=no_repeat_ngram_size,
					use_cache=True,
					max_time=max_time
				)
			
			generated = outputs[0].to("cpu")
			start_idx = 0
			if isinstance(inputs, dict) and "input_ids" in inputs:
				start_idx = inputs["input_ids"].shape[1]
			text = self.tokenizer.decode(generated[start_idx:], skip_special_tokens=True)
			return text.strip()
			
		except Exception as e:
			print(f"❌ Yanıt üretme hatası: {e}")
			return "Yanıt üretemedim, teknik bir sorun oluştu."

	async def query(self, user_query):
		"""
		Kullanıcı sorgusunu işler ve yanıt döner.
		
		Args:
			user_query (str): Kullanıcı sorgusu
			
		Returns:
			str: Doğal dil yanıtı
		"""
		print(f"\n🔍 Sorgu işleniyor: '{user_query}'")
		
		try:
			# 1. Zaman bilgisini çıkar
			time_range = self.parse_time_query(user_query)
			print(f"⏰ Zaman aralığı: {time_range['start_time']} - {time_range['end_time']}")
			
			# Özel: 'kaç kayıt' gibi sayım soruları
			if re.search(r"(kaç|kac).*kayıt|kac.*record|how many", user_query.lower()):
				total = await self.count_records(time_range)
				return f"Seçilen zaman aralığında toplam {total} kayıt var."
			
			# 2. Sorgu amacını belirle
			intent = self.parse_query_intent(user_query)
			print(f"🎯 Tespit edilen amaç: {intent['intent']} (güven: {intent['confidence']})")
			
			# 3. Elasticsearch'te veri ara
			print("📊 Veriler sorgulanıyor...")
			data = await self.search_data(intent, time_range)
			print(f"📋 {len(data)} kayıt bulundu")
			
			# 4. Yanıtı formatla
			structured_response = self.format_response(intent, data, time_range)
			
			# 5. Yanıt üretimi
			deterministic_intents = {
				'vpn_status', 'speed_info', 'system_info', 'location_info',
				'device_listing', 'time_analysis', 'data_coverage'
			}
			if intent['intent'] in deterministic_intents:
				natural_response = structured_response
			else:
				# Daha iyi yönlendirme: intent ve zaman aralığını bağlama ekle
				context = (
					f"Soru: {user_query}\n"
					f"Amaç: {intent['intent']}\n"
					f"Zaman: {time_range['start_time']} - {time_range['end_time']}\n"
					f"Bulunan: {structured_response}\n"
					f"Kısa, net bir yanıt ver:"
				)
				natural_response = self.generate_response_with_qwen(context)
			
			print(f"✅ Sorgu işlendi!")
			return natural_response
			
		except Exception as e:
			print(f"❌ Sorgu işleme hatası: {e}")
			return f"Sorgu işlenirken hata oluştu: {str(e)}"
	
	async def process_query(self, user_query):
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
		
		# Özel: 'kaç kayıt' gibi sayım soruları
		if re.search(r"(kaç|kac).*kayıt|kac.*record|how many", user_query.lower()):
			total = await self.count_records(time_range)
			response_text = f"📊 Seçilen zaman aralığında toplam {total} kayıt var."
			return {
				"query": user_query,
				"intent": {"intent": "count_records", "confidence": 1.0},
				"time_range": time_range,
				"data_found": total,
				"structured_response": response_text,
				"natural_response": response_text,
				"timestamp": datetime.now().isoformat()
			}
		
		# 2. Sorgu amacını belirle
		intent = self.parse_query_intent(user_query)
		print(f"🎯 Tespit edilen amaç: {intent['intent']} (güven: {intent['confidence']})")
		
		# 3. Elasticsearch'te veri ara
		print("📊 Veriler sorgulanıyor...")
		data = await self.search_data(intent, time_range)
		print(f"📋 {len(data)} kayıt bulundu")
		
		# 4. Yanıtı formatla
		structured_response = self.format_response(intent, data, time_range)
		
		# 5. Yanıt üretimi
		# Yapısal cevap yeterliyse LLM'i kullanma (hız ve doğruluk için)
		deterministic_intents = {
			'vpn_status', 'speed_info', 'system_info', 'location_info',
			'device_listing', 'time_analysis', 'data_coverage'
		}
		if intent['intent'] in deterministic_intents:
			natural_response = structured_response
		else:
			# Daha iyi yönlendirme: intent ve zaman aralığını bağlama ekle
			context = (
				f"Soru: {user_query}\n"
				f"Amaç: {intent['intent']}\n"
				f"Zaman: {time_range['start_time']} - {time_range['end_time']}\n"
				f"Bulunan: {structured_response}\n"
				f"Kısa, net bir yanıt ver:"
			)
			natural_response = self.generate_response_with_qwen(context)
		
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
		print("🤖 Query System - Etkileşimli Mod")
		print("="*60)
		print("Sistem ve ağ verileriniz hakkında soru sorabilirsiniz!")
		print("Örnek sorular:")
		print("- 'Son 2 saatte VPN bağlı mıydı?'")
		print("- '14:30'da internet hızı nasıldı?'")
		print("- 'Bugün sistem performansı nasıl?'")
		print("- 'Dün akşam hangi ülkede görünüyordum?'")
		print("- 'Bugün hangi bilgisayarların verisi var?'")
		print("- 'Bu haftaki hangi saatlerde veri toplandı?'")
		print("- 'Son 1 günde kaç kayıt var?'")
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
				
				# Sorguyu işle (async)
				import asyncio
				result = asyncio.run(self.process_query(user_input))
				
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
			"Son 120 saatte VPN bağlı mıydı?",
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
