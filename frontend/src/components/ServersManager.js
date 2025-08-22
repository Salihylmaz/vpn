import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Server, 
  Plus, 
  Trash2, 
  Monitor, 
  Activity,
  Database,
  Wifi,
  HardDrive,
  Cpu,
  CheckCircle,
  XCircle,
  Eye,
  Play,
  Pause
} from 'lucide-react';
import { apiPost, apiGet, apiDelete } from '../lib/apiClient';

const ServersManager = () => {
  const [servers, setServers] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newServer, setNewServer] = useState({ name: '', ip: '', description: '' });
  const [serverData, setServerData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadServers();
  }, []);

  useEffect(() => {
    // İlk yükleme için localhost sunucuyu seç
    if (servers.length > 0 && !selectedServer) {
      const localhost = servers.find(s => s.ip === '127.0.0.1') || servers[0];
      setSelectedServer(localhost);
    }
  }, [servers, selectedServer]);

  useEffect(() => {
    if (selectedServer) {
      fetchServerData();
    }
  }, [selectedServer]);

  const loadServers = async () => {
    try {
      const response = await apiGet('/api/servers');
      setServers(response.servers || []);
    } catch (error) {
      console.error('Sunucular yüklenemedi:', error);
    }
  };

  const fetchServerData = async () => {
    if (!selectedServer) return;
    
    try {
      setLoading(true);
      
      if (selectedServer.ip === '127.0.0.1' || selectedServer.ip === 'localhost') {
        // Yerel bilgisayar için mevcut API'leri kullan
        const [systemInfo, latestData] = await Promise.all([
          apiGet('/api/system-info'),
          apiGet('/api/latest-data')
        ]);
        
        setServerData({
          system: systemInfo,
          latest: latestData?.data?.[0] || null
        });
      } else {
        // Diğer sunucular için server-specific data
        try {
          const serverSpecificData = await apiGet(`/api/servers/${selectedServer.id}/data`);
          setServerData({
            system: serverSpecificData.data?.[0]?.system_data || null,
            latest: serverSpecificData.data?.[0] || null
          });
        } catch (error) {
          console.log('Server-specific data not available yet');
          setServerData(null);
        }
      }
    } catch (error) {
      console.error('Sunucu verisi alınamadı:', error);
    } finally {
      setLoading(false);
    }
  };

  const addServer = async () => {
    if (!newServer.name || !newServer.ip) return;
    
    try {
      const response = await apiPost('/api/servers', {
        name: newServer.name,
        ip: newServer.ip,
        description: newServer.description
      });
      
      if (response.server) {
        await loadServers(); // Reload servers from Elasticsearch
        setNewServer({ name: '', ip: '', description: '' });
        setShowAddForm(false);
      }
    } catch (error) {
      console.error('Sunucu eklenemedi:', error);
      alert('Sunucu eklenirken hata oluştu: ' + error.message);
    }
  };

  const deleteServer = async (serverId) => {
    if (servers.length <= 1) return; // En az bir sunucu kalsın
    
    try {
      await apiDelete(`/api/servers/${serverId}`);
      await loadServers(); // Reload servers from Elasticsearch
      
      if (selectedServer?.id === serverId) {
        const remainingServers = servers.filter(s => s.id !== serverId);
        setSelectedServer(remainingServers[0] || null);
      }
    } catch (error) {
      console.error('Sunucu silinemedi:', error);
      alert('Sunucu silinirken hata oluştu: ' + error.message);
    }
  };

  const toggleMonitoring = async (serverId) => {
    const server = servers.find(s => s.id === serverId);
    if (!server) return;

    try {
      if (server.ip === '127.0.0.1' || server.ip === 'localhost') {
        // Localhost için genel monitoring
        if (server.monitoring) {
          await apiPost('/api/stop-monitoring', {});
        } else {
          await apiPost('/api/start-monitoring', {});
        }
      } else {
        // Diğer sunucular için server-specific data collection
        await apiPost(`/api/servers/${serverId}/collect`, {});
      }
      
      // Update local state
      setServers(prev => prev.map(s => 
        s.id === serverId ? { ...s, monitoring: !s.monitoring } : s
      ));
    } catch (error) {
      console.error('İzleme durumu değiştirilemedi:', error);
      alert('İzleme durumu değiştirilemedi: ' + error.message);
    }
  };

  const collectServerData = async (serverId) => {
    try {
      const response = await apiPost(`/api/servers/${serverId}/collect`, {});
      alert(response.message || 'Veri toplama başlatıldı');
      
      // Refresh server data after a short delay
      setTimeout(() => {
        fetchServerData();
      }, 2000);
    } catch (error) {
      console.error('Veri toplama başlatılamadı:', error);
      alert('Veri toplama başlatılamadı: ' + error.message);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'active': return 'text-green-400';
      case 'inactive': return 'text-red-400';
      case 'unknown': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active': return <CheckCircle className="w-4 h-4" />;
      case 'inactive': return <XCircle className="w-4 h-4" />;
      default: return <Monitor className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Sunucu Yönetimi</h1>
          <p className="text-white/60">Bilgisayar ve sunucuları ekleyip izleyin</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setShowAddForm(true)}
          className="btn-primary flex items-center space-x-2"
        >
          <Plus className="w-5 h-5" />
          <span>Sunucu Ekle</span>
        </motion.button>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Servers List */}
        <div className="lg:col-span-1">
          <div className="card p-4">
            <h3 className="text-white font-semibold mb-4 flex items-center">
              <Server className="w-5 h-5 mr-2" />
              Sunucular ({servers.length})
            </h3>
            
            <div className="space-y-2">
              {servers.map((server) => (
                <motion.div
                  key={server.id}
                  whileHover={{ scale: 1.02 }}
                  onClick={() => setSelectedServer(server)}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    selectedServer?.id === server.id 
                      ? 'bg-blue-500/20 border border-blue-500/50' 
                      : 'bg-white/5 hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className={`${getStatusColor(server.status)}`}>
                        {getStatusIcon(server.status)}
                      </div>
                      <div>
                        <p className="text-white font-medium">{server.name}</p>
                        <p className="text-white/60 text-sm">{server.ip}</p>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (server.ip === '127.0.0.1' || server.ip === 'localhost') {
                            toggleMonitoring(server.id);
                          } else {
                            collectServerData(server.id);
                          }
                        }}
                        className={`p-1 rounded ${
                          server.monitoring ? 'text-green-400' : 'text-white/60'
                        }`}
                      >
                        {(server.ip === '127.0.0.1' || server.ip === 'localhost') ? 
                          (server.monitoring ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />) :
                          <Database className="w-4 h-4" />
                        }
                      </motion.button>
                      
                      {server.id !== 'localhost' && (
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteServer(server.id);
                          }}
                          className="p-1 rounded text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="w-4 h-4" />
                        </motion.button>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>

        {/* Server Details & Data */}
        <div className="lg:col-span-2">
          {selectedServer ? (
            <div className="space-y-4">
              {/* Server Info */}
              <div className="card p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-white font-semibold flex items-center">
                    <Monitor className="w-5 h-5 mr-2" />
                    {selectedServer.name}
                  </h3>
                  <div className={`flex items-center space-x-2 px-3 py-1 rounded-lg ${
                    selectedServer.monitoring ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                  }`}>
                    <Activity className="w-4 h-4" />
                    <span className="text-sm">
                      {selectedServer.monitoring ? 'İzleniyor' : 'Pasif'}
                    </span>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-white/60">IP Adresi</p>
                    <p className="text-white">{selectedServer.ip}</p>
                  </div>
                  <div>
                    <p className="text-white/60">Durum</p>
                    <p className={`${getStatusColor(selectedServer.status)}`}>
                      {selectedServer.status === 'active' ? 'Aktif' : 
                       selectedServer.status === 'inactive' ? 'Pasif' : 'Bilinmiyor'}
                    </p>
                  </div>
                  {selectedServer.description && (
                    <div className="col-span-2">
                      <p className="text-white/60">Açıklama</p>
                      <p className="text-white">{selectedServer.description}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* System Metrics */}
              {serverData && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {/* CPU */}
                  <div className="card p-4">
                    <div className="flex items-center justify-between mb-2">
                      <Cpu className="w-5 h-5 text-blue-400" />
                      <span className="text-2xl font-bold text-white">
                        {serverData.system?.cpu?.cpu_percent?.toFixed(1) || '0'}%
                      </span>
                    </div>
                    <p className="text-white/60 text-sm">CPU Kullanımı</p>
                  </div>

                  {/* Memory */}
                  <div className="card p-4">
                    <div className="flex items-center justify-between mb-2">
                      <HardDrive className="w-5 h-5 text-purple-400" />
                      <span className="text-2xl font-bold text-white">
                        {serverData.system?.memory?.virtual_memory?.percent?.toFixed(1) || '0'}%
                      </span>
                    </div>
                    <p className="text-white/60 text-sm">RAM Kullanımı</p>
                  </div>

                  {/* Network */}
                  <div className="card p-4">
                    <div className="flex items-center justify-between mb-2">
                      <Wifi className="w-5 h-5 text-green-400" />
                      <span className="text-2xl font-bold text-white">
                        {serverData.system?.network?.network_io ? '✓' : '?'}
                      </span>
                    </div>
                    <p className="text-white/60 text-sm">Ağ Durumu</p>
                  </div>

                  {/* Data Count */}
                  <div className="card p-4">
                    <div className="flex items-center justify-between mb-2">
                      <Database className="w-5 h-5 text-orange-400" />
                      <span className="text-2xl font-bold text-white">
                        {serverData.latest ? '1' : '0'}
                      </span>
                    </div>
                    <p className="text-white/60 text-sm">Son Kayıt</p>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="card p-4">
                <h4 className="text-white font-medium mb-3">İşlemler</h4>
                <div className="flex space-x-3">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => fetchServerData()}
                    disabled={loading}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    <Eye className="w-4 h-4" />
                    <span>Verileri Yenile</span>
                  </motion.button>
                  
                  {(selectedServer.ip === '127.0.0.1' || selectedServer.ip === 'localhost') ? (
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => toggleMonitoring(selectedServer.id)}
                      className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                        selectedServer.monitoring 
                          ? 'bg-red-500 hover:bg-red-600 text-white' 
                          : 'bg-green-500 hover:bg-green-600 text-white'
                      }`}
                    >
                      {selectedServer.monitoring ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      <span>{selectedServer.monitoring ? 'İzlemeyi Durdur' : 'İzlemeyi Başlat'}</span>
                    </motion.button>
                  ) : (
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => collectServerData(selectedServer.id)}
                      className="bg-blue-500 hover:bg-blue-600 text-white flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors"
                    >
                      <Database className="w-4 h-4" />
                      <span>Veri Topla</span>
                    </motion.button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="card p-8 text-center">
              <Monitor className="w-16 h-16 text-white/30 mx-auto mb-4" />
              <p className="text-white/60">Bir sunucu seçin</p>
            </div>
          )}
        </div>
      </div>

      {/* Add Server Modal */}
      <AnimatePresence>
        {showAddForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowAddForm(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="card p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-white font-semibold mb-4">Yeni Sunucu Ekle</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-white/60 text-sm mb-2">Sunucu Adı</label>
                  <input
                    type="text"
                    value={newServer.name}
                    onChange={(e) => setNewServer(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-white/10 text-white outline-none"
                    placeholder="Örn: Web Sunucusu"
                  />
                </div>
                
                <div>
                  <label className="block text-white/60 text-sm mb-2">IP Adresi</label>
                  <input
                    type="text"
                    value={newServer.ip}
                    onChange={(e) => setNewServer(prev => ({ ...prev, ip: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-white/10 text-white outline-none"
                    placeholder="Örn: 192.168.1.100"
                  />
                </div>
                
                <div>
                  <label className="block text-white/60 text-sm mb-2">Açıklama (Opsiyonel)</label>
                  <input
                    type="text"
                    value={newServer.description}
                    onChange={(e) => setNewServer(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-white/10 text-white outline-none"
                    placeholder="Sunucu açıklaması"
                  />
                </div>
              </div>
              
              <div className="flex space-x-3 mt-6">
                <button
                  onClick={() => setShowAddForm(false)}
                  className="flex-1 px-4 py-2 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-colors"
                >
                  İptal
                </button>
                <button
                  onClick={addServer}
                  disabled={!newServer.name || !newServer.ip}
                  className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Ekle
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ServersManager;
