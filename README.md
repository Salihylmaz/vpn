# VPN Monitoring System

Modern bir web tabanlı sistem izleme uygulaması. React frontend ve FastAPI backend ile geliştirilmiştir.

## 🚀 Özellikler

- **Gerçek Zamanlı İzleme**: CPU, RAM, disk ve ağ performansını canlı olarak izler
- **VPN Durumu**: VPN bağlantı durumunu kontrol eder ve geçmiş kayıtları listeler
- **AI Sorgu Sistemi**: Doğal dil ile sistem verileriniz hakkında sorular sorun
- **Veri Geçmişi**: Geçmiş performans verilerini grafiklerle görüntüler
- **Modern UI**: Renkli ve kullanıcı dostu arayüz
- **Responsive Design**: Mobil ve masaüstü uyumlu

## 🛠️ Teknolojiler

### Backend
- **FastAPI**: Modern Python web framework
- **Elasticsearch**: Veri depolama ve arama
- **psutil**: Sistem izleme
- **Transformers**: AI model entegrasyonu

### Frontend
- **React**: Modern JavaScript framework
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Animasyonlar
- **Recharts**: Veri görselleştirme
- **Lucide React**: İkonlar

## 📋 Gereksinimler

- Python 3.8+
- Node.js 16+
- Elasticsearch 8.0+
- Modern web tarayıcısı

## 🚀 Kurulum

### 1. Backend Kurulumu

```bash
# Proje dizinine git
cd vpn

# Python sanal ortamı oluştur
python -m venv venv

# Sanal ortamı aktifleştir
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt
```

### 2. Elasticsearch Kurulumu

Elasticsearch'i Docker ile çalıştırmak için:

```bash
# Elasticsearch container'ını başlat
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  docker.elastic.co/elasticsearch/elasticsearch:8.8.0
```

### 3. Frontend Kurulumu

```bash
# Frontend dizinine git
cd frontend

# Bağımlılıkları yükle
npm install

# Geliştirme sunucusunu başlat
npm start
```

## 🏃‍♂️ Çalıştırma

### 1. Backend'i Başlat

Tercih edilen yol: kökten `start_app.bat` (Windows) veya doğrudan API:

```bash
# Ana dizinde
python start_backend.py  # Elasticsearch kontrol + API başlatma
# veya
cd api
python main.py
```

Backend `http://localhost:8000` adresinde çalışacak.

### 2. Frontend'i Başlat

```bash
# Frontend dizininde
cd frontend
npm start
```

Frontend `http://localhost:3000` adresinde çalışacak.

### 3. API Dokümantasyonu

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📊 Kullanım

### Dashboard
- Sistem genel durumu, hızlı metrikler
- Manuel veri toplama butonu

### Sistem İzleme
- Gerçek zamanlı CPU, RAM, disk, ağ
- Ağ durumu ve bağlantılar

### Sorgu Sistemi
- Doğal dil ile sorular
- Örnek: “Son 6 saatte VPN durumu?” veya “Son 2 saatte VPN kayıtlarını göster”
- Çoklu VPN kaydı listeleri desteklenir

### Veri Geçmişi
- Zaman aralıklarına göre filtreleme
- CSV olarak dışa aktarma

## 🔧 Konfigürasyon

Konfigürasyon dosyaları artık `backend/` paketinde tutulmaktadır:

```python
# backend/config.py
ELASTICSEARCH_CONFIG = {
    'host': 'localhost',
    'port': 9200,
    'username': None,
    'password': None,
    'use_ssl': False,
    'verify_certs': False,
}

USER_CONFIG = {
    'user_id': 'default_user',
    'device_id': None,
}
```

## 📁 Proje Yapısı

```
vpn/
├── api/
│   └── main.py                # FastAPI uygulaması
├── backend/                   # Backend paket (yeni)
│   ├── __init__.py
│   ├── config.py              # Konfigürasyon
│   ├── data_collector.py      # Veri toplama ve ES kayıt
│   ├── elasticsearch_client_v8.py # ES 8.x async istemcisi (sarmalayıcı)
│   ├── query_system.py        # AI sorgu sistemi (Qwen)
│   ├── system_monitor.py      # Sistem bilgisi toplayıcı
│   └── web.py                 # IP, VPN, hız testi (fallback destekli)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
├── start_backend.py           # Elasticsearch kontrol + API başlatma
├── start_app.bat              # Windows toplu başlatıcı (Backend+Frontend)
├── requirements.txt
└── README.md
```

## 🐛 Sorun Giderme

### Elasticsearch Bağlantı Hatası
```bash
curl http://localhost:9200
# Container'ı yeniden başlat
docker restart elasticsearch
```

### Frontend Build Hatası
```bash
rm -rf node_modules package-lock.json
npm install
```

### Backend Import Hatası
`backend/` paketini içeren proje kökü `PYTHONPATH` içinde olmalıdır (API `main.py` bunu otomatik ekler).

## 📈 Performans

- API yanıtları düşük gecikme için optimize edildi (CPU örnekleme 0.1s)
- Sürekli izleme aralığı ortam değişkeni ile ayarlanabilir: `COLLECTION_INTERVAL_SECONDS`

## 🔒 Güvenlik

- CORS koruması
- Input validasyonu
- Rate limiting (gelecek sürümde)
- HTTPS desteği (production)

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.
