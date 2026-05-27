import React, { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import './SearchAnalytics.css';

const COLORS = ['#8b5cf6', '#ec4899', '#10b981', '#f59e0b', '#3b82f6', '#ef4444'];

const SearchAnalytics = ({ products }) => {
    const analyticsData = useMemo(() => {
        if (!products || products.length === 0) return null;

        const platforms = {};

        products.forEach(p => {
            const pf = p.platform || 'Unknown';
            if (!platforms[pf]) {
                platforms[pf] = { name: pf, count: 0, totalPrice: 0, totalRating: 0, ratingCount: 0 };
            }
            platforms[pf].count += 1;
            if (p.price) platforms[pf].totalPrice += p.price;
            if (p.rating) {
                platforms[pf].totalRating += p.rating;
                platforms[pf].ratingCount += 1;
            }
        });

        return Object.values(platforms).map(p => ({
            name: p.name,
            Count: p.count,
            'Avg Price': p.totalPrice / p.count,
            'Avg Rating': p.ratingCount > 0 ? p.totalRating / p.ratingCount : 0
        }));
    }, [products]);

    if (!analyticsData) return null;

    return (
        <div className="search-analytics">
            <div className="sa-header">
                <h3>🔍 Search Insights</h3>
                <p>Real-time analytics for "{products.length}" results</p>
            </div>

            <div className="sa-grid">
                <div className="sa-card">
                    <h4>Products by Platform</h4>
                    <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={analyticsData}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--glass-border)" />
                            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-dim)', fontSize: 12 }} />
                            <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--text-dim)', fontSize: 12 }} />
                            <Tooltip
                                contentStyle={{ background: 'var(--bg-color)', border: '1px solid var(--glass-border)', borderRadius: '12px' }}
                                itemStyle={{ color: 'var(--text-main)' }}
                            />
                            <Bar dataKey="Count" radius={[6, 6, 0, 0]}>
                                {analyticsData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="sa-card">
                    <h4>Price Comparison (Avg)</h4>
                    <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={analyticsData}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--glass-border)" />
                            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-dim)', fontSize: 12 }} />
                            <YAxis axisLine={false} tickLine={false} tick={{ fill: 'var(--text-dim)', fontSize: 12 }} />
                            <Tooltip
                                formatter={(val) => `₹${val.toFixed(0)}`}
                                contentStyle={{ background: 'var(--bg-color)', border: '1px solid var(--glass-border)', borderRadius: '12px' }}
                            />
                            <Bar dataKey="Avg Price" fill="var(--primary)" radius={[6, 6, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="sa-card">
                    <h4>Rating Analysis</h4>
                    <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={analyticsData}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--glass-border)" />
                            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-dim)', fontSize: 12 }} />
                            <YAxis domain={[0, 5]} axisLine={false} tickLine={false} tick={{ fill: 'var(--text-dim)', fontSize: 12 }} />
                            <Tooltip
                                formatter={(val) => `${val.toFixed(1)} ★`}
                                contentStyle={{ background: 'var(--bg-color)', border: '1px solid var(--glass-border)', borderRadius: '12px' }}
                            />
                            <Bar dataKey="Avg Rating" fill="var(--accent)" radius={[6, 6, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

export default SearchAnalytics;
