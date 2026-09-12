import psutil
import platform
import subprocess
from datetime import datetime
import json
import os
import time

class SystemMonitor:
	"""
	Sistem kaynaklarını izleyen ve bilgi toplayan sınıf.
	CPU, bellek, disk, ağ ve işletim sistemi bilgilerini toplar.
	Docker container'da çalışırken host sistem bilgilerini almaya çalışır.
	"""
	
	def __init__(self):
		self.system_info = None
		self.last_network_stats = None
		self.use_host_proc = os.path.exists('/host/proc')
		if self.use_host_proc:
			print("🔍 DEBUG: Host /proc dizini bulundu, gerçek sistem verileri kullanılacak")
		else:
			print("🔍 DEBUG: Container içi sistem verileri kullanılacak")
		
	def _get_host_cpu_percent(self):
		"""Host sistem CPU yüzdesini /host/proc/stat'tan okur"""
		try:
			# İlk okuma
			with open('/host/proc/stat', 'r') as f:
				line1 = f.readline()
			cpu_times1 = [int(x) for x in line1.split()[1:8]]  # user, nice, system, idle, iowait, irq, softirq
			
			# 1 saniye bekle
			time.sleep(1)
			
			# İkinci okuma
			with open('/host/proc/stat', 'r') as f:
				line2 = f.readline()
			cpu_times2 = [int(x) for x in line2.split()[1:8]]
			
			# Farkları hesapla
			diffs = [cpu_times2[i] - cpu_times1[i] for i in range(len(cpu_times1))]
			
			total_diff = sum(diffs)
			idle_diff = diffs[3]  # idle time
			
			if total_diff == 0:
				return 0.0
				
			cpu_percent = 100.0 * (1.0 - idle_diff / total_diff)
			print(f"🔍 DEBUG: Host CPU hesaplama - Total: {total_diff}, Idle: {idle_diff}, CPU: {cpu_percent:.2f}%")
			return round(cpu_percent, 2)
		except Exception as e:
			print(f"❌ Host CPU okuma hatası: {e}")
			return None
	
	def _get_host_memory_info(self):
		"""Host sistem bellek bilgilerini /host/proc/meminfo'dan okur"""
		try:
			meminfo = {}
			with open('/host/proc/meminfo', 'r') as f:
				for line in f:
					parts = line.split()
					if len(parts) >= 2:
						key = parts[0].rstrip(':')
						value = int(parts[1]) * 1024  # kB to bytes
						meminfo[key] = value
			
			total = meminfo.get('MemTotal', 0)
			free = meminfo.get('MemFree', 0)
			available = meminfo.get('MemAvailable', free)
			buffers = meminfo.get('Buffers', 0)
			cached = meminfo.get('Cached', 0)
			used = total - available
			
			print(f"🔍 DEBUG: Host bellek RAW - MemTotal: {meminfo.get('MemTotal', 0) // (1024*1024)} MB")
			print(f"🔍 DEBUG: Host bellek - Total: {total / (1024**3):.1f} GB, Used: {used / (1024**3):.1f} GB, Available: {available / (1024**3):.1f} GB")
			print(f"🔍 DEBUG: Bellek detay - Free: {free / (1024**3):.1f} GB, Buffers: {buffers / (1024**3):.1f} GB, Cached: {cached / (1024**3):.1f} GB")
			
			return {
				"virtual_memory": {
					"total": total,
					"available": available,
					"percent": round((used / total) * 100, 2) if total > 0 else 0,
					"used": used,
					"free": free,
					"buffers": buffers,
					"cached": cached
				}
			}
		except Exception as e:
			print(f"❌ Host bellek okuma hatası: {e}")
			return None
	
	def get_cpu_info(self):
		"""
		CPU bilgilerini toplar.
		
		Returns:
			dict: CPU bilgileri
		"""
		try:
			if self.use_host_proc:
				cpu_percent = self._get_host_cpu_percent()
			else:
				# İlk çağrıda baseline oluştur, sonra daha uzun interval kullan
				cpu_percent = psutil.cpu_percent(interval=1.0)  # 1 saniye interval ile daha stabil ölçüm
			
			cpu_info = {
				"cpu_percent": round(cpu_percent, 2) if cpu_percent is not None else None,
				"cpu_count_logical": psutil.cpu_count(logical=True),
				"cpu_count_physical": psutil.cpu_count(logical=False),
				"cpu_freq": None,
				"cpu_times": None,
				"cpu_stats": None,
				"load_average": None
			}
			
			# CPU frekans bilgisi
			try:
				freq = psutil.cpu_freq()
				if freq:
					cpu_info["cpu_freq"] = {
						"current": round(freq.current, 2),
						"min": round(freq.min, 2) if freq.min else None,
						"max": round(freq.max, 2) if freq.max else None
					}
			except Exception:
				pass
			
			# CPU times
			try:
				times = psutil.cpu_times()
				cpu_info["cpu_times"] = {
					"user": times.user,
					"system": times.system,
					"idle": times.idle
				}
			except Exception:
				pass
			
			# CPU stats
			try:
				stats = psutil.cpu_stats()
				cpu_info["cpu_stats"] = {
					"ctx_switches": stats.ctx_switches,
					"interrupts": stats.interrupts,
					"soft_interrupts": stats.soft_interrupts,
					"syscalls": getattr(stats, 'syscalls', None)
				}
			except Exception:
				pass
			
			# Load average (Linux/Unix)
			try:
				if hasattr(psutil, 'getloadavg'):
					load_avg = psutil.getloadavg()
					cpu_info["load_average"] = {
						"1min": round(load_avg[0], 2),
						"5min": round(load_avg[1], 2),
						"15min": round(load_avg[2], 2)
					}
			except Exception:
				pass
			
			return cpu_info
			
		except Exception as e:
			print(f"❌ CPU bilgisi alınamadı: {e}")
			return None
	
	def get_memory_info(self):
		"""
		Bellek bilgilerini toplar.
		
		Returns:
			dict: Bellek bilgileri
		"""
		try:
			if self.use_host_proc:
				memory_info = self._get_host_memory_info()
			else:
				# Virtual memory
				vmem = psutil.virtual_memory()
				memory_info = {
					"virtual_memory": {
						"total": vmem.total,
						"available": vmem.available,
						"percent": round(vmem.percent, 2),
						"used": vmem.used,
						"free": vmem.free,
						"active": getattr(vmem, 'active', None),
						"inactive": getattr(vmem, 'inactive', None),
						"buffers": getattr(vmem, 'buffers', None),
						"cached": getattr(vmem, 'cached', None),
						"shared": getattr(vmem, 'shared', None)
					}
				}
			
			# Swap memory
			try:
				swap = psutil.swap_memory()
				memory_info["swap_memory"] = {
					"total": swap.total,
					"used": swap.used,
					"free": swap.free,
					"percent": round(swap.percent, 2),
					"sin": swap.sin,
					"sout": swap.sout
				}
			except Exception:
				memory_info["swap_memory"] = None
			
			return memory_info
			
		except Exception as e:
			print(f"❌ Bellek bilgisi alınamadı: {e}")
			return None
	
	def get_disk_info(self):
		"""
		Disk bilgilerini toplar.
		
		Returns:
			dict: Disk bilgileri
		"""
		try:
			disk_info = {
				"disk_partitions": [],
				"disk_usage": {},
				"disk_io": None
			}
			
			# Disk bölümleri
			partitions = psutil.disk_partitions()
			for partition in partitions:
				try:
					partition_usage = psutil.disk_usage(partition.mountpoint)
					partition_info = {
						"device": partition.device,
						"mountpoint": partition.mountpoint,
						"fstype": partition.fstype,
						"opts": partition.opts,
						"total": partition_usage.total,
						"used": partition_usage.used,
						"free": partition_usage.free,
						"percent": round((partition_usage.used / partition_usage.total) * 100, 2) if partition_usage.total > 0 else 0
					}
					disk_info["disk_partitions"].append(partition_info)
				except PermissionError:
					# Bazı sistem bölümlerine erişim olmayabilir
					continue
				except Exception as e:
					print(f"⚠️ Bölüm bilgisi alınamadı ({partition.device}): {e}")
					continue
			
			# Ana disk kullanımı (/)
			try:
				main_disk = psutil.disk_usage('/')
				disk_info["disk_usage"]["main"] = {
					"total": main_disk.total,
					"used": main_disk.used,
					"free": main_disk.free,
					"percent": round((main_disk.used / main_disk.total) * 100, 2)
				}
			except Exception:
				pass
			
			# Disk I/O istatistikleri
			try:
				disk_io = psutil.disk_io_counters()
				if disk_io:
					disk_info["disk_io"] = {
						"read_count": disk_io.read_count,
						"write_count": disk_io.write_count,
						"read_bytes": disk_io.read_bytes,
						"write_bytes": disk_io.write_bytes,
						"read_time": disk_io.read_time,
						"write_time": disk_io.write_time
					}
			except Exception:
				pass
			
			return disk_info
			
		except Exception as e:
			print(f"❌ Disk bilgisi alınamadı: {e}")
			return None
	
	def get_network_info(self):
		"""
		Ağ bilgilerini toplar.
		
		Returns:
			dict: Ağ bilgileri
		"""
		try:
			network_info = {
				"network_io": None,
				"network_connections": None,
				"network_interfaces": {},
				"network_stats": None
			}
			
			# Host ağ bilgilerini kullan
			if self.use_host_proc:
				print("🔍 DEBUG: Host ağ bilgileri okunuyor...")
				# Host ağ arayüzlerini /host/proc/net/dev'den oku
				try:
					with open('/host/proc/net/dev', 'r') as f:
						lines = f.readlines()
					
					# İlk iki satırı atla (başlık)
					for line in lines[2:]:
						parts = line.split(':')
						if len(parts) == 2:
							interface = parts[0].strip()
							stats = parts[1].split()
							if len(stats) >= 16:
								network_info["network_interfaces"][interface] = {
									"bytes_recv": int(stats[0]),
									"packets_recv": int(stats[1]),
									"bytes_sent": int(stats[8]),
									"packets_sent": int(stats[9])
								}
				except Exception as e:
					print(f"⚠️ Host ağ bilgisi okuma hatası: {e}")
			
			# Fallback: psutil kullan
			if not network_info["network_interfaces"]:
				# Ağ I/O istatistikleri
				try:
					net_io = psutil.net_io_counters()
					if net_io:
						network_info["network_io"] = {
							"bytes_sent": net_io.bytes_sent,
							"bytes_recv": net_io.bytes_recv,
							"packets_sent": net_io.packets_sent,
							"packets_recv": net_io.packets_recv,
							"errin": net_io.errin,
							"errout": net_io.errout,
							"dropin": net_io.dropin,
							"dropout": net_io.dropout
						}
				except Exception:
					pass
				
				# Ağ arayüzleri
				try:
					interfaces = psutil.net_if_addrs()
					for interface_name, addresses in interfaces.items():
						interface_info = {
							"addresses": [],
							"stats": None
						}
						
						for addr in addresses:
							addr_info = {
								"family": str(addr.family),
								"address": addr.address,
								"netmask": addr.netmask,
								"broadcast": addr.broadcast,
								"ptp": addr.ptp
							}
							interface_info["addresses"].append(addr_info)
						
						# Arayüz istatistikleri
						try:
							if_stats = psutil.net_if_stats()
							if interface_name in if_stats:
								stats = if_stats[interface_name]
								interface_info["stats"] = {
									"isup": stats.isup,
									"duplex": stats.duplex,
									"speed": stats.speed,
									"mtu": stats.mtu
								}
						except Exception:
							pass
						
						network_info["network_interfaces"][interface_name] = interface_info
				except Exception:
					pass
			
			# Ağ bağlantıları (sadece aktif olanlar)
			try:
				connections = psutil.net_connections(kind='inet')
				connection_summary = {
					"total_connections": len(connections),
					"established": len([c for c in connections if c.status == 'ESTABLISHED']),
					"listening": len([c for c in connections if c.status == 'LISTEN']),
					"time_wait": len([c for c in connections if c.status == 'TIME_WAIT'])
				}
				network_info["network_connections"] = connection_summary
			except (psutil.AccessDenied, PermissionError):
				# Bazı sistemlerde bağlantı bilgilerine erişim olmayabilir
				pass
			except Exception:
				pass
			
			return network_info
			
		except Exception as e:
			print(f"❌ Ağ bilgisi alınamadı: {e}")
			return None
	
	def get_system_info(self):
		"""
		İşletim sistemi bilgilerini toplar.
		
		Returns:
			dict: Sistem bilgileri
		"""
		try:
			system_info = {
				"platform": {
					"system": platform.system(),
					"node": platform.node(),
					"release": platform.release(),
					"version": platform.version(),
					"machine": platform.machine(),
					"processor": platform.processor(),
					"platform": platform.platform(),
					"architecture": platform.architecture()
				},
				"boot_time": None,
				"uptime": None,
				"users": []
			}
			
			# Boot time ve uptime
			try:
				boot_time = psutil.boot_time()
				system_info["boot_time"] = datetime.fromtimestamp(boot_time).isoformat()
				uptime_seconds = datetime.now().timestamp() - boot_time
				system_info["uptime"] = {
					"total_seconds": int(uptime_seconds),
					"days": int(uptime_seconds // 86400),
					"hours": int((uptime_seconds % 86400) // 3600),
					"minutes": int((uptime_seconds % 3600) // 60)
				}
			except Exception:
				pass
			
			# Kullanıcılar
			try:
				users = psutil.users()
				for user in users:
					user_info = {
						"name": user.name,
						"terminal": user.terminal,
						"host": user.host,
						"started": datetime.fromtimestamp(user.started).isoformat() if user.started else None,
						"pid": getattr(user, 'pid', None)
					}
					system_info["users"].append(user_info)
			except Exception:
				pass
			
			return system_info
			
		except Exception as e:
			print(f"❌ Sistem bilgisi alınamadı: {e}")
			return None
	
	def get_process_info(self, top_n=10):
		"""
		En çok kaynak kullanan işlemleri toplar.
		
		Args:
			top_n (int): Kaç işlem gösterilsin
			
		Returns:
			dict: İşlem bilgileri
		"""
		try:
			processes = []
			
			for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status', 'create_time', 'username']):
				try:
					processes.append(proc.info)
				except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
					pass
			
			# CPU kullanımına göre sırala
			cpu_top = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:top_n]
			
			# Bellek kullanımına göre sırala
			memory_top = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:top_n]
			
			process_info = {
				"total_processes": len(processes),
				"top_cpu_processes": cpu_top,
				"top_memory_processes": memory_top,
				"process_count_by_status": {}
			}
			
			# Durum bazında işlem sayısı
			status_count = {}
			for proc in processes:
				status = proc.get('status', 'unknown')
				status_count[status] = status_count.get(status, 0) + 1
			
			process_info["process_count_by_status"] = status_count
			
			return process_info
			
		except Exception as e:
			print(f"❌ İşlem bilgisi alınamadı: {e}")
			return None
	
	def get_temperature_info(self):
		"""
		Sistem sıcaklık bilgilerini toplar (varsa).
		
		Returns:
			dict: Sıcaklık bilgileri veya None
		"""
		try:
			if hasattr(psutil, 'sensors_temperatures'):
				temps = psutil.sensors_temperatures()
				if temps:
					temperature_info = {}
					for name, entries in temps.items():
						sensor_data = []
						for entry in entries:
							sensor_data.append({
								"label": entry.label or 'N/A',
								"current": entry.current,
								"high": entry.high,
								"critical": entry.critical
							})
						temperature_info[name] = sensor_data
					return temperature_info
			return None
		except Exception:
			return None
	
	def get_battery_info(self):
		"""
		Batarya bilgilerini toplar (varsa).
		
		Returns:
			dict: Batarya bilgileri veya None
		"""
		try:
			if hasattr(psutil, 'sensors_battery'):
				battery = psutil.sensors_battery()
				if battery:
					return {
						"percent": round(battery.percent, 2),
						"power_plugged": battery.power_plugged,
						"secsleft": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else "unlimited"
					}
			return None
		except Exception:
			return None
	
	def get_complete_system_info(self, include_processes=True, top_processes=10):
		"""
		Tüm sistem bilgilerini toplar.
		
		Args:
			include_processes (bool): İşlem bilgileri dahil edilsin mi
			top_processes (int): Kaç işlem gösterilsin
			
		Returns:
			dict: Tüm sistem bilgileri
		"""
		print("💻 Sistem bilgileri toplanıyor...")
		
		cpu_info = self.get_cpu_info()
		memory_info = self.get_memory_info()
		
		print(f"🔍 DEBUG: CPU kullanımı: {cpu_info['cpu_percent'] if cpu_info else 'N/A'}%")
		print(f"🔍 DEBUG: Bellek kullanımı: {memory_info['virtual_memory']['percent'] if memory_info else 'N/A'}%")
		print(f"🔍 DEBUG: Toplam bellek: {memory_info['virtual_memory']['total'] / (1024**3):.1f} GB" if memory_info else "🔍 DEBUG: Bellek bilgisi alınamadı")
		
		system_data = {
			"collection_timestamp": datetime.now().isoformat(),
			"cpu": cpu_info,
			"memory": memory_info,
			"disk": self.get_disk_info(),
			"network": self.get_network_info(),
			"system": self.get_system_info(),
			"processes": None,
			"temperature": self.get_temperature_info(),
			"battery": self.get_battery_info()
		}
		
		if include_processes:
			system_data["processes"] = self.get_process_info(top_processes)
		
		return system_data
	
	def get_summary(self):
		"""
		Sistem bilgilerinin özetini döndürür.
		
		Returns:
			dict: Özet bilgiler
		"""
		cpu_info = self.get_cpu_info()
		memory_info = self.get_memory_info()
		disk_info = self.get_disk_info()
		system_info = self.get_system_info()
		
		summary = {
			"hostname": system_info["platform"]["node"] if system_info else "N/A",
			"os": f"{system_info['platform']['system']} {system_info['platform']['release']}" if system_info else "N/A",
			"cpu_usage": f"{cpu_info['cpu_percent']}%" if cpu_info else "N/A",
			"memory_usage": f"{memory_info['virtual_memory']['percent']}%" if memory_info else "N/A",
			"disk_usage": f"{disk_info['disk_usage']['main']['percent']}%" if disk_info and disk_info.get('disk_usage', {}).get('main') else "N/A",
			"uptime": f"{system_info['uptime']['days']}d {system_info['uptime']['hours']}h {system_info['uptime']['minutes']}m" if system_info and system_info.get('uptime') else "N/A"
		}
		
		return summary
	
	def print_summary(self):
		"""Sistem özetini konsola yazdırır."""
		summary = self.get_summary()
		
		print("\n" + "="*50)
		print("📊 SİSTEM ÖZETİ")
		print("="*50)
		print(f"🖥️  Hostname: {summary['hostname']}")
		print(f"🔧 İşletim Sistemi: {summary['os']}")
		print(f"⚡ CPU Kullanımı: {summary['cpu_usage']}")
		print(f"🧠 Bellek Kullanımı: {summary['memory_usage']}")
		print(f"💾 Disk Kullanımı: {summary['disk_usage']}")
		print(f"⏰ Uptime: {summary['uptime']}")
		print("="*50)
