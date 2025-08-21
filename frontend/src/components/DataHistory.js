import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  Download, 
  RefreshCw
} from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiGet } from '../lib/apiClient';

const DataHistory = () => {
  const [historicalData, setHistoricalData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('24h');
  const [selectedMetric, setSelectedMetric] = useState('cpu');

  const fetchHistoricalData = useCallback(async () => {
    try {
      setLoading(true);
      const json = await apiGet('/api/latest-data');
      const items = Array.isArray(json.data) ? json.data : [];

      // Filter by time range
      const now = Date.now();
      const msMap = { '1h': 3600e3, '6h': 6*3600e3, '24h': 24*3600e3, '7d': 7*24*3600e3 };
      const maxAge = msMap[timeRange] || msMap['24h'];

      const data = items
        .filter(it => it.timestamp && (now - new Date(it.timestamp).getTime()) <= maxAge)
        .map(it => {
          const cpu = it.system_data?.cpu?.cpu_percent ?? it.cpu?.cpu_percent ?? 0;
          const memory = it.system_data?.memory?.virtual_memory?.percent ?? it.memory?.virtual_memory?.percent ?? 0;
          const disk_percent = it.system_data?.disk?.disk_usage?.main?.percent ?? it.disk?.disk_usage?.main?.percent ?? 0;
          const download_mbps = it.web_data?.speed_test?.download_speed ?? it.speed_test?.download_speed ?? null;
          const vpn_status = it.web_data?.vpn_detection?.status ?? it.vpn_detection?.status ?? null;
          return {
            time: new Date(it.timestamp).toLocaleString(),
            cpu,
            memory,
            disk_percent,
            download_mbps,
            vpn_status
          };
        })
        .reverse();

      setHistoricalData(data);
      setLoading(false);
    } catch (error) {
      console.error('Veri geçmişi yükleme hatası:', error);
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  const exportCSV = () => {
    const headers = ['time','cpu','memory','disk_percent','download_mbps','vpn_status'];
    const rows = historicalData.map(d => [d.time, d.cpu, d.memory, d.disk_percent, d.download_mbps ?? '', d.vpn_status ?? ''].join(','));
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `history_${timeRange}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Veri Geçmişi</h1>
          <p className="text-white/60">Elasticsearch'ten gerçek veriler</p>
        </div>
        <div className="flex items-center space-x-3">
          <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)} className="px-3 py-2 bg-black/40 text-white rounded-lg border border-white/20">
            <option value="1h">Son 1 Saat</option>
            <option value="6h">Son 6 Saat</option>
            <option value="24h">Son 24 Saat</option>
            <option value="7d">Son 7 Gün</option>
          </select>
          <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={fetchHistoricalData} className="btn-secondary flex items-center">
            <RefreshCw className="w-4 h-4 mr-2" /> Yenile
          </motion.button>
          <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={exportCSV} className="btn-secondary flex items-center">
            <Download className="w-4 h-4 mr-2" /> Dışa Aktar
          </motion.button>
        </div>
      </motion.div>

      <div className="card p-6">
        <div className="flex items-center mb-4 space-x-4">
          <span className="text-white/80">Metriği Seç:</span>
          <select value={selectedMetric} onChange={(e) => setSelectedMetric(e.target.value)} className="px-3 py-2 bg-black/40 text-white rounded-lg border border-white/20">
            <option value="cpu">CPU (%)</option>
            <option value="memory">Bellek (%)</option>
            <option value="download_mbps">İndirme Hızı (Mbps)</option>
            <option value="disk_percent">Disk (%)</option>
          </select>
        </div>
        <div style={{ width: '100%', height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={historicalData} margin={{ top: 10, right: 20, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="time" stroke="#bbb" />
              <YAxis stroke="#bbb" />
              <Tooltip contentStyle={{ background: 'rgba(0,0,0,0.7)', border: 'none', color: '#fff' }} />
              <Line type="monotone" dataKey={selectedMetric} stroke="#22d3ee" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Table */}
      <div className="card p-6">
        <h3 className="text-white font-semibold mb-4">Detaylı Kayıtlar</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-left text-white/80">
            <thead className="text-white">
              <tr>
                <th className="py-2 px-3">Zaman</th>
                <th className="py-2 px-3">CPU (%)</th>
                <th className="py-2 px-3">Bellek (%)</th>
                <th className="py-2 px-3">Disk (%)</th>
                <th className="py-2 px-3">İndirme Hızı (Mbps)</th>
                <th className="py-2 px-3">VPN</th>
              </tr>
            </thead>
            <tbody>
              {historicalData.map((row, idx) => (
                <tr key={idx} className="border-t border-white/10">
                  <td className="py-2 px-3">{row.time}</td>
                  <td className="py-2 px-3">{row.cpu}</td>
                  <td className="py-2 px-3">{row.memory}</td>
                  <td className="py-2 px-3">{row.disk_percent}</td>
                  <td className="py-2 px-3">{row.download_mbps ?? '-'}</td>
                  <td className="py-2 px-3">{row.vpn_status ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DataHistory;
