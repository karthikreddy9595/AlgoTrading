"use client";

import { useState } from "react";
import { orderLogsApi } from "@/lib/api";

interface BrokerConnection {
  id: string;
  broker: string;
  is_active: boolean;
}

interface BrokerTestOrderProps {
  connections: BrokerConnection[];
  onSuccess?: () => void;
}

export default function BrokerTestOrder({ connections, onSuccess }: BrokerTestOrderProps) {
  const [formData, setFormData] = useState({
    broker_connection_id: connections[0]?.id || "",
    symbol: "RELIANCE",
    exchange: "NSE",
    quantity: 1,
    order_type: "LIMIT",
    transaction_type: "BUY",
    price: "",
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
    broker_order_id?: string;
    error?: string;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const data = await orderLogsApi.testBrokerOrder({
        broker_connection_id: formData.broker_connection_id,
        symbol: formData.symbol,
        exchange: formData.exchange,
        transaction_type: formData.transaction_type as 'BUY' | 'SELL',
        quantity: formData.quantity,
        order_type: formData.order_type as 'MARKET' | 'LIMIT',
        price: formData.price ? parseFloat(formData.price) : undefined,
      });

      setResult(data);

      if (data.success && onSuccess) {
        onSuccess();
      }
    } catch (err: any) {
      console.error("Test order failed:", err);
      setResult({
        success: false,
        message: "Failed to place test order",
        error: err.response?.data?.detail || err.message || "An error occurred",
      });
    } finally {
      setLoading(false);
    }
  };

  if (connections.length === 0) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <p className="text-yellow-800 dark:text-yellow-200">
          No active broker connections found. Please connect a broker first.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Warning */}
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <svg className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <h3 className="font-semibold text-red-800 dark:text-red-200">Real Order Warning</h3>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">
              This will place a REAL order with your broker using real money. Use small quantities (1-10 shares) for testing only.
              Cancel the order immediately after verification if needed.
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Broker Connection
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              value={formData.broker_connection_id}
              onChange={(e) => setFormData({ ...formData, broker_connection_id: e.target.value })}
              required
            >
              {connections.map((conn) => (
                <option key={conn.id} value={conn.id}>
                  {conn.broker} {conn.is_active ? "(Active)" : "(Inactive)"}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Symbol
            </label>
            <input
              type="text"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              value={formData.symbol}
              onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
              placeholder="RELIANCE"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Exchange
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              value={formData.exchange}
              onChange={(e) => setFormData({ ...formData, exchange: e.target.value })}
            >
              <option value="NSE">NSE</option>
              <option value="BSE">BSE</option>
              <option value="NFO">NFO</option>
              <option value="MCX">MCX</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Quantity (1-10)
            </label>
            <input
              type="number"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              value={formData.quantity}
              onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) })}
              min="1"
              max="10"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Order Type
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              value={formData.order_type}
              onChange={(e) => setFormData({ ...formData, order_type: e.target.value })}
            >
              <option value="MARKET">MARKET</option>
              <option value="LIMIT">LIMIT</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Transaction Type
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              value={formData.transaction_type}
              onChange={(e) => setFormData({ ...formData, transaction_type: e.target.value })}
            >
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </div>

          {formData.order_type === "LIMIT" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Price (Leave empty for current market price)
              </label>
              <input
                type="number"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                placeholder="Auto-fill at market price"
              />
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Placing Test Order..." : "Place Test Order"}
        </button>
      </form>

      {/* Result */}
      {result && (
        <div className={`border rounded-lg p-4 ${
          result.success
            ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800"
            : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
        }`}>
          <div className="flex items-start gap-3">
            {result.success ? (
              <svg className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
            <div className="flex-1">
              <h3 className={`font-semibold ${
                result.success
                  ? "text-green-800 dark:text-green-200"
                  : "text-red-800 dark:text-red-200"
              }`}>
                {result.success ? "Test Order Successful!" : "Test Order Failed"}
              </h3>
              <p className={`text-sm mt-1 ${
                result.success
                  ? "text-green-700 dark:text-green-300"
                  : "text-red-700 dark:text-red-300"
              }`}>
                {result.message}
              </p>
              {result.broker_order_id && (
                <p className="text-xs mt-2 font-mono text-gray-600 dark:text-gray-400">
                  Broker Order ID: {result.broker_order_id}
                </p>
              )}
              {result.error && (
                <p className="text-xs mt-2 text-red-600 dark:text-red-400">
                  Error: {result.error}
                </p>
              )}
              {result.success && (
                <div className="mt-3 text-sm text-yellow-700 dark:text-yellow-300 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded p-2">
                  ⚠️ Don't forget to cancel this test order from your broker's order book if you don't want it to be executed!
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
