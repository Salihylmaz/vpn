import React, { useState, useEffect, useCallback } from 'react';
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
  Pause,
  User,
  MapPin,
  Calendar,
  Settings,
  BarChart3,
  Network,
  Shield,
  Clock,
  Zap,
  Globe,
  Tag
} from 'lucide-react';
import { apiPost, apiGet, apiDelete } from '../lib/apiClient';

const ServersManager = () => {
  const [servers, setServers] = useState([]);
  const [selectedServer, setSelectedServer] = useState(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newServer, setNewServer] = useState({ 
    name: '', 
    ip: '', 
    description: '',
    category: 'server',
    location: '',
    owner: '',
    tags: []
  });
  const [serverData, setServerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const serverCategories = [
    { id: 'server', name: 'Sunucu', icon: '🖥️', color: 'blue' },
    { id: 'workstation', name: 'İş İstasyonu', icon: '💻', color: 'green' },
    { id: 'laptop', name: 'Dizüstü', icon: '💻', color: 'purple' },
    { id: 'router', name: 'Router/Ağ', icon: '🌐', color: 'orange' },
    { id: 'database', name: 'Veritabanı', icon: '🗄️', color: 'red' },
    { id: 'web', name: 'Web Sunucusu', icon: '🌍', color: 'cyan' }
  ];

  const fetchServerData = useCallback(async () => {
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
  }, [selectedServer]);

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
  }, [selectedServer, fetchServerData]);

  const loadServers = async () => {
    try {
      const response = await apiGet('/api/servers');
      setServers(response.servers || []);
    } catch (error) {
      console.error('Sunucular yüklenemedi:', error);
    }
  };

  const addServer = async () => {
    if (!newServer.name || !newServer.ip) return;
    
    try {
      const response = await apiPost('/api/servers', {
        name: newServer.name,
        ip: newServer.ip,
        description: newServer.description,
        category: newServer.category,
        location: newServer.location,
        owner: newServer.owner,
        tags: newServer.tags
      });
      
      if (response.server) {
        await loadServers(); // Reload servers from Elasticsearch
        setNewServer({ 
          name: '', 
          ip: '', 
          description: '',
          category: 'server',
          location: '',
          owner: '',
          tags: []
        });
        setShowAddForm(false);
        
        // Automatically select the newly added server
        setSelectedServer(response.server);
      }
    } catch (error) {
      console.error('Sunucu eklenemedi:', error);
      console.error('Error details:', error.response?.data || error.message);
      
      let errorMessage = 'Bilinmeyen hata';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert('Sunucu eklenirken hata oluştu: ' + errorMessage);
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
      console.error('Error details:', error.response?.data || error.message);
      
      let errorMessage = 'Bilinmeyen hata';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert('Sunucu silinirken hata oluştu: ' + errorMessage);
    }
  };

  const deleteServersByName = async (serverName) => {
    if (!window.confirm(`'${serverName}' adlı tüm sunucuları silmek istediğinizden emin misiniz?`)) {
      return;
    }
    
    try {
      const response = await fetch(`/api/servers/delete-by-name/${encodeURIComponent(serverName)}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      // Reload servers list
      await loadServers();
      setSelectedServer(null);
      
      alert(result.message || `${serverName} sunucuları silindi`);
      
    } catch (error) {
      console.error('Sunucular silinemedi:', error);
      alert('Sunucu silme hatası: ' + error.message);
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
      console.error('Error details:', error.response?.data || error.message);
      
      let errorMessage = 'Bilinmeyen hata';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert('İzleme durumu değiştirilemedi: ' + errorMessage);
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
      console.error('Error details:', error.response?.data || error.message);
      
      let errorMessage = 'Bilinmeyen hata';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert('Veri toplama başlatılamadı: ' + errorMessage);
    }
  };

  const activateServerProfile = async (serverId) => {
    try {
      const response = await apiPost(`/api/servers/${serverId}/activate`);
      
      // Update servers list to reflect the activation
      await loadServers();
      
      alert(response.message || 'Sunucu profili aktifleştirildi');
      
    } catch (error) {
      console.error('Profil aktifleştirilemedi:', error);
      console.error('Error details:', error.response?.data || error.message);
      
      let errorMessage = 'Bilinmeyen hata';
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      alert('Profil aktifleştirilemedi: ' + errorMessage);
    }
  };

  const clearAllServers = async () => {
    if (!window.confirm('Tüm sunucu profillerini silmek istediğinizden emin misiniz?')) {
      return;
    }
    
    try {
      const response = await fetch('/api/servers/clear-all', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      
      // Reload servers list
      await loadServers();
      setSelectedServer(null);
      
      alert(result.message || 'Tüm profiller temizlendi');
      
    } catch (error) {
      console.error('Profiller temizlenemedi:', error);
      alert('Profil temizleme hatası: ' + error.message);
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

  const getCategoryInfo = (categoryId) => {
    return serverCategories.find(cat => cat.id === categoryId) || serverCategories[0];
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatUptime = (seconds) => {
    if (!seconds) return 'Bilinmiyor';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}g ${hours}s ${minutes}d`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex justify-between items-center"
        >
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Sunucu Profilleri</h1>
            <p className="text-white/60">Sistem ve ağ bilgilerini detaylı olarak izleyin</p>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowAddForm(true)}
            className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 shadow-lg"
          >
            <Plus className="w-5 h-5" />
            <span>Yeni Profil</span>
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={clearAllServers}
            className="bg-red-500 hover:bg-red-600 text-white px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 shadow-lg"
          >
            <Trash2 className="w-5 h-5" />
            <span>Tümünü Sil</span>
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => deleteServersByName('Yerel Bilgisayar')}
            className="bg-red-500 hover:bg-red-600 text-white px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 shadow-lg"
          >
            <Trash2 className="w-5 h-5" />
            <span>Yerel Bilgisayarları Sil</span>
          </motion.button>
        </motion.div>

        <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
          {/* Server Profiles List */}
          <div className="xl:col-span-1">
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-white font-semibold flex items-center">
                  <Server className="w-5 h-5 mr-2" />
                  Profiller ({servers.length})
                </h3>
              </div>
              
              <div className="space-y-3">
                {servers.map((server) => {
                  const categoryInfo = getCategoryInfo(server.category);
                  return (
                    <motion.div
                      key={server.id}
                      whileHover={{ scale: 1.02 }}
                      onClick={() => setSelectedServer(server)}
                      className={`p-4 rounded-xl cursor-pointer transition-all ${
                        selectedServer?.id === server.id 
                          ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/50' 
                          : 'bg-white/5 hover:bg-white/10 border border-transparent'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="text-2xl">{categoryInfo.icon}</div>
                          <div>
                            <p className="text-white font-medium">{server.name}</p>
                            <p className="text-white/60 text-sm">{server.ip}</p>
                            <div className="flex items-center space-x-2 mt-1">
                              <span className={`text-xs px-2 py-1 rounded-full bg-${categoryInfo.color}-500/20 text-${categoryInfo.color}-400`}>
                                {categoryInfo.name}
                              </span>
                              <div className={`${getStatusColor(server.status)}`}>
                                {getStatusIcon(server.status)}
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex flex-col items-end space-y-1">
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
                            className={`p-2 rounded-lg ${
                              server.monitoring ? 'text-green-400 bg-green-500/20' : 'text-white/60 bg-white/10'
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
                                activateServerProfile(server.id);
                              }}
                              className="p-2 rounded-lg text-blue-400 hover:bg-blue-500/20"
                            >
                              <Play className="w-4 h-4" />
                            </motion.button>
                          )}
                          
                          {server.id !== 'localhost' && (
                            <motion.button
                              whileHover={{ scale: 1.1 }}
                              whileTap={{ scale: 0.9 }}
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteServer(server.id);
                              }}
                              className="p-2 rounded-lg text-red-400 hover:bg-red-500/20"
                            >
                              <Trash2 className="w-4 h-4" />
                            </motion.button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Server Details & Data */}
          <div className="xl:col-span-3">
            {selectedServer ? (
              <div className="space-y-4">
                {/* Server Info */}
                <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
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
                    <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                      <div className="flex items-center justify-between mb-2">
                        <Cpu className="w-5 h-5 text-blue-400" />
                        <span className="text-2xl font-bold text-white">
                          {serverData.system?.cpu?.cpu_percent?.toFixed(1) || '0'}%
                        </span>
                      </div>
                      <p className="text-white/60 text-sm">CPU Kullanımı</p>
                    </div>

                    {/* Memory */}
                    <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                      <div className="flex items-center justify-between mb-2">
                        <HardDrive className="w-5 h-5 text-purple-400" />
                        <span className="text-2xl font-bold text-white">
                          {serverData.system?.memory?.virtual_memory?.percent?.toFixed(1) || '0'}%
                        </span>
                      </div>
                      <p className="text-white/60 text-sm">RAM Kullanımı</p>
                    </div>

                    {/* Network */}
                    <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                      <div className="flex items-center justify-between mb-2">
                        <Wifi className="w-5 h-5 text-green-400" />
                        <span className="text-2xl font-bold text-white">
                          {serverData.system?.network?.network_io ? '✓' : '?'}
                        </span>
                      </div>
                      <p className="text-white/60 text-sm">Ağ Durumu</p>
                    </div>

                    {/* Data Count */}
                    <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
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
                <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                  <h4 className="text-white font-medium mb-3">İşlemler</h4>
                  <div className="flex space-x-3">
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => fetchServerData()}
                      disabled={loading}
                      className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 shadow-lg"
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
              <div className="bg-white/10 backdrop-blur-sm rounded-xl p-8 text-center">
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
                className="bg-white/10 backdrop-blur-sm rounded-xl p-6 w-full max-w-md"
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
                  
                  <div>
                    <label className="block text-white/60 text-sm mb-2">Kategori</label>
                    <select
                      value={newServer.category}
                      onChange={(e) => setNewServer(prev => ({ ...prev, category: e.target.value }))}
                      className="w-full px-3 py-2 rounded-lg bg-white/10 text-white outline-none"
                    >
                      {serverCategories.map(category => (
                        <option key={category.id} value={category.id}>{category.name}</option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <label className="block text-white/60 text-sm mb-2">Konum</label>
                    <input
                      type="text"
                      value={newServer.location}
                      onChange={(e) => setNewServer(prev => ({ ...prev, location: e.target.value }))}
                      className="w-full px-3 py-2 rounded-lg bg-white/10 text-white outline-none"
                      placeholder="Örn: İstanbul"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-white/60 text-sm mb-2">Sahip</label>
                    <input
                      type="text"
                      value={newServer.owner}
                      onChange={(e) => setNewServer(prev => ({ ...prev, owner: e.target.value }))}
                      className="w-full px-3 py-2 rounded-lg bg-white/10 text-white outline-none"
                      placeholder="Örn: John Doe"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-white/60 text-sm mb-2">Etiketler</label>
                    <input
                      type="text"
                      value={newServer.tags.join(', ')}
                      onChange={(e) => setNewServer(prev => ({ ...prev, tags: e.target.value.split(',').map(tag => tag.trim()) }))}
                      className="w-full px-3 py-2 rounded-lg bg-white/10 text-white outline-none"
                      placeholder="Örn: web, sunucu, linux"
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
                    className="flex-1 bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white px-6 py-3 rounded-xl font-semibold flex items-center space-x-2 shadow-lg"
                  >
                    Ekle
                  </button>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default ServersManager;
