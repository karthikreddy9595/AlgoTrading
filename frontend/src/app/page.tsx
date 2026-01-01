import Link from 'next/link'
import { ArrowRight, BarChart3, Shield, Zap, TrendingUp } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white dark:from-gray-950 dark:to-gray-900">
      {/* Header */}
      <header className="border-b border-gray-200 dark:border-gray-800">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold">AlgoTrading</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="px-4 py-2 text-sm font-medium bg-primary text-white rounded-lg hover:bg-primary/90"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h1 className="text-5xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-6xl">
          Algorithmic Trading
          <br />
          <span className="text-primary">Made Simple</span>
        </h1>
        <p className="mt-6 text-lg leading-8 text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
          Subscribe to professionally curated trading strategies, allocate capital,
          and let our platform execute trades automatically. Focus on results,
          not the complexity.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link
            href="/register"
            className="flex items-center gap-2 px-6 py-3 text-sm font-semibold bg-primary text-white rounded-lg hover:bg-primary/90"
          >
            Start Trading <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="#features"
            className="px-6 py-3 text-sm font-semibold text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
          >
            Learn More
          </Link>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="container mx-auto px-4 py-20">
        <h2 className="text-3xl font-bold text-center mb-12">
          Why Choose AlgoTrading?
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          <FeatureCard
            icon={<BarChart3 className="h-10 w-10 text-primary" />}
            title="Curated Strategies"
            description="Access professionally developed trading strategies with proven track records. No coding required."
          />
          <FeatureCard
            icon={<Shield className="h-10 w-10 text-primary" />}
            title="Risk Management"
            description="Built-in safeguards including stop-loss, max drawdown limits, and a global kill switch."
          />
          <FeatureCard
            icon={<Zap className="h-10 w-10 text-primary" />}
            title="Fast Execution"
            description="Low-latency order execution with real-time market data from leading Indian brokers."
          />
        </div>
      </section>

      {/* How It Works */}
      <section className="bg-gray-50 dark:bg-gray-900/50 py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">How It Works</h2>
          <div className="grid md:grid-cols-4 gap-8">
            <StepCard
              step="1"
              title="Sign Up"
              description="Create your account and connect your broker"
            />
            <StepCard
              step="2"
              title="Choose Strategy"
              description="Browse and select from our curated strategies"
            />
            <StepCard
              step="3"
              title="Allocate Capital"
              description="Set your capital and risk parameters"
            />
            <StepCard
              step="4"
              title="Go Live"
              description="Toggle ON and watch your strategy execute"
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container mx-auto px-4 py-20 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to Start?</h2>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          Try your first strategy free. No credit card required.
        </p>
        <Link
          href="/register"
          className="inline-flex items-center gap-2 px-8 py-4 text-lg font-semibold bg-primary text-white rounded-lg hover:bg-primary/90"
        >
          Create Free Account <ArrowRight className="h-5 w-5" />
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-800 py-8">
        <div className="container mx-auto px-4 text-center text-sm text-gray-500">
          <p>&copy; 2024 AlgoTrading Platform. All rights reserved.</p>
          <p className="mt-2">
            Trading involves risk. Past performance is not indicative of future results.
          </p>
        </div>
      </footer>
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
    <div className="p-6 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
      <div className="mb-4">{icon}</div>
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
      <div className="w-12 h-12 rounded-full bg-primary text-white text-xl font-bold flex items-center justify-center mx-auto mb-4">
        {step}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400 text-sm">{description}</p>
    </div>
  )
}
