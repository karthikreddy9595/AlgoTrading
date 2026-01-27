"use client";

import { useState, useEffect } from "react";
import OrderLogTable from "@/components/orders/OrderLogTable";
import BrokerTestOrder from "@/components/orders/BrokerTestOrder";
import { brokerApi } from "@/lib/api";

interface BrokerConnection {
  id: string;
  broker: string;
  is_active: boolean;
}

export default function OrderTestPage() {
  const [activeTab, setActiveTab] = useState<"logs" | "test">("logs");
  const [connections, setConnections] = useState<BrokerConnection[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBrokerConnections();
  }, []);

  const fetchBrokerConnections = async () => {
    try {
      const connections = await brokerApi.getConnections();
      setConnections(connections.filter((conn: BrokerConnection) => conn.is_active));
    } catch (error) {
      console.error("Failed to fetch broker connections:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Order Testing & Monitoring</h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Test broker connectivity and monitor all order execution events
          </p>
        </div>

        {/* Info Banner */}
        <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-100">How to Test Order Execution</h3>
              <ul className="mt-2 text-sm text-blue-800 dark:text-blue-200 space-y-1">
                <li>• <strong>Dry-Run Mode:</strong> Enable on your strategy to simulate orders without sending to broker</li>
                <li>• <strong>Order Logs:</strong> View all order events including generation, submission, and broker responses</li>
                <li>• <strong>Test Order:</strong> Place a real test order with minimal quantity to verify broker integration</li>
                <li>• <strong>Event Types:</strong> Generated → Submitted → Placed → Filled (or Rejected/Failed)</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab("logs")}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === "logs"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600"
                }`}
              >
                Order Logs
              </button>
              <button
                onClick={() => setActiveTab("test")}
                className={`py-4 px-1 border-b-2 font-medium text-sm ${
                  activeTab === "test"
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600"
                }`}
              >
                Test Broker
              </button>
            </nav>
          </div>
        </div>

        {/* Content */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
          {activeTab === "logs" && (
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Order Execution Logs
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Track every order event to verify if orders are being sent to your broker.
                Look for "PLACED" events with broker order IDs to confirm successful execution.
              </p>
              <OrderLogTable />
            </div>
          )}

          {activeTab === "test" && (
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
                Test Broker Connection
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
                Place a small test order to verify your broker integration is working correctly.
                The order will appear in your broker's order book and in the order logs.
              </p>
              {loading ? (
                <div className="text-center py-8 text-gray-400">Loading broker connections...</div>
              ) : (
                <BrokerTestOrder
                  connections={connections}
                  onSuccess={() => setActiveTab("logs")}
                />
              )}
            </div>
          )}
        </div>

        {/* Documentation */}
        <div className="mt-8 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Understanding Order Events
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Event Types:</h4>
              <ul className="space-y-2 text-gray-600 dark:text-gray-400">
                <li><span className="font-mono text-xs bg-blue-100 dark:bg-blue-900 px-2 py-0.5 rounded">GENERATED</span> - Strategy created an order signal</li>
                <li><span className="font-mono text-xs bg-purple-100 dark:bg-purple-900 px-2 py-0.5 rounded">DRY_RUN</span> - Order simulated (not sent to broker)</li>
                <li><span className="font-mono text-xs bg-yellow-100 dark:bg-yellow-900 px-2 py-0.5 rounded">SUBMITTED</span> - Order sent to broker</li>
                <li><span className="font-mono text-xs bg-green-100 dark:bg-green-900 px-2 py-0.5 rounded">PLACED</span> - Broker confirmed order placement</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Troubleshooting:</h4>
              <ul className="space-y-2 text-gray-600 dark:text-gray-400">
                <li>• If you see only <strong>GENERATED</strong> events, check if dry-run mode is enabled</li>
                <li>• If you see <strong>SUBMITTED</strong> but no <strong>PLACED</strong>, check broker connection</li>
                <li>• <strong>REJECTED</strong> events indicate broker rejected the order (check error message)</li>
                <li>• <strong>FAILED</strong> events indicate technical errors (API issues, auth problems, etc.)</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
