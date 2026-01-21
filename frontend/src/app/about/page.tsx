import { Metadata } from 'next'
import Link from 'next/link'
import Image from 'next/image'
import {
  BarChart3, Shield, Zap, Bot, LineChart, TrendingUp,
  CheckCircle, ArrowRight, Clock, Users, Target, Lock
} from 'lucide-react'
import { Header } from '@/components/Header'
import { Footer } from '@/components/Footer'

export const metadata: Metadata = {
  title: 'About ArthaQuant - Algorithmic Trading Platform for Indian Markets',
  description: 'Learn about ArthaQuant, the leading algorithmic trading platform for Indian retail traders. Discover our features, how it works, and why traders choose us for automated trading.',
  keywords: ['algorithmic trading', 'algo trading', 'indian stock market', 'automated trading', 'NSE', 'BSE', 'trading platform'],
  openGraph: {
    title: 'About ArthaQuant - Algorithmic Trading Made Simple',
    description: 'Discover how ArthaQuant empowers Indian traders with automated trading strategies, risk management, and professional-grade execution.',
    type: 'website',
  },
}

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-gray-950">
      <Header />

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-gray-50 to-white dark:from-gray-900 dark:to-gray-950 py-20">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6">
            Empowering Indian Traders with
            <span className="text-primary"> Algorithmic Intelligence</span>
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
            ArthaQuant bridges the gap between sophisticated trading strategies
            and everyday retail traders in Indian markets. No coding required,
            professional-grade results.
          </p>
        </div>
      </section>

      {/* Platform Features */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">Platform Features</h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Everything you need to automate your trading journey
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              icon={<Bot className="h-8 w-8 text-primary" />}
              title="Automated Execution"
              description="Set it and forget it. Our platform executes trades automatically based on your subscribed strategies, ensuring you never miss an opportunity."
            />
            <FeatureCard
              icon={<Shield className="h-8 w-8 text-primary" />}
              title="Advanced Risk Management"
              description="Built-in stop-loss, maximum drawdown limits, daily loss caps, and an emergency kill switch to protect your capital."
            />
            <FeatureCard
              icon={<LineChart className="h-8 w-8 text-primary" />}
              title="Strategy Backtesting"
              description="Test strategies against historical data before going live. Understand performance metrics, drawdowns, and expected returns."
            />
            <FeatureCard
              icon={<Zap className="h-8 w-8 text-primary" />}
              title="Low-Latency Execution"
              description="Direct broker integration ensures fast order execution with real-time market data from leading Indian brokers."
            />
            <FeatureCard
              icon={<Target className="h-8 w-8 text-primary" />}
              title="Curated Strategies"
              description="Access professionally developed trading strategies with proven track records. Choose from trend-following, mean-reversion, and more."
            />
            <FeatureCard
              icon={<Lock className="h-8 w-8 text-primary" />}
              title="Secure & Transparent"
              description="Your broker credentials are never stored. OAuth-based authentication ensures your account remains secure."
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-gray-50 dark:bg-gray-900/50 py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">How It Works</h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Get started in minutes with our simple 4-step process
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <StepCard
              step="1"
              title="Create Account"
              description="Sign up for free and complete your profile. No credit card required to start."
            />
            <StepCard
              step="2"
              title="Connect Broker"
              description="Securely link your existing broker account using OAuth. We support Fyers and more brokers coming soon."
            />
            <StepCard
              step="3"
              title="Choose Strategy"
              description="Browse our curated strategies, backtest them with historical data, and pick the ones that match your goals."
            />
            <StepCard
              step="4"
              title="Go Live"
              description="Allocate capital, set your risk parameters, and toggle ON. Watch your strategy execute trades automatically."
            />
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl font-bold mb-6">Why Traders Choose ArthaQuant</h2>
              <div className="space-y-4">
                <BenefitItem text="No coding or technical skills required" />
                <BenefitItem text="Professionally developed and tested strategies" />
                <BenefitItem text="Real-time monitoring and notifications" />
                <BenefitItem text="Transparent performance metrics and reporting" />
                <BenefitItem text="Paper trading mode to test without risk" />
                <BenefitItem text="Dedicated support for all your questions" />
                <BenefitItem text="Regular strategy updates and improvements" />
                <BenefitItem text="Competitive pricing with no hidden fees" />
              </div>
            </div>
            <div className="bg-gradient-to-br from-primary/10 to-primary/5 rounded-2xl p-8">
              <div className="grid grid-cols-2 gap-6">
                <StatCard value="10K+" label="Trades Executed" />
                <StatCard value="99.9%" label="Uptime" />
                <StatCard value="<50ms" label="Avg. Execution" />
                <StatCard value="24/7" label="Monitoring" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Supported Brokers */}
      <section className="bg-gray-50 dark:bg-gray-900/50 py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">Supported Brokers</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-12 max-w-2xl mx-auto">
            Connect your existing broker account seamlessly. We're constantly adding support for more brokers.
          </p>
          <div className="flex flex-wrap justify-center items-center gap-8">
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="text-2xl font-bold text-green-600">Fyers</div>
              <p className="text-sm text-gray-500 mt-1">Available Now</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 opacity-60">
              <div className="text-2xl font-bold text-gray-400">Zerodha</div>
              <p className="text-sm text-gray-500 mt-1">Coming Soon</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 opacity-60">
              <div className="text-2xl font-bold text-gray-400">Angel One</div>
              <p className="text-sm text-gray-500 mt-1">Coming Soon</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 opacity-60">
              <div className="text-2xl font-bold text-gray-400">Upstox</div>
              <p className="text-sm text-gray-500 mt-1">Coming Soon</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Automate Your Trading?</h2>
          <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-2xl mx-auto">
            Join thousands of traders who have already taken their trading to the next level.
            Start with paper trading - no risk, no commitment.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-primary text-white rounded-lg hover:bg-primary/90 font-semibold"
            >
              Get Started Free <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              href="/blog"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 font-semibold"
            >
              Read Our Blog
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="p-6 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 hover:shadow-lg transition-shadow">
      <div className="mb-4 p-3 bg-primary/10 rounded-lg w-fit">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400">{description}</p>
    </div>
  )
}

function StepCard({
  step,
  title,
  description,
}: {
  step: string
  title: string
  description: string
}) {
  return (
    <div className="text-center">
      <div className="w-14 h-14 rounded-full bg-primary text-white text-2xl font-bold flex items-center justify-center mx-auto mb-4">
        {step}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400 text-sm">{description}</p>
    </div>
  )
}

function BenefitItem({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-3">
      <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
      <span className="text-gray-700 dark:text-gray-300">{text}</span>
    </div>
  )
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 text-center">
      <div className="text-3xl font-bold text-primary">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  )
}
