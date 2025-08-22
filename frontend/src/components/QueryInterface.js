import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Bot, 
  User, 
  Loader2,
  Power,
  CheckCircle
} from 'lucide-react';
import { apiPost, apiGet } from '../lib/apiClient';

const QueryInterface = () => {
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modelStatus, setModelStatus] = useState({ initialized: false, status: 'not_initialized' });
  const [initializingModel, setInitializingModel] = useState(false);

  useEffect(() => {
    checkModelStatus();
  }, []);

  const checkModelStatus = async () => {
    try {
      const status = await apiGet('/api/model-status');
      setModelStatus(status);
    } catch (error) {
      console.error('Model durum kontrolü hatası:', error);
    }
  };

  const initializeModel = async () => {
    try {
      setInitializingModel(true);
      const response = await apiPost('/api/init-model', {});
      await checkModelStatus();
      setConversation(prev => [...prev, { 
        role: 'assistant', 
        content: response.message || 'Model başarıyla başlatıldı!' 
      }]);
    } catch (error) {
      console.error('Model başlatma hatası:', error);
      setConversation(prev => [...prev, { 
        role: 'assistant', 
        content: 'Model başlatılamadı. Lütfen tekrar deneyin.' 
      }]);
    } finally {
      setInitializingModel(false);
    }
  };

  const exampleQuestions = [
    'CPU kullanımı nasıl?',
    'Son 1 günde kaç kayıt var?',
    'Son 6 saatte VPN durumu nasıldı?',
    'Son ölçümlerde indirme hızı ortalaması?',
    'RAM kullanımı yüksek mi?'
  ];

  const ask = async (text) => {
    if (!text?.trim()) return;
    setLoading(true);
    setQuestion('');
    setConversation(prev => [...prev, { role: 'user', content: text }]);

    try {
      const data = await apiPost('/api/query', { question: text });
      const answer = data?.response || 'Yanıt alınamadı.';
      setConversation(prev => [...prev, { role: 'assistant', content: answer }]);
    } catch (e) {
      console.error('Sorgu hatası', e);
      setConversation(prev => [...prev, { role: 'assistant', content: 'Sunucuya bağlanılamadı.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    ask(question);
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Sorgu Sistemi</h1>
          <p className="text-white/60">Gerçek veriler ile doğal dilde sorgulama yapın</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg ${
            modelStatus.initialized ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {modelStatus.initialized ? (
              <CheckCircle className="w-4 h-4" />
            ) : (
              <Power className="w-4 h-4" />
            )}
            <span className="text-sm">
              {modelStatus.initialized ? 'Model Hazır' : 'Model Kapalı'}
            </span>
          </div>
          {!modelStatus.initialized && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={initializeModel}
              disabled={initializingModel}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {initializingModel ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Başlatılıyor...</span>
                </>
              ) : (
                <>
                  <Power className="w-4 h-4" />
                  <span>Modeli Başlat</span>
                </>
              )}
            </motion.button>
          )}
        </div>
      </motion.div>

      {/* Quick examples */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-2">
          {exampleQuestions.map((ex, idx) => (
            <button 
              key={idx} 
              onClick={() => ask(ex)} 
              disabled={!modelStatus.initialized}
              className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Conversation - flexible height */}
      <div className="card p-4 space-y-3 flex-1 overflow-y-auto">
        <AnimatePresence>
          {conversation.map((msg, idx) => (
            <motion.div key={idx} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className={`flex items-start space-x-3 ${msg.role === 'assistant' ? '' : 'justify-end'}`}>
              {msg.role === 'assistant' && <Bot className="w-5 h-5 text-white mt-1" />}
              <div className={`px-3 py-2 rounded-lg ${msg.role === 'assistant' ? 'bg-white/10 text-white' : 'bg-blue-500/80 text-white'}`}>
                {msg.content}
              </div>
              {msg.role === 'user' && <User className="w-5 h-5 text-white mt-1" />}
            </motion.div>
          ))}
        </AnimatePresence>
        {loading && (
          <div className="flex items-center space-x-2 text-white/70">
            <Loader2 className="w-4 h-4 animate-spin" /> <span>Yanıt oluşturuluyor...</span>
          </div>
        )}
      </div>

      {/* Input - fixed at bottom */}
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={modelStatus.initialized ? "Bir soru yazın..." : "Önce modeli başlatın..."}
          disabled={!modelStatus.initialized}
          className="flex-1 px-4 py-3 rounded-lg bg-white/10 text-white outline-none disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button 
          type="submit" 
          disabled={!modelStatus.initialized}
          className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="w-4 h-4" /> <span>Gönder</span>
        </button>
      </form>
    </div>
  );
};

export default QueryInterface;
