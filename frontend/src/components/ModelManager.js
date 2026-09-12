import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Brain, 
  Download, 
  Settings, 
  RefreshCw, 
  CheckCircle, 
  AlertCircle,
  Cpu,
  Zap,
  Clock,
  BarChart3,
  Sliders
} from 'lucide-react';
import { apiGet, apiPost } from '../lib/apiClient';

const ModelManager = () => {
  const [models, setModels] = useState([]);
  const [currentModel, setCurrentModel] = useState(null);
  const [modelSettings, setModelSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [changing, setChanging] = useState(false);
  const [systemInfo, setSystemInfo] = useState({});
  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiGet('/api/models');
      
      // Check if there's an error in the response
      if (response.error) {
        setError(response.error);
      }
      
      setModels(response.models || []);
      setCurrentModel(response.current_model);
      setSystemInfo({
        cuda_available: response.system_info?.cuda_available || false,
        torch_threads: response.system_info?.torch_threads || 1
      });
      
      // Load current settings
      try {
        const settingsResponse = await apiGet('/api/models/settings');
        setModelSettings(settingsResponse.settings || settingsResponse.model_settings || {});
      } catch (settingsError) {
        console.warn('Settings could not be loaded:', settingsError);
        setModelSettings({});
      }
    } catch (err) {
      console.error('Model loading error:', err);
      setError('Backend bağlantısı kurulamadı. Lütfen backend servisinin çalıştığından emin olun.');
      setModels([]); // Ensure models is always an array
    } finally {
      setLoading(false);
    }
  };

  const changeModel = async (modelId) => {
    try {
      setChanging(true);
      setError(null);
      
      const response = await apiPost('/api/models/change', {
        model_id: modelId
      });
      
      setCurrentModel(response.model);
      
      // Show success message
      setTimeout(() => {
        setChanging(false);
      }, 2000);
      
    } catch (err) {
      setError('Model değiştirilemedi: ' + err.message);
      setChanging(false);
    }
  };

  const updateSettings = async (newSettings) => {
    try {
      const response = await apiPost('/api/models/settings', newSettings);
      setModelSettings(response.settings);
      setShowSettings(false);
    } catch (err) {
      setError('Ayarlar güncellenemedi: ' + err.message);
    }
  };

  const reloadModel = async () => {
    try {
      setChanging(true);
      await apiPost('/api/models/reload');
      await loadModels();
    } catch (err) {
      setError('Model yeniden yüklenemedi: ' + err.message);
    } finally {
      setChanging(false);
    }
  };

  const getModelIcon = (size) => {
    if (size.includes('3B')) return '🚀';
    if (size.includes('7B')) return '⚡';
    if (size.includes('8B')) return '🔥';
    if (size.includes('14B')) return '💎';
    return '🤖';
  };

  const getRecommendationColor = (recommended) => {
    if (recommended.includes('fast')) return 'text-green-400';
    if (recommended.includes('complex')) return 'text-blue-400';
    if (recommended.includes('advanced')) return 'text-purple-400';
    return 'text-gray-400';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto mb-4" />
          <p className="text-white">Model bilgileri yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-gradient-to-r from-violet-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Brain className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white">Model Yönetimi</h1>
                <p className="text-white/60">HuggingFace modellerini yönetin</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white flex items-center space-x-2 transition-colors"
              >
                <Settings className="w-4 h-4" />
                <span>Ayarlar</span>
              </button>
              
              <button
                onClick={reloadModel}
                disabled={changing}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-white flex items-center space-x-2 transition-colors"
              >
                <RefreshCw className={`w-4 h-4 ${changing ? 'animate-spin' : ''}`} />
                <span>Yenile</span>
              </button>
            </div>
          </div>
        </motion.div>

        {/* Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center space-x-3"
          >
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-red-200">{error}</p>
          </motion.div>
        )}

        {/* System Info */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center space-x-3 mb-4">
              <Cpu className="w-6 h-6 text-blue-400" />
              <h3 className="text-white font-semibold">İşlemci</h3>
            </div>
            <p className="text-white/80">
              {systemInfo.cuda_available ? 'CUDA GPU Mevcut' : 'CPU Modu'}
            </p>
            <p className="text-white/60 text-sm">
              {systemInfo.torch_threads} Thread
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center space-x-3 mb-4">
              <Brain className="w-6 h-6 text-purple-400" />
              <h3 className="text-white font-semibold">Aktif Model</h3>
            </div>
            <p className="text-white/80">
              {currentModel ? currentModel.display_name : 'Yüklü değil'}
            </p>
            <p className="text-white/60 text-sm">
              {currentModel ? currentModel.size : 'N/A'}
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20">
            <div className="flex items-center space-x-3 mb-4">
              <BarChart3 className="w-6 h-6 text-green-400" />
              <h3 className="text-white font-semibold">Durum</h3>
            </div>
            <p className="text-white/80">
              {changing ? 'Değiştiriliyor...' : 'Hazır'}
            </p>
            <p className="text-white/60 text-sm">
              {models?.length || 0} Model Mevcut
            </p>
          </div>
        </motion.div>

        {/* Model Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {(models || []).map((model, index) => (
            <motion.div
              key={model?.id || index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`relative bg-white/10 backdrop-blur-sm rounded-xl p-6 border transition-all duration-300 hover:scale-105 cursor-pointer ${
                currentModel?.id === model?.id
                  ? 'border-green-400 bg-green-500/20'
                  : 'border-white/20 hover:border-white/40'
              }`}
              onClick={() => currentModel?.id !== model?.id && !changing && changeModel(model?.id)}
            >
              {/* Current Model Indicator */}
              {currentModel?.id === model?.id && (
                <div className="absolute -top-2 -right-2 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                  <CheckCircle className="w-4 h-4 text-white" />
                </div>
              )}

              {/* Model Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{getModelIcon(model?.size || '')}</span>
                  <div>
                    <h3 className="text-white font-semibold">{model?.display_name || 'Unknown Model'}</h3>
                    <p className="text-white/60 text-sm">{model?.size || 'N/A'}</p>
                  </div>
                </div>
                
                {changing && currentModel?.id !== model?.id && (
                  <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
                )}
              </div>

              {/* Model Description */}
              <p className="text-white/80 text-sm mb-4">{model?.description || 'No description available'}</p>

              {/* Model Details */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-white/60 text-xs">Diller:</span>
                  <span className="text-white/80 text-xs">
                    {(model?.language_support || []).join(', ').toUpperCase() || 'N/A'}
                  </span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-white/60 text-xs">Önerilen:</span>
                  <span className={`text-xs ${getRecommendationColor((model?.recommended_for || []).join(', '))}`}>
                    {(model?.recommended_for || []).join(', ') || 'N/A'}
                  </span>
                </div>
              </div>

              {/* Action Button */}
              <div className="mt-4 pt-4 border-t border-white/10">
                {currentModel?.id === model?.id ? (
                  <div className="flex items-center justify-center space-x-2 text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    <span className="text-sm font-medium">Aktif Model</span>
                  </div>
                ) : (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      changeModel(model?.id);
                    }}
                    disabled={changing}
                    className="w-full py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg text-white text-sm font-medium transition-colors flex items-center justify-center space-x-2"
                  >
                    <Download className="w-4 h-4" />
                    <span>Bu Modeli Yükle</span>
                  </button>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Settings Panel */}
        {showSettings && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-6"
            onClick={() => setShowSettings(false)}
          >
            <div
              className="bg-gray-900 rounded-xl p-6 max-w-md w-full border border-white/20"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-white text-lg font-semibold">Model Ayarları</h3>
                <button
                  onClick={() => setShowSettings(false)}
                  className="text-white/60 hover:text-white"
                >
                  ✕
                </button>
              </div>

              <ModelSettingsForm
                settings={modelSettings}
                onUpdate={updateSettings}
              />
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

// Settings Form Component
const ModelSettingsForm = ({ settings, onUpdate }) => {
  const [formData, setFormData] = useState(settings);

  const handleSubmit = (e) => {
    e.preventDefault();
    onUpdate(formData);
  };

  const handleChange = (key, value) => {
    setFormData(prev => ({
      ...prev,
      [key]: value
    }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-white/80 text-sm mb-2">Max Tokens</label>
        <input
          type="number"
          value={formData.max_new_tokens || 256}
          onChange={(e) => handleChange('max_new_tokens', parseInt(e.target.value))}
          className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white"
          min="1"
          max="2048"
        />
      </div>

      <div>
        <label className="block text-white/80 text-sm mb-2">Temperature</label>
        <input
          type="range"
          value={formData.temperature || 0.7}
          onChange={(e) => handleChange('temperature', parseFloat(e.target.value))}
          className="w-full"
          min="0.1"
          max="2.0"
          step="0.1"
        />
        <div className="text-white/60 text-xs text-center">{formData.temperature || 0.7}</div>
      </div>

      <div>
        <label className="block text-white/80 text-sm mb-2">Top P</label>
        <input
          type="range"
          value={formData.top_p || 0.9}
          onChange={(e) => handleChange('top_p', parseFloat(e.target.value))}
          className="w-full"
          min="0.1"
          max="1.0"
          step="0.1"
        />
        <div className="text-white/60 text-xs text-center">{formData.top_p || 0.9}</div>
      </div>

      <div>
        <label className="block text-white/80 text-sm mb-2">Repetition Penalty</label>
        <input
          type="range"
          value={formData.repetition_penalty || 1.1}
          onChange={(e) => handleChange('repetition_penalty', parseFloat(e.target.value))}
          className="w-full"
          min="1.0"
          max="2.0"
          step="0.1"
        />
        <div className="text-white/60 text-xs text-center">{formData.repetition_penalty || 1.1}</div>
      </div>

      <div>
        <label className="block text-white/80 text-sm mb-2">Max Generation Time (s)</label>
        <input
          type="number"
          value={formData.max_generation_time || 30}
          onChange={(e) => handleChange('max_generation_time', parseFloat(e.target.value))}
          className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white"
          min="5"
          max="120"
        />
      </div>

      <div className="flex space-x-3 pt-4">
        <button
          type="submit"
          className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium transition-colors"
        >
          Kaydet
        </button>
        <button
          type="button"
          onClick={() => setFormData(settings)}
          className="flex-1 py-2 bg-gray-600 hover:bg-gray-700 rounded-lg text-white font-medium transition-colors"
        >
          Sıfırla
        </button>
      </div>
    </form>
  );
};

export default ModelManager;
