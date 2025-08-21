import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Cpu, 
  HardDrive, 
  Wifi
} from 'lucide-react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { apiGet } from '../lib/apiClient';

const SystemMonitor = () => {
  const [systemData, setSystemData] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSystemData();
    fetchHistory();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchSystemData();
      fetchHistory();
    }, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const fetchSystemData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGet('/api/system-info');
      setSystemData(data);
      setLoading(false);
    } catch (e) {
      console.error('Sistem verisi hatası', e);
      setError('Sunucuya bağlanılamadı.');
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const json = await apiGet('/api/latest-data');
      const items = Array.isArray(json.data) ? json.data : [];
      const chart = items.map(item => ({
        time: new Date(item.timestamp).toLocaleTimeString(),
        cpu: item.system_data?.cpu?.cpu_percent ?? item.cpu?.cpu_percent ?? 0,
        memory: item.system_data?.memory?.virtual_memory?.percent ?? item.memory?.virtual_memory?.percent ?? 0
      })).reverse();
      setHistoricalData(chart);
    } catch (e) {
      console.error('Geçmiş veri hatası', e);
      // geçmiş yüklenemese de UI'yı engellemeyelim
    }
  };

  const memPercent = systemData?.memory?.virtual_memory?.percent || 0;
  const cpuPercent = systemData?.cpu?.cpu_percent || 0;

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Sistem İzleme</h1>
          <p className="text-white/60">Gerçek zamanlı sistem metrikleri</p>
        </div>
        <div className="flex items-center space-x-4">
          <label className="flex items-center space-x-2 text-white/80">
            <input type="checkbox" checked={autoRefresh} onChange={() => setAutoRefresh(!autoRefresh)} />
            <span>Otomatik Yenile</span>
          </label>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => { fetchSystemData(); fetchHistory(); }}
            className="btn-secondary"
          >
            Yenile
          </motion.button>
        </div>
      </motion.div>

      {error && (
        <div className="card p-4 border border-red-500/40">
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
              <Cpu className="w-6 h-6 text-white" />
            </div>
            <div className={`text-2xl font-bold ${cpuPercent < 50 ? 'text-green-400' : cpuPercent < 80 ? 'text-yellow-400' : 'text-red-400'}`}>{(cpuPercent || 0).toFixed(1)}%</div>
          </div>
          <h3 className="text-white font-semibold mb-1">CPU Kullanımı</h3>
          <p className="text-white/60 text-sm">Mantıksal Çekirdek: {systemData?.cpu?.cpu_count_logical ?? '-'}</p>
        </div>
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
              <HardDrive className="w-6 h-6 text-white" />
            </div>
            <div className={`text-2xl font-bold ${memPercent < 70 ? 'text-green-400' : memPercent < 90 ? 'text-yellow-400' : 'text-red-400'}`}>{(memPercent || 0).toFixed(1)}%</div>
          </div>
          <h3 className="text-white font-semibold mb-1">Bellek Kullanımı</h3>
          <p className="text-white/60 text-sm">Toplam: {systemData?.memory?.virtual_memory?.total ? ((systemData.memory.virtual_memory.total)/1024/1024/1024).toFixed(1) : '-'} GB</p>
        </div>
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-500 rounded-xl flex items-center justify-center">
              <Wifi className="w-6 h-6 text-white" />
            </div>
            <div className={`text-2xl font-bold ${systemData?.network?.network_io ? 'text-green-400' : 'text-yellow-400'}`}>{systemData?.network?.network_io ? '✓' : '⚠'}</div>
          </div>
          <h3 className="text-white font-semibold mb-1">Ağ Durumu</h3>
          <p className="text-white/60 text-sm">Bağlantılar: {systemData?.network?.network_connections?.total_connections ?? '-'}</p>
        </div>
      </div>

      {/* Charts */}
      <div className="card p-6">
        <h3 className="text-white font-semibold mb-4">CPU ve Bellek Geçmişi</h3>
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <AreaChart data={historicalData} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#22d3ee" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="colorMem" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#a78bfa" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="#bbb" />
              <YAxis stroke="#bbb" domain={[0, 100]} />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.7)', border: 'none', color: '#fff' }} />
              <Area type="monotone" dataKey="cpu" stroke="#22d3ee" fillOpacity={1} fill="url(#colorCpu)" />
              <Area type="monotone" dataKey="memory" stroke="#a78bfa" fillOpacity={1} fill="url(#colorMem)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default SystemMonitor;
