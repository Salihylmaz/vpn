#!/usr/bin/env python3
"""
Elasticsearch Debug Aracı
Mevcut indeksleri tarar, gerçek veri durumunu gösterir
"""

import sys
import os
from datetime import datetime
import json

# Mevcut dizini Python path'ine ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from elasticsearch_client_v8 import ElasticsearchClient

class ElasticsearchDebugger:
    """
    Elasticsearch'te veri durumunu analiz eden sınıf
    """
    
    def __init__(self, es_host='localhost', es_port=9200, es_username=None, es_password=None, use_ssl=False):
        self.es_client = ElasticsearchClient(
            host=es_host,
            port=es_port,
            username=es_username,
            password=es_password,
            use_ssl=use_ssl
        )
    
    def scan_all_indices(self):
        """
        Tüm indeksleri tarar ve detaylı bilgi verir
        """
        print("\n🔍 TÜM İNDEKSLER TARANYOR...")
        print("="*60)
        
        try:
            # Tüm indeksleri al
            all_indices = self.es_client.get_all_indices()
            
            if not all_indices:
                print("❌ Hiç indeks bulunamadı!")
                return
            
            print(f"📋 Toplam {len(all_indices)} indeks bulundu:")
            print("-" * 60)
            
            total_documents = 0
            monitoring_indices = []
            
            for index_name in sorted(all_indices):
                # Sistem indekslerini atla (. ile başlayanlar)
                if index_name.startswith('.'):
                    continue
                
                try:
                    # Belge sayısını al
                    doc_count = self.es_client.count_documents(index_name)
                    total_documents += doc_count
                    
                    # İndeks istatistiklerini al
                    stats = self.es_client.get_index_stats(index_name)
                    size_mb = 0
                    if stats and 'total' in stats and 'store' in stats['total']:
                        size_bytes = stats['total']['store']['size_in_bytes']
                        size_mb = round(size_bytes / (1024 * 1024), 2)
                    
                    # Monitoring ile ilgili indeksleri işaretle
                    is_monitoring = any(keyword in index_name.lower() for keyword in ['monitoring', 'system', 'web', 'combined'])
                    if is_monitoring:
                        monitoring_indices.append(index_name)
                    
                    status_icon = "📊" if is_monitoring else "📁"
                    print(f"{status_icon} {index_name}:")
                    print(f"   └─ Doküman: {doc_count:,}")
                    print(f"   └─ Boyut: {size_mb} MB")
                    
                    # Eğer dokümanlı varsa, son belgeyi göster
                    if doc_count > 0:
                        latest_doc = self.es_client.get_latest_document(index_name)
                        if latest_doc:
                            timestamp = latest_doc.get('timestamp', latest_doc.get('collection_timestamp', 'N/A'))
                            print(f"   └─ Son Belge: {timestamp}")
                    
                    print()
                    
                except Exception as e:
                    print(f"❌ {index_name}: Hata - {e}")
            
            # Özet
            print("="*60)
            print(f"📈 ÖZET:")
            print(f"   🗂️  Toplam İndeks: {len([i for i in all_indices if not i.startswith('.')])}")
            print(f"   📊 Monitoring İndeks: {len(monitoring_indices)}")
            print(f"   📄 Toplam Doküman: {total_documents:,}")
            
            if monitoring_indices:
                print(f"\n📊 MONİTORİNG İNDEKSLERİ:")
                for idx in monitoring_indices:
                    print(f"   - {idx}")
            
            return {
                'all_indices': all_indices,
                'monitoring_indices': monitoring_indices,
                'total_documents': total_documents
            }
            
        except Exception as e:
            print(f"❌ İndeks tarama hatası: {e}")
            return None
    
    def search_monitoring_data(self, limit=5):
        """
        Monitoring verilerini tüm indekslerde arar
        """
        print("\n🔍 MONİTORİNG VERİLERİ ARANYOR...")
        print("="*50)
        
        # Olası monitoring indeks isimleri
        possible_indices = [
            'system-monitoring', 'web-monitoring', 'combined-monitoring',
            'monitoring', 'system_monitoring', 'web_monitoring', 'combined_monitoring',
            'system-info', 'web-info', 'system_info', 'web_info'
        ]
        
        found_data = {}
        
        for index_name in possible_indices:
            try:
                if self.es_client.index_exists(index_name):
                    doc_count = self.es_client.count_documents(index_name)
                    if doc_count > 0:
                        print(f"✅ {index_name}: {doc_count} belge bulundu")
                        
                        # Son birkaç belgeyi al
                        recent_docs = self.es_client.search(index_name, size=limit)
                        if recent_docs:
                            found_data[index_name] = {
                                'count': doc_count,
                                'recent_docs': [doc['_source'] for doc in recent_docs]
                            }
                            
                            # İlk belgenin yapısını göster
                            first_doc = recent_docs[0]['_source']
                            print(f"   📋 Belge yapısı:")
                            self._print_document_structure(first_doc, indent=6)
                        print()
                    else:
                        print(f"⚠️ {index_name}: İndeks var ama boş")
                else:
                    print(f"❌ {index_name}: İndeks mevcut değil")
            except Exception as e:
                print(f"❌ {index_name}: Hata - {e}")
        
        return found_data
    
    def _print_document_structure(self, doc, indent=0, max_depth=2, current_depth=0):
        """
        Belge yapısını yazdırır
        """
        if current_depth >= max_depth:
            return
        
        spaces = " " * indent
        
        for key, value in doc.items():
            if isinstance(value, dict):
                print(f"{spaces}├─ {key}: (object)")
                self._print_document_structure(value, indent + 2, max_depth, current_depth + 1)
            elif isinstance(value, list):
                print(f"{spaces}├─ {key}: (array[{len(value)}])")
            else:
                # Değeri kısalt
                str_value = str(value)
                if len(str_value) > 50:
                    str_value = str_value[:47] + "..."
                print(f"{spaces}├─ {key}: {str_value}")
    
    def find_data_by_pattern(self, patterns=None):
        """
        Belirli kalıplara göre veri arar
        """
        if patterns is None:
            patterns = ['cpu', 'memory', 'ip_address', 'speed_test', 'vpn', 'system']
        
        print(f"\n🔍 VERİ KALIPLARI ARANYOR: {', '.join(patterns)}")
        print("="*60)
        
        all_indices = self.es_client.get_all_indices()
        found_patterns = {}
        
        for index_name in all_indices:
            if index_name.startswith('.'):
                continue
                
            try:
                doc_count = self.es_client.count_documents(index_name)
                if doc_count == 0:
                    continue
                
                # Birkaç belge al ve içeriğini kontrol et
                sample_docs = self.es_client.search(index_name, size=3)
                
                for pattern in patterns:
                    for doc_hit in sample_docs:
                        doc = doc_hit['_source']
                        if self._contains_pattern(doc, pattern):
                            if pattern not in found_patterns:
                                found_patterns[pattern] = []
                            
                            if index_name not in [item['index'] for item in found_patterns[pattern]]:
                                found_patterns[pattern].append({
                                    'index': index_name,
                                    'doc_count': doc_count,
                                    'sample_doc': doc
                                })
                            break
                            
            except Exception as e:
                print(f"❌ {index_name} kontrol edilemedi: {e}")
        
        # Sonuçları yazdır
        for pattern, results in found_patterns.items():
            print(f"\n🎯 '{pattern}' kalıbı bulundu:")
            for result in results:
                print(f"   📊 {result['index']}: {result['doc_count']} belge")
        
        return found_patterns
    
    def _contains_pattern(self, obj, pattern, max_depth=3, current_depth=0):
        """
        Obje içinde kalıp arar (recursive)
        """
        if current_depth >= max_depth:
            return False
        
        if isinstance(obj, dict):
            # Anahtar isimlerinde ara
            for key in obj.keys():
                if pattern.lower() in key.lower():
                    return True
            
            # Değerlerde ara
            for value in obj.values():
                if self._contains_pattern(value, pattern, max_depth, current_depth + 1):
                    return True
                    
        elif isinstance(obj, list):
            for item in obj:
                if self._contains_pattern(item, pattern, max_depth, current_depth + 1):
                    return True
                    
        elif isinstance(obj, str):
            if pattern.lower() in obj.lower():
                return True
        
        return False
    
    def cleanup_empty_indices(self):
        """
        Boş indeksleri temizleme (isteğe bağlı)
        """
        print("\n🧹 BOŞ İNDEKSLER ARANYOR...")
        print("="*40)
        
        all_indices = self.es_client.get_all_indices()
        empty_indices = []
        
        for index_name in all_indices:
            if index_name.startswith('.'):
                continue
                
            try:
                doc_count = self.es_client.count_documents(index_name)
                if doc_count == 0:
                    empty_indices.append(index_name)
                    print(f"📭 {index_name}: Boş indeks")
            except Exception as e:
                print(f"❌ {index_name}: Kontrol hatası - {e}")
        
        if empty_indices:
            print(f"\n⚠️ {len(empty_indices)} boş indeks bulundu:")
            for idx in empty_indices:
                print(f"   - {idx}")
            
            response = input("\nBoş indeksleri silmek ister misiniz? (y/n): ").strip().lower()
            if response == 'y':
                deleted_count = 0
                for idx in empty_indices:
                    if self.es_client.delete_index(idx):
                        deleted_count += 1
                print(f"✅ {deleted_count} boş indeks silindi.")
        else:
            print("✅ Boş indeks bulunamadı.")
    
    def full_analysis(self):
        """
        Tam analiz yapar
        """
        print("\n🔬 ELASTICSEARCH TAM ANALİZİ")
        print("="*60)
        
        # 1. Tüm indeksleri tara
        index_info = self.scan_all_indices()
        
        # 2. Monitoring verilerini ara
        monitoring_data = self.search_monitoring_data()
        
        # 3. Kalıp analizi
        pattern_data = self.find_data_by_pattern()
        
        # 4. Özet rapor
        print("\n📋 ANALİZ RAPORU")
        print("="*40)
        
        if index_info:
            print(f"🗂️  Toplam İndeks: {len(index_info['all_indices'])}")
            print(f"📊 Monitoring İndeks: {len(index_info['monitoring_indices'])}")
            print(f"📄 Toplam Doküman: {index_info['total_documents']:,}")
        
        if monitoring_data:
            print(f"✅ Veri bulunan indeksler: {len(monitoring_data)}")
            for idx, data in monitoring_data.items():
                print(f"   - {idx}: {data['count']} belge")
        
        if pattern_data:
            print(f"🎯 Bulunan veri kalıpları: {len(pattern_data)}")
            for pattern in pattern_data.keys():
                print(f"   - {pattern}")
        
        return {
            'indices': index_info,
            'monitoring': monitoring_data,
            'patterns': pattern_data
        }

