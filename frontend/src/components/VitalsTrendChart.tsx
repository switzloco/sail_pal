"use client";

import React from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, Legend, AreaChart, Area 
} from 'recharts';

interface VitalData {
  time: string;
  hr: number | null;
  temp: number | null;
  spo2: number | null;
  bp: string | null;
}

export default function VitalsTrendChart({ data }: { data: VitalData[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-32 flex items-center justify-center bg-slate-50 rounded-xl border border-dashed border-slate-300 text-slate-400 italic text-sm">
        No trend data available
      </div>
    );
  }

  // Format time for XAxis (HH:MM)
  const formattedData = data.map(d => ({
    ...d,
    displayTime: new Date(d.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }));

  return (
    <div className="space-y-6">
      {/* Heart Rate & SpO2 Chart */}
      <div className="bg-white/80 backdrop-blur-md p-5 rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <h3 className="text-sm font-black text-slate-400 uppercase tracking-[0.2em] mb-4">Vitals: HR (BPM) & SpO2 (%)</h3>
        <div className="h-48 w-full -ml-6">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={formattedData}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="displayTime" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
              <YAxis axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
              <Tooltip 
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', fontSize: '14px' }}
              />
              <Legend verticalAlign="top" align="right" height={24} iconType="circle" wrapperStyle={{ fontSize: '12px', fontWeight: 'bold' }} />
              <Line 
                type="monotone" 
                dataKey="hr" 
                name="HR" 
                stroke="#ef4444" 
                strokeWidth={3} 
                dot={{ r: 4, fill: '#ef4444', strokeWidth: 2, stroke: '#fff' }} 
                activeDot={{ r: 6 }} 
              />
              <Line 
                type="monotone" 
                dataKey="spo2" 
                name="SpO2" 
                stroke="#0ea5e9" 
                strokeWidth={3} 
                dot={{ r: 4, fill: '#0ea5e9', strokeWidth: 2, stroke: '#fff' }} 
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Temperature Chart */}
      <div className="bg-white/80 backdrop-blur-md p-5 rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <h3 className="text-sm font-black text-slate-400 uppercase tracking-[0.2em] mb-4">Body Temperature (°C)</h3>
        <div className="h-48 w-full -ml-6">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={formattedData}>
              <defs>
                <linearGradient id="colorTemp" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
              <XAxis dataKey="displayTime" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
              <YAxis domain={['auto', 'auto']} axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
              <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', fontSize: '14px' }} />
              <Area 
                type="monotone" 
                dataKey="temp" 
                name="Temp" 
                stroke="#f59e0b" 
                fillOpacity={1} 
                fill="url(#colorTemp)" 
                strokeWidth={3} 
                dot={{ r: 4, fill: '#f59e0b', strokeWidth: 2, stroke: '#fff' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
