import React from 'react';
import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  Monitor, 
  MessageSquare, 
  History,
  Shield,
  Server
} from 'lucide-react';

const Navigation = () => {
  const navItems = [
    {
      path: '/',
      name: 'Dashboard',
      icon: LayoutDashboard,
      color: 'from-blue-500 to-cyan-500'
    },
    {
      path: '/system',
      name: 'Sistem İzleme',
      icon: Monitor,
      color: 'from-green-500 to-emerald-500'
    },
    {
      path: '/servers',
      name: 'Sunucular',
      icon: Server,
      color: 'from-indigo-500 to-purple-500'
    },
    {
      path: '/query',
      name: 'Sorgu Sistemi',
      icon: MessageSquare,
      color: 'from-purple-500 to-pink-500'
    },
    {
      path: '/history',
      name: 'Veri Geçmişi',
      icon: History,
      color: 'from-orange-500 to-red-500'
    }
  ];

  return (
    <motion.div
      initial={{ x: -250 }}
      animate={{ x: 0 }}
      transition={{ duration: 0.5 }}
      className="w-64 bg-black/20 backdrop-blur-xl border-r border-white/10 min-h-screen p-6"
    >
      {/* Logo */}
      <div className="mb-8">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-white font-bold text-lg">VPN Monitor</h1>
            <p className="text-white/60 text-sm">Sistem İzleme</p>
          </div>
        </div>
      </div>

      {/* Navigation Items */}
      <nav className="space-y-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-300 group ${
                  isActive
                    ? `bg-gradient-to-r ${item.color} text-white shadow-lg`
                    : 'text-white/70 hover:text-white hover:bg-white/10'
                }`
              }
            >
              <motion.div
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
              >
                <Icon className="w-5 h-5" />
              </motion.div>
              <span className="font-medium">{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Status Indicator */}
      <div className="absolute bottom-6 left-6 right-6">
        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
          <div className="flex items-center space-x-3">
            <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            <div>
              <p className="text-white text-sm font-medium">Sistem Aktif</p>
              <p className="text-white/60 text-xs">Elasticsearch Bağlı</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default Navigation;
