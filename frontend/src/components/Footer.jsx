import React from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, Github, Heart } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                <TrendingUp size={16} className="text-white" />
              </div>
              <span className="text-lg font-bold text-slate-900">BhaavShare</span>
            </div>
            <p className="text-slate-500 text-sm leading-relaxed max-w-sm">
              Nepal's AI-powered stock market analysis platform. LSTM predictions, real-time NLP sentiment analysis, and 124+ NEPSE stock coverage.
            </p>
          </div>
          <div>
            <h4 className="text-slate-900 font-semibold mb-4 text-sm">Platform</h4>
            <div className="space-y-2.5">
              <Link to="/stocks" className="block text-slate-500 hover:text-blue-600 text-sm transition-colors">Stock Analysis</Link>
              <Link to="/news" className="block text-slate-500 hover:text-blue-600 text-sm transition-colors">Live News</Link>
              <Link to="/ai" className="block text-slate-500 hover:text-blue-600 text-sm transition-colors">AI Assistant</Link>
              <Link to="/about" className="block text-slate-500 hover:text-blue-600 text-sm transition-colors">About Us</Link>
            </div>
          </div>
          <div>
            <h4 className="text-slate-900 font-semibold mb-4 text-sm">Connect</h4>
            <div className="space-y-2.5">
              <Link to="/contact" className="block text-slate-500 hover:text-blue-600 text-sm transition-colors">Contact Us</Link>
              <a href="https://github.com/Aabishkar2/nepse-data" target="_blank" rel="noreferrer" className="flex items-center gap-2 text-slate-500 hover:text-blue-600 text-sm transition-colors"><Github size={14} /> Data Source</a>
              <Link to="/login" className="block text-slate-500 hover:text-blue-600 text-sm transition-colors">Sign In</Link>
              <Link to="/signup" className="block text-slate-500 hover:text-blue-600 text-sm transition-colors">Create Account</Link>
            </div>
          </div>
        </div>
        <div className="mt-10 pt-6 border-t border-slate-100 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-slate-400 text-xs">© 2026 BhaavShare. Built with PyTorch, FastAPI & React.</p>
          <p className="text-slate-400 text-xs flex items-center gap-1">Made with <Heart size={12} className="text-red-500 fill-red-500" /> in Nepal</p>
        </div>
      </div>
    </footer>
  );
}
