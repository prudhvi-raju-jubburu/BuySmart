import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const ComparisonChart = ({ products }) => {
    if (!products || products.length === 0) {
        return null;
    }

    const data = products.map(p => ({
        name: p.name.length > 20 ? p.name.substring(0, 17) + '...' : p.name,
        Price: p.price,
        Rating: p.rating
    }));

    return (
        <div className="comparison-chart-container" style={{ padding: '1rem' }}>
            <div style={{ marginBottom: '3rem' }}>
                <h3 style={{ color: 'white', marginBottom: '1.5rem', fontSize: '1.1rem', fontWeight: '700' }}>Price Comparison (₹)</h3>
                <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer>
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis dataKey="name" stroke="var(--text-dim)" fontSize={11} tickLine={false} axisLine={false} />
                            <YAxis stroke="var(--text-dim)" fontSize={11} tickLine={false} axisLine={false} />
                            <Tooltip
                                contentStyle={{ background: 'rgba(20, 20, 25, 0.9)', border: '1px solid var(--glass-border)', borderRadius: '12px' }}
                                itemStyle={{ color: 'var(--primary)' }}
                            />
                            <Bar dataKey="Price" fill="var(--primary)" radius={[6, 6, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div>
                <h3 style={{ color: 'white', marginBottom: '1.5rem', fontSize: '1.1rem', fontWeight: '700' }}>Rating Comparison (1-5)</h3>
                <div style={{ width: '100%', height: 300 }}>
                    <ResponsiveContainer>
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis dataKey="name" stroke="var(--text-dim)" fontSize={11} tickLine={false} axisLine={false} />
                            <YAxis domain={[0, 5]} stroke="var(--text-dim)" fontSize={11} tickLine={false} axisLine={false} />
                            <Tooltip
                                contentStyle={{ background: 'rgba(20, 20, 25, 0.9)', border: '1px solid var(--glass-border)', borderRadius: '12px' }}
                                itemStyle={{ color: 'var(--secondary)' }}
                            />
                            <Bar dataKey="Rating" fill="var(--secondary)" radius={[6, 6, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

export default ComparisonChart;
