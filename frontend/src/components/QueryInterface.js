import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Bot, 
  User, 
  Loader2
} from 'lucide-react';
import { apiPost } from '../lib/apiClient';

const QueryInterface = () => {
  const [question, setQuestion] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);

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
    <div className="space-y-6">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center"
      >
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Sorgu Sistemi</h1>
          <p className="text-white/60">Gerçek veriler ile doğal dilde sorgulama yapın</p>
        </div>
      </motion.div>

      {/* Quick examples */}
      <div className="card p-4">
        <div className="flex flex-wrap gap-2">
          {exampleQuestions.map((ex, idx) => (
            <button key={idx} onClick={() => ask(ex)} className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm">
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Conversation */}
      <div className="card p-4 space-y-3" style={{ maxHeight: 600, height: 500, overflowY: 'auto' }}>
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

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Bir soru yazın..."
          className="flex-1 px-4 py-3 rounded-lg bg-white/10 text-white outline-none"
        />
        <button type="submit" className="btn-primary flex items-center space-x-2">
          <Send className="w-4 h-4" /> <span>Gönder</span>
        </button>
      </form>
    </div>
  );
};

export default QueryInterface;
