import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const PriceHistoryChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="no-data" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-dim)', background: 'var(--glass)', borderRadius: '12px' }}>
        No price history available for this product yet.
      </div>
    );
  }

  const chartData = data.map(item => ({
    date: new Date(item.recorded_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
    price: item.price,
  })).reverse();

  return (
    <div className="price-history-chart" style={{ width: '100%', height: 350, marginTop: '1.5rem' }}>
      <h3 style={{ color: 'white', marginBottom: '1.5rem', fontSize: '1.1rem', fontWeight: '700' }}>Price Trend</h3>
      <ResponsiveContainer>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="date"
            stroke="var(--text-dim)"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="var(--text-dim)"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `₹${value}`}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(20, 20, 25, 0.9)',
              border: '1px solid var(--glass-border)',
              borderRadius: '12px',
              color: 'white'
            }}
            itemStyle={{ color: 'var(--primary)' }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="var(--primary)"
            strokeWidth={3}
            dot={{ fill: 'var(--primary)', strokeWidth: 2, r: 4, stroke: '#fff' }}
            activeDot={{ r: 6, strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default PriceHistoryChart;
