import React, { useEffect, useState } from 'react';
import { SecureAPI } from '../lib/secureApi';

interface RevenueData {
    property_id: string;
    total_revenue: number;
    currency: string;
    reservations_count: number;
}

interface RevenueSummaryProps {
    propertyId?: string;
    propertyName?: string; // both clients have a prop-001, so the id alone is ambiguous
    month?: number; // 1-12; with year, shows that month instead of all time
    year?: number;
    showRaw?: boolean;
}

const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'];

export const RevenueSummary: React.FC<RevenueSummaryProps> = ({ propertyId = 'prop-001', propertyName, month, year, showRaw }) => {
    const [data, setData] = useState<RevenueData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        // Set when the property changes before this response arrives, so a slow
        // answer for the previous property can't overwrite the current one.
        let ignore = false;

        const fetchRevenue = async () => {
            setLoading(true);
            setError(''); // a previous failure must not stick to every later property
            try {
                // Use SecureAPI to handle authentication automatically.
                // The tenant always comes from the login token on the server.
                const response = await SecureAPI.getDashboardSummary(propertyId, {
                    timestamp: Date.now(),
                    month,
                    year
                });
                if (!ignore) setData(response);
            } catch (err) {
                if (!ignore) setError('Failed to load revenue data');
                console.error(err);
            } finally {
                if (!ignore) setLoading(false);
            }
        };

        fetchRevenue();
        return () => { ignore = true; };
    }, [propertyId, month, year]);

    if (loading) {
        return (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                <div className="animate-pulse space-y-4">
                    <div className="h-4 bg-gray-100 rounded w-1/4"></div>
                    <div className="h-8 bg-gray-100 rounded w-1/2"></div>
                    <div className="flex gap-4 pt-4">
                        <div className="h-12 bg-gray-100 rounded flex-1"></div>
                        <div className="h-12 bg-gray-100 rounded flex-1"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) return <div className="p-4 text-red-500 bg-red-50 rounded-lg">{error}</div>;
    if (!data) return null;

    // The API already rounds to cents (Decimal, half-up). Don't round again in
    // floating point here: Math.round(x * 100) / 100 mis-rounds values like 1.005.
    const displayTotal = data.total_revenue;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow duration-300">
            {showRaw && (
                <div className="p-3 bg-gray-50 text-xs font-mono border-b border-gray-100 overflow-auto max-h-32">
                    <strong className="block mb-1 text-gray-500 uppercase tracking-wider text-[10px]">Raw API Response</strong>
                    <pre className="text-gray-700">{JSON.stringify(data, null, 2)}</pre>
                </div>
            )}

            <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
                            Total Revenue · {month && year ? `${MONTH_NAMES[month - 1]} ${year}` : 'All time'}
                        </h2>
                        <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-3xl font-bold text-gray-900 tracking-tight">
                                {data.currency} {displayTotal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                    <div>
                        <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Property</p>
                        <p className="text-sm font-semibold text-gray-700 mt-1">
                            {propertyName && <span>{propertyName} · </span>}
                            <span className="font-mono">{data.property_id}</span>
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Reservations</p>
                        <p className="text-sm font-semibold text-gray-700 mt-1">{data.reservations_count} <span className="font-normal text-gray-400">bookings</span></p>
                    </div>
                </div>

                {/* Precision Warning Area */}
                <div className="mt-4 h-6">
                    {Math.abs(data.total_revenue - displayTotal) > 0.000001 && showRaw && (
                        <div className="flex items-center text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
                            <svg className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            Precision Mismatch Detected
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
