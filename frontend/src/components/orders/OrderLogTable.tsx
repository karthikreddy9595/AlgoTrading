"use client";

import { useState, useEffect } from "react";
import { format } from "date-fns";
import { orderLogsApi } from "@/lib/api";

interface OrderLog {
  id: string;
  subscription_id: string;
  symbol: string;
  exchange: string;
  order_type: string;
  transaction_type: string;
  quantity: number;
  price: number | null;
  event_type: string;
  is_dry_run: boolean;
  is_test_order: boolean;
  success: boolean | null;
  broker_order_id: string | null;
  broker_name: string | null;
  error_message: string | null;
  strategy_name: string | null;
  created_at: string;
}

interface OrderLogTableProps {
  subscriptionId?: string;
  className?: string;
}

export default function OrderLogTable({ subscriptionId, className = "" }: OrderLogTableProps) {
  const [logs, setLogs] = useState<OrderLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    eventType: "",
    isDryRun: "",
    isTestOrder: "",
    success: "",
  });
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 50;

  useEffect(() => {
    fetchOrderLogs();
  }, [subscriptionId, filters, page]);

  const fetchOrderLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = {
        page: page,
        page_size: pageSize,
      };

      if (subscriptionId) {
        params.subscription_id = subscriptionId;
      }

      if (filters.eventType) {
        params.event_type = filters.eventType;
      }

      if (filters.isDryRun !== "") {
        params.is_dry_run = filters.isDryRun === "true";
      }

      if (filters.isTestOrder !== "") {
        params.is_test_order = filters.isTestOrder === "true";
      }

      if (filters.success !== "") {
        params.success = filters.success === "true";
      }

      const data = await orderLogsApi.getOrderLogs(params);
      setLogs(data.logs);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to fetch order logs:", err);
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const getEventTypeBadge = (eventType: string) => {
    const badges: Record<string, { bg: string; text: string }> = {
      generated: { bg: "bg-blue-100 dark:bg-blue-900", text: "text-blue-800 dark:text-blue-100" },
      dry_run: { bg: "bg-purple-100 dark:bg-purple-900", text: "text-purple-800 dark:text-purple-100" },
      submitted: { bg: "bg-yellow-100 dark:bg-yellow-900", text: "text-yellow-800 dark:text-yellow-100" },
      placed: { bg: "bg-green-100 dark:bg-green-900", text: "text-green-800 dark:text-green-100" },
      filled: { bg: "bg-emerald-100 dark:bg-emerald-900", text: "text-emerald-800 dark:text-emerald-100" },
      rejected: { bg: "bg-red-100 dark:bg-red-900", text: "text-red-800 dark:text-red-100" },
      failed: { bg: "bg-red-100 dark:bg-red-900", text: "text-red-800 dark:text-red-100" },
    };

    const style = badges[eventType] || { bg: "bg-gray-100 dark:bg-gray-700", text: "text-gray-800 dark:text-gray-100" };

    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${style.bg} ${style.text}`}>
        {eventType.replace("_", " ").toUpperCase()}
      </span>
    );
  };

  const getSuccessBadge = (success: boolean | null) => {
    if (success === null) {
      return <span className="px-2 py-1 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-100">PENDING</span>;
    }
    if (success) {
      return <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-100">SUCCESS</span>;
    }
    return <span className="px-2 py-1 rounded text-xs font-medium bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-100">FAILED</span>;
  };

  if (loading && logs.length === 0) {
    return <div className="text-center py-8 text-gray-400">Loading order logs...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-800 dark:text-red-200">{error}</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Event Type</label>
          <select
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            value={filters.eventType}
            onChange={(e) => {
              setFilters({ ...filters, eventType: e.target.value });
              setPage(1);
            }}
          >
            <option value="">All Events</option>
            <option value="generated">Generated</option>
            <option value="dry_run">Dry Run</option>
            <option value="submitted">Submitted</option>
            <option value="placed">Placed</option>
            <option value="filled">Filled</option>
            <option value="rejected">Rejected</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Mode</label>
          <select
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            value={filters.isDryRun}
            onChange={(e) => {
              setFilters({ ...filters, isDryRun: e.target.value });
              setPage(1);
            }}
          >
            <option value="">All Modes</option>
            <option value="true">Dry Run</option>
            <option value="false">Live</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Test Orders</label>
          <select
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            value={filters.isTestOrder}
            onChange={(e) => {
              setFilters({ ...filters, isTestOrder: e.target.value });
              setPage(1);
            }}
          >
            <option value="">All Orders</option>
            <option value="true">Test Only</option>
            <option value="false">Real Only</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Status</label>
          <select
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            value={filters.success}
            onChange={(e) => {
              setFilters({ ...filters, success: e.target.value });
              setPage(1);
            }}
          >
            <option value="">All Status</option>
            <option value="true">Success</option>
            <option value="false">Failed</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 dark:bg-gray-800">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Time</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Symbol</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Type</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Qty</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700 dark:text-gray-300">Price</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Event</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Status</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Broker ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700 dark:text-gray-300">Flags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                  No order logs found. Orders will appear here once your strategy starts generating signals.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="px-4 py-3 text-gray-700 dark:text-gray-300 whitespace-nowrap">
                    {format(new Date(log.created_at), "MMM dd, HH:mm:ss")}
                  </td>
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                    {log.symbol}
                    <span className="ml-1 text-xs text-gray-500 dark:text-gray-400">({log.exchange})</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-medium ${log.transaction_type === "BUY" ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
                      {log.transaction_type}
                    </span>
                    <span className="ml-1 text-xs text-gray-500 dark:text-gray-400">{log.order_type}</span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">{log.quantity}</td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {log.price ? `₹${log.price.toFixed(2)}` : "-"}
                  </td>
                  <td className="px-4 py-3">{getEventTypeBadge(log.event_type)}</td>
                  <td className="px-4 py-3">{getSuccessBadge(log.success)}</td>
                  <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400 font-mono">
                    {log.broker_order_id || "-"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      {log.is_dry_run && (
                        <span className="px-1.5 py-0.5 rounded text-xs bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-200">DRY</span>
                      )}
                      {log.is_test_order && (
                        <span className="px-1.5 py-0.5 rounded text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200">TEST</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} logs
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-300"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page * pageSize >= total}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-gray-700 dark:text-gray-300"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
