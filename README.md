# VPN Monitoring System

Modern bir web tabanlı sistem izleme uygulaması. React frontend ve FastAPI backend ile geliştirilmiştir.

## 🚀 Özellikler

- **Gerçek Zamanlı İzleme**: CPU, RAM, disk ve ağ performansını canlı olarak izler
- **VPN Durumu**: VPN bağlantı durumunu kontrol eder
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

```bash
# Ana dizinde
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

FastAPI otomatik dokümantasyonu şu adreslerde mevcuttur:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 📊 Kullanım

### Dashboard
- Sistem durumunu genel bakış
- Hızlı metrikler
- Son aktiviteler

### Sistem İzleme
- Gerçek zamanlı CPU, RAM, disk kullanımı
- Ağ performansı
- VPN durumu
- Canlı grafikler

### Sorgu Sistemi
- Doğal dil ile sorular sorun
- AI destekli yanıtlar
- Örnek sorular

### Veri Geçmişi
- Geçmiş performans verileri
- İnteraktif grafikler
- İstatistikler
- Veri dışa aktarma

## 🔧 Konfigürasyon

`config.py` dosyasında aşağıdaki ayarları yapabilirsiniz:

```python
ELASTICSEARCH_CONFIG = {
    'host': 'localhost',
    'port': 9200,
    'username': None,
    'password': None,
    'use_ssl': False
}
```

## 📁 Proje Yapısı

```
vpn/
├── api/
│   └── main.py              # FastAPI backend
├── frontend/
│   ├── src/
│   │   ├── components/      # React bileşenleri
│   │   ├── App.js          # Ana uygulama
│   │   └── index.js        # Giriş noktası
│   ├── package.json        # Frontend bağımlılıkları
│   └── tailwind.config.js  # Tailwind konfigürasyonu
├── data_collector.py       # Veri toplama
├── query_system.py         # AI sorgu sistemi
├── system_monitor.py       # Sistem izleme
├── config.py              # Konfigürasyon
└── requirements.txt       # Python bağımlılıkları
```

## 🎨 Özelleştirme

### Renk Teması
`frontend/tailwind.config.js` dosyasında renk paletini özelleştirebilirsiniz:

```javascript
colors: {
  primary: {
    500: '#3b82f6',
    // ...
  }
}
```

### API Endpoints
`api/main.py` dosyasında yeni endpoint'ler ekleyebilirsiniz.

## 🐛 Sorun Giderme

### Elasticsearch Bağlantı Hatası
```bash
# Elasticsearch durumunu kontrol et
curl http://localhost:9200

# Container'ı yeniden başlat
docker restart elasticsearch
```

### Frontend Build Hatası
```bash
# Node modules'u temizle ve yeniden yükle
rm -rf node_modules package-lock.json
npm install
```

### Backend Import Hatası
```bash
# Python path'ini kontrol et
export PYTHONPATH="${PYTHONPATH}:/path/to/vpn"
```

## 📈 Performans

- Backend: ~100ms API yanıt süresi
- Frontend: <2s sayfa yükleme süresi
- Veri toplama: 5 saniyede bir güncelleme
- Grafik güncelleme: Gerçek zamanlı

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

## 📞 Destek

Sorularınız için issue açabilir veya iletişime geçebilirsiniz.

---

**Not**: Bu uygulama geliştirme amaçlıdır. Production kullanımı için ek güvenlik önlemleri alınmalıdır.
