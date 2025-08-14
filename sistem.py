import psutil, platform, subprocess, requests, speedtest

class SystemInfo:
    def __init__(self):
        self.cpu_count = psutil.cpu_count(logical=True)
        self.memory = psutil.virtual_memory()
        self.disk_usage = psutil.disk_usage('/')
        self.platform = platform.system()
        self.ram = self.memory.total / (1024 ** 3)  # Convert bytes to GB
    
    def get_gpu_info(self):
        try:
            gpu_info = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,memory.used", "--format=csv,noheader"],
                encoding='utf-8'
            )
            return gpu_info.strip().split('\n')
        except FileNotFoundError:
            return "NVIDIA GPU bulunamadı veya 'nvidia-smi' mevcut değil."

    def get_system_info(self):
        return{
            "cpu_count": self.cpu_count,
            "gpu_info": self.get_gpu_info(),
            "memory_total": self.memory.total,
            "memory_available": self.memory.available,
            "disk_total": self.disk_usage.total,
            "disk_used": self.disk_usage.used,
            "platform": self.platform,
            "ram_gb": self.ram
        }
    
