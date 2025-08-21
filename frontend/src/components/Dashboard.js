import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Activity, 
  Cpu, 
  HardDrive, 
  Wifi, 
  Shield, 
  TrendingUp,
  Clock,
  Database
} from 'lucide-react';
import { apiGet, apiPost } from '../lib/apiClient';

const Dashboard = () => {
  const [systemData, setSystemData] = useState(null);
  const [healthStatus, setHealthStatus] = useState(null);
  const [monitoringStatus, setMonitoringStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000); // 30 saniyede bir güncelle
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [health, system, status] = await Promise.all([
        apiGet('/api/health'),
        apiGet('/api/system-info'),
        apiGet('/api/status')
      ]);

      setHealthStatus(health);
      setSystemData(system);
      setMonitoringStatus(status);
      setLoading(false);
    } catch (error) {
      console.error('Dashboard veri yükleme hatası:', error);
      setLoading(false);
    }
  };

  const handleCollectData = async () => {
    try {
      setCollecting(true);
      await apiPost('/api/collect-data', {});
      alert('✅ Veri toplama başlatıldı');
      await fetchDashboardData();
    } catch (error) {
      console.error('Veri toplama hatası:', error);
      alert('❌ Veri toplama sırasında hata oluştu');
    } finally {
      setCollecting(false);
    }
  };

  const handleQuickAction = (action) => {
    switch (action) {
      case 'collect':
        handleCollectData();
        break;
      case 'history':
        window.location.href = '/history';
        break;
      case 'system':
        window.location.href = '/system';
        break;
      default:
        break;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-400';
      case 'warning': return 'text-yellow-400';
      case 'unhealthy':
      case 'error': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  const getCpuColor = (usage) => {
    if (usage < 50) return 'text-green-400';
    if (usage < 80) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getMemoryColor = (usage) => {
    if (usage < 70) return 'text-green-400';
    if (usage < 90) return 'text-yellow-400';
    return 'text-red-400';
  };

  const memPercent = systemData?.memory?.virtual_memory?.percent || 0;
  const memUsed = systemData?.memory?.virtual_memory?.used || 0;
  const memTotal = systemData?.memory?.virtual_memory?.total || 1;
  const cpuPercent = systemData?.cpu?.cpu_percent || 0;
  const networkOk = !!systemData?.network?.network_io;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
          <p className="text-white/60">Sistem durumu ve performans metrikleri</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleCollectData}
          disabled={collecting}
          className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {collecting ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              <span>Toplanıyor...</span>
            </>
          ) : (
            <>
              <Activity className="w-5 h-5" />
              <span>Veri Topla</span>
            </>
          )}
        </motion.button>
      </motion.div>

      {/* Continuous Monitoring Status */}
      {monitoringStatus && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className={`w-3 h-3 rounded-full ${monitoringStatus.active ? 'bg-green-400' : 'bg-red-400'}`}></div>
              <div>
                <h3 className="text-white font-semibold">Sürekli İzleme</h3>
                <p className="text-white/60 text-sm">
                  {monitoringStatus.active ? 'Aktif - 1 dakikada bir veri toplanıyor' : 'Pasif'}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-white/60 text-sm">Son toplama</p>
              <p className="text-white font-medium">{monitoringStatus.last_collection || '-'}</p>
              <p className="text-white/60 text-sm">Sonraki toplama</p>
              <p className="text-white font-medium">{monitoringStatus.next_collection || '-'}</p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* System Health */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div className={`text-2xl font-bold ${getStatusColor(healthStatus?.status)}`}>
              {healthStatus?.status === 'healthy' ? '✓' : '⚠'}
            </div>
          </div>
          <h3 className="text-white font-semibold mb-1">Sistem Sağlığı</h3>
          <p className="text-white/60 text-sm">
            {healthStatus?.elasticsearch ? 'Elasticsearch Bağlı' : 'Bağlantı Yok'}
          </p>
        </motion.div>

        {/* CPU Usage */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
              <Cpu className="w-6 h-6 text-white" />
            </div>
            <div className={`text-2xl font-bold ${getCpuColor(cpuPercent)}`}>
              {cpuPercent.toFixed(1)}%
            </div>
          </div>
          <h3 className="text-white font-semibold mb-1">CPU Kullanımı</h3>
          <p className="text-white/60 text-sm">
            {systemData?.cpu?.cpu_count_logical || 0} Mantıksal Çekirdek
          </p>
        </motion.div>

        {/* Memory Usage */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
              <HardDrive className="w-6 h-6 text-white" />
            </div>
            <div className={`text-2xl font-bold ${getMemoryColor(memPercent)}`}>
              {memPercent.toFixed(1)}%
            </div>
          </div>
          <h3 className="text-white font-semibold mb-1">RAM Kullanımı</h3>
          <p className="text-white/60 text-sm">
            {(memUsed / 1024 / 1024 / 1024).toFixed(1)} GB / {(memTotal / 1024 / 1024 / 1024).toFixed(1)} GB
          </p>
        </motion.div>

        {/* Network Status */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-500 rounded-xl flex items-center justify-center">
              <Wifi className="w-6 h-6 text-white" />
            </div>
            <div className={`text-2xl font-bold ${networkOk ? 'text-green-400' : 'text-yellow-400'}`}>
              {networkOk ? '✓' : '⚠'}
            </div>
          </div>
          <h3 className="text-white font-semibold mb-1">Ağ Durumu</h3>
          <p className="text-white/60 text-sm">
            {networkOk ? 'Aktif' : 'Bilgi Yok'}
          </p>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="card p-6"
      >
        <h3 className="text-white font-semibold mb-4 flex items-center">
          <TrendingUp className="w-5 h-5 mr-2" />
          Hızlı İşlemler
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <motion.button 
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleQuickAction('collect')}
            className="btn-secondary flex items-center justify-center space-x-2"
          >
            <Database className="w-4 h-4" />
            <span>Veri Topla</span>
          </motion.button>
          <motion.button 
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleQuickAction('history')}
            className="btn-secondary flex items-center justify-center space-x-2"
          >
            <Clock className="w-4 h-4" />
            <span>Geçmişi Görüntüle</span>
          </motion.button>
          <motion.button 
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleQuickAction('system')}
            className="btn-secondary flex items-center justify-center space-x-2"
          >
            <Activity className="w-4 h-4" />
            <span>Sistem Durumu</span>
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
};

export default Dashboard;
