from elasticsearch import Elasticsearch
from datetime import datetime
import time
import warnings
import json

# SSL sertifika uyarılarını devre dışı bırak.
# Geliştirme ortamları için kullanışlıdır ancak üretimde sertifikaları doğrulamak önemlidir.
warnings.filterwarnings('ignore', category=UserWarning, message='Unverified HTTPS request')

class ElasticsearchClient:
    """
    Elasticsearch 8.x istemcisi için basit bir sarmalayıcı sınıfı.
    """
    def __init__(self, host='localhost', port=9200, username=None, password=None, use_ssl=False, max_retries=3, retry_delay=2):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # URL oluştur
        scheme = 'https' if self.use_ssl else 'http'
        self.url = f"{scheme}://{self.host}:{self.port}"
        
        print(f"Elasticsearch bağlantısı deneniyor: {self.url}")
        
        # Bağlantı parametrelerini hazırla
        hosts = [self.url]
        http_auth = (username, password) if username and password else None
        
        try:
            # Client'ı en temel parametrelerle başlatıyoruz
            # Hata mesajındaki versiyon uyumsuzluğunu gidermek için headers parametresi eklendi.
            # `compatible-with=8` ile client'ın 8.x sunucusuyla uyumlu bir şekilde iletişim kurmasını sağlıyoruz.
            self.es = Elasticsearch(
                hosts=hosts,
                basic_auth=http_auth,
                headers={'accept': 'application/vnd.elasticsearch+json; compatible-with=8'}
            )
            
            # Bağlantıyı manuel olarak test et
            if not self._test_connection():
                raise ConnectionError("Elasticsearch bağlantısı başarısız oldu!")
            
            print("✅ Elasticsearch'e başarıyla bağlanıldı!")
            
        except ConnectionError as e:
            print(f"❌ Elasticsearch bağlantısı başarısız: {e}")
            self._print_troubleshooting_tips()
            raise
        except Exception as e:
            print(f"❌ Elasticsearch istemci oluşturulamadı: {e}")
            raise
    
    def _test_connection(self):
        """Elasticsearch bağlantısını ping ile test eder."""
        for attempt in range(self.max_retries):
            try:
                info = self.es.info()
                print(f"✅ Bağlantı başarılı: Cluster '{info['cluster_name']}' Version '{info['version']['number']}'")
                return True
            except Exception as e:
                print(f"❌ Bağlantı testi başarısız (deneme {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    print(f"{self.retry_delay} saniye bekleniyor...")
                    time.sleep(self.retry_delay)
        return False

    def _print_troubleshooting_tips(self):
        """Bağlantı sorunları için ipuçları yazdırır."""
        print("\n=== Elasticsearch 8.x İçin Öneriler ===")
        print("1. Bağlantı bilgilerini kontrol edin: host, port, kullanıcı adı ve şifre doğru mu?")
        print("2. Güvenlik ayarlarını kontrol edin: xpack.security.enabled ayarı 'false' olarak ayarlanmış mı?")
        print("3. **Çok Önemli:** `elasticsearch` kütüphanesini yeniden kurun. Terminalinize sırasıyla şu komutları yazın:")
        print("   `pip uninstall elasticsearch`")
        print("   `pip install elasticsearch`")
        print("4. Python ortamınızda SSL/TLS ile ilgili bir sorun olabilir.")

    def create_index(self, index_name, mapping=None):
        """Index oluşturur (Elasticsearch 8.x uyumlu)."""
        try:
            if not self.es.indices.exists(index=index_name):
                self.es.indices.create(index=index_name, body={"mappings": mapping} if mapping else None)
                print(f"Index '{index_name}' oluşturuldu.")
            else:
                print(f"Index '{index_name}' zaten mevcut.")
        except Exception as e:
            print(f"Index oluşturma hatası: {e}")
    
    def index_document(self, index_name, document, doc_id=None):
        """Belge index'ler (Elasticsearch 8.x uyumlu)."""
        try:
            document['timestamp'] = datetime.now().isoformat()
            response = self.es.index(
                index=index_name,
                document=document,
                id=doc_id
            )
            print(f"Belge index'lendi: {response['_id']}")
            return response
        except Exception as e:
            print(f"Index'leme hatası: {e}")
            return None
    
    def bulk_index(self, index_name, documents):
        """Toplu belge index'leme (Elasticsearch 8.x uyumlu)."""
        from elasticsearch.helpers import bulk
        
        actions = [
            {
                "_index": index_name,
                "_source": {**doc, "timestamp": datetime.now().isoformat()}
            }
            for doc in documents
        ]
        
        try:
            success, failed = bulk(self.es, actions)
            print(f"Toplu index'leme: {success} başarılı, {len(failed)} başarısız")
            return success, failed
        except Exception as e:
            print(f"Toplu index'leme hatası: {e}")
            return 0, []
    
    def search(self, index_name, query=None, size=10):
        """Index'te arama yapar (Elasticsearch 8.x uyumlu)."""
        try:
            search_body = {"query": query if query else {"match_all": {}}}
            # Uyarıyı gidermek için 'size' parametresi 'body' içine eklendi.
            search_body["size"] = size
            response = self.es.search(index=index_name, body=search_body)
            return response['hits']['hits']
        except Exception as e:
            print(f"Arama hatası: {e}")
            return []

# Test fonksiyonu
def test_elasticsearch_8x():
    """Düzeltilmiş Elasticsearch 8.x istemci testi"""
    print("=== Elasticsearch 8.x Test ===")
    
    try:
        # İstemciyi başlat
        # Güvensiz bağlantı için `use_ssl=False` kullanın
        client = ElasticsearchClient()
        
        test_doc = {
            "test_field": "test_value",
            "number_field": 42,
            "description": "Bu bir test belgesidir."
        }
        
        client.create_index("test-index")
        
        result = client.index_document("test-index", test_doc)
        
        if result:
            print("✅ Test belgesi başarıyla eklendi!")
            
            time.sleep(1)
            search_results = client.search("test-index")
            
            print(f"✅ Arama sonucu: {len(search_results)} belge bulundu")
            print("Bulunan belgeler:")
            for hit in search_results:
                print(f"  - ID: {hit['_id']}, Kaynak: {hit['_source']}")
        
        return True
    except Exception as e:
        print(f"❌ Test başarısız: {e}")
        return False

if __name__ == "__main__":
    if test_elasticsearch_8x():
        print("\n🎉 Tüm testler başarıyla tamamlandı!")
    else:
        print("\n😞 Testler başarısız oldu. Lütfen yukarıdaki hataları kontrol edin.")
