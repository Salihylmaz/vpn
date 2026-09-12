#!/usr/bin/env python3
"""
Backend başlatma scripti
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def check_elasticsearch():
    """Elasticsearch bağlantısını kontrol et"""
    try:
        import requests
        response = requests.get('http://localhost:9200', timeout=5)
        if response.status_code == 200:
            print("✅ Elasticsearch bağlantısı başarılı")
            return True
        else:
            print("❌ Elasticsearch yanıt vermiyor")
            return False
    except Exception as e:
        print(f"❌ Elasticsearch bağlantı hatası: {e}")
        return False

def start_elasticsearch():
    """Elasticsearch'i Docker ile başlat"""
    print("🐳 Elasticsearch başlatılıyor...")
    try:
        # Elasticsearch container'ını başlat
        subprocess.run([
            'docker', 'run', '-d',
            '--name', 'elasticsearch',
            '-p', '9200:9200',
            '-p', '9300:9300',
            '-e', 'discovery.type=single-node',
            '-e', 'xpack.security.enabled=false',
            'docker.elastic.co/elasticsearch/elasticsearch:8.8.0'
        ], check=True)
        
        print("⏳ Elasticsearch başlatılıyor, lütfen bekleyin...")
        time.sleep(30)  # Elasticsearch'in başlaması için bekle
        
        if check_elasticsearch():
            print("✅ Elasticsearch başarıyla başlatıldı")
            return True
        else:
            print("❌ Elasticsearch başlatılamadı")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker hatası: {e}")
        return False
    except FileNotFoundError:
        print("❌ Docker bulunamadı. Lütfen Docker'ı yükleyin.")
        return False

def check_dependencies():
    """Gerekli bağımlılıkları kontrol et"""
    print("📦 Bağımlılıklar kontrol ediliyor...")
    
    try:
        import fastapi
        import uvicorn
        import elasticsearch
        import psutil
        print("✅ Tüm bağımlılıklar mevcut")
        return True
    except ImportError as e:
        print(f"❌ Eksik bağımlılık: {e}")
        print("💡 Lütfen 'pip install -r requirements.txt' komutunu çalıştırın")
        return False

def main():
    """Ana başlatma fonksiyonu"""
    print("🚀 VPN Monitoring System Backend Başlatılıyor...")
    print("=" * 50)
    
    # Bağımlılıkları kontrol et
    if not check_dependencies():
        sys.exit(1)
    
    # Elasticsearch'i kontrol et
    if not check_elasticsearch():
        print("\n🔧 Elasticsearch başlatılıyor...")
        if not start_elasticsearch():
            print("\n❌ Elasticsearch başlatılamadı. Manuel olarak başlatın:")
            print("docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 \\")
            print("  -e 'discovery.type=single-node' \\")
            print("  -e 'xpack.security.enabled=false' \\")
            print("  docker.elastic.co/elasticsearch/elasticsearch:8.8.0")
            sys.exit(1)
    
    print("\n🎯 Backend başlatılıyor...")
    
    # Backend dizinine git
    backend_dir = Path(__file__).parent / 'backend'
    if not backend_dir.exists():
        print(f"❌ Backend dizini bulunamadı: {backend_dir}")
        sys.exit(1)
    
    os.chdir(backend_dir)
    
    # Backend'i başlat
    try:
        subprocess.run([
            sys.executable, '-m', 'uvicorn', 
            'api:app', 
            '--host', '0.0.0.0', 
            '--port', '8000',
            '--reload'
        ])
    except KeyboardInterrupt:
        print("\n👋 Backend durduruldu")
    except Exception as e:
        print(f"❌ Backend başlatma hatası: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