def main():
    """
    Ana fonksiyon
    """
    print("🔍 Elasticsearch Debug Aracı")
    print("="*50)
    
    try:
        debugger = ElasticsearchDebugger()
        
        while True:
            print("\n🛠️  ELASTICSEARCH DEBUG MENÜSÜ")
            print("="*40)
            print("1. 🔍 Tüm indeksleri tara")
            print("2. 📊 Monitoring verilerini ara")
            print("3. 🎯 Veri kalıplarını ara")
            print("4. 🧹 Boş indeksleri temizle")
            print("5. 🔬 Tam analiz yap")
            print("6. 🚪 Çıkış")
            
            choice = input("\nSeçiminiz (1-6): ").strip()
            
            if choice == '1':
                debugger.scan_all_indices()
            elif choice == '2':
                debugger.search_monitoring_data()
            elif choice == '3':
                patterns = input("Aranacak kalıplar (virgülle ayırın, boş=varsayılan): ").strip()
                if patterns:
                    pattern_list = [p.strip() for p in patterns.split(',')]
                    debugger.find_data_by_pattern(pattern_list)
                else:
                    debugger.find_data_by_pattern()
            elif choice == '4':
                debugger.cleanup_empty_indices()
            elif choice == '5':
                debugger.full_analysis()
            elif choice == '6':
                print("👋 Görüşürüz!")
                break
            else:
                print("⚠️ Geçersiz seçim!")
                
    except Exception as e:
        print(f"❌ Debug aracı hatası: {e}")

if __name__ == "__main__":
    main()