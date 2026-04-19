import React, { useState } from 'react';
import { Mail, MapPin, Phone, Send, CheckCircle, AlertTriangle, Github } from 'lucide-react';
import api from '../utils/api';

export default function ContactPage() {
  const [status, setStatus] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('sending');
    setErrorMsg('');
    try {
      await api.post('/contact', form);
      setStatus('sent');
      setForm({ name: '', email: '', subject: '', message: '' });
      setTimeout(() => setStatus(null), 4000);
    } catch (err) {
      setStatus('error');
      setErrorMsg(err?.response?.data?.detail || 'Could not deliver your message. Try again later.');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 pt-20 px-4 md:px-6 pb-12">
      <div className="max-w-5xl mx-auto pt-8">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Get In Touch</h1>
          <p className="text-slate-500 max-w-lg mx-auto">Have questions about BhaavShare or want to collaborate? We'd love to hear from you.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-10">
          {[
            { icon: <Mail size={20} />, title: "Email", detail: "hello@bhaavshare.com" },
            { icon: <MapPin size={20} />, title: "Location", detail: "Kathmandu, Nepal" },
            { icon: <Phone size={20} />, title: "Phone", detail: "+977 9843678924" },
            { icon: <Github size={20} />, title: "Data", detail: "Aabishkar2/nepse-data" },
          ].map((c, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 text-center hover:border-blue-200 transition card-hover">
              <div className="w-11 h-11 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">{c.icon}</div>
              <h3 className="text-slate-800 font-semibold text-sm">{c.title}</h3>
              <p className="text-slate-500 text-sm mt-1">{c.detail}</p>
            </div>
          ))}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-7 md:p-10 max-w-2xl mx-auto shadow-card relative">
          {status === 'sent' && (
            <div className="absolute inset-0 z-20 bg-white/95 flex flex-col items-center justify-center rounded-xl">
              <CheckCircle size={44} className="text-green-500 mb-3" />
              <p className="text-slate-900 font-bold text-lg">Message Sent!</p>
              <p className="text-slate-500 text-sm mt-1">We'll get back to you soon.</p>
            </div>
          )}
          <h2 className="text-lg font-bold text-slate-900 mb-5">Send a Message</h2>
          {status === 'error' && (
            <div className="flex items-center gap-2 p-3 mb-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              <AlertTriangle size={15} /> {errorMsg}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input type="text" placeholder="Your Name" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-blue-400 transition text-slate-800 placeholder-slate-400" />
              <input type="email" placeholder="Email Address" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                className="bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-blue-400 transition text-slate-800 placeholder-slate-400" />
            </div>
            <input type="text" placeholder="Subject" required value={form.subject} onChange={e => setForm({ ...form, subject: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-blue-400 transition text-slate-800 placeholder-slate-400" />
            <textarea rows={5} placeholder="Your message…" required value={form.message} onChange={e => setForm({ ...form, message: e.target.value })}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-blue-400 transition text-slate-800 placeholder-slate-400 resize-none" />
            <button type="submit" disabled={status === 'sending'}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-3 rounded-lg font-semibold transition-colors shadow-sm flex items-center justify-center gap-2 btn-press">
              <Send size={15} /> {status === 'sending' ? 'Sending…' : 'Send Message'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
