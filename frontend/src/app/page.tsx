import Link from 'next/link'
import Image from 'next/image'
import {
  ArrowRight,
  BarChart3,
  Shield,
  Zap,
  Mail,
  Twitter,
  Linkedin,
  Youtube,
  Instagram,
  TrendingUp,
  Lock,
  Target,
  LineChart,
  Cpu,
  CheckCircle2,
  Play,
  ChevronRight,
  Users,
  Award,
  Globe,
} from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-gray-900 overflow-hidden">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-200">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Image src="/logo.png" alt="ArthaQuant" width={40} height={40} className="h-10 w-10" />
            <span className="text-xl font-bold bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent">ArthaQuant</span>
          </div>
          <nav className="hidden md:flex items-center gap-8">
            <Link href="/about" className="text-sm text-gray-600 hover:text-purple-600 transition-colors">
              About
            </Link>
            <Link href="/blog" className="text-sm text-gray-600 hover:text-purple-600 transition-colors">
              Blog
            </Link>
            <Link href="#features" className="text-sm text-gray-600 hover:text-purple-600 transition-colors">
              Features
            </Link>
            <Link href="#how-it-works" className="text-sm text-gray-600 hover:text-purple-600 transition-colors">
              How It Works
            </Link>
          </nav>
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-purple-600 transition-colors"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="px-5 py-2.5 text-sm font-semibold bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-full hover:shadow-lg hover:shadow-purple-500/25 transition-all"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative min-h-screen flex items-center pt-20">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-50 via-white to-yellow-50">
          {/* Animated gradient orbs */}
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-300/30 rounded-full blur-[128px] animate-pulse" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-yellow-300/30 rounded-full blur-[128px] animate-pulse delay-1000" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-r from-purple-200/20 to-yellow-200/20 rounded-full blur-[128px]" />
        </div>

        {/* Grid Pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(147,51,234,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(147,51,234,0.03)_1px,transparent_1px)] bg-[size:64px_64px]" />

        <div className="container mx-auto px-4 relative z-10">
          <div className="max-w-5xl mx-auto text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-100 border border-purple-200 mb-8">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm text-purple-700">Now live with Fyers broker integration</span>
            </div>

            {/* Main Headline */}
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
              <span className="text-gray-900">
                The Future of
              </span>
              <br />
              <span className="bg-gradient-to-r from-purple-600 via-purple-500 to-yellow-500 bg-clip-text text-transparent">
                Algorithmic Trading
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-10">
              Harness the power of automated trading strategies. Subscribe, allocate capital,
              and let AI-driven algorithms execute trades while you focus on what matters.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
              <Link
                href="/register"
                className="group flex items-center gap-2 px-8 py-4 text-lg font-semibold bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-full hover:shadow-2xl hover:shadow-purple-500/30 transition-all duration-300"
              >
                Start Trading Free
                <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="#how-it-works"
                className="flex items-center gap-2 px-8 py-4 text-lg font-semibold text-gray-700 border-2 border-gray-300 rounded-full hover:border-purple-400 hover:text-purple-600 transition-all"
              >
                <Play className="h-5 w-5" />
                Watch Demo
              </Link>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-3xl mx-auto">
              <StatItem value="10K+" label="Active Traders" />
              <StatItem value="50Cr+" label="Capital Managed" />
              <StatItem value="99.9%" label="Uptime" />
              <StatItem value="<10ms" label="Execution Speed" />
            </div>
          </div>
        </div>
      </section>

      {/* Trusted By Section */}
      <section className="py-16 border-y border-gray-200 bg-gray-50">
        <div className="container mx-auto px-4">
          <p className="text-center text-sm text-gray-500 mb-8">INTEGRATED WITH LEADING INDIAN BROKERS</p>
          <div className="flex flex-wrap items-center justify-center gap-12">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-green-100 to-green-200 flex items-center justify-center">
                <span className="font-bold text-green-600">F</span>
              </div>
              <span className="font-semibold text-gray-700">Fyers</span>
              <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">Active</span>
            </div>
            <div className="flex items-center gap-3 text-gray-400">
              <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                <span className="font-bold">Z</span>
              </div>
              <span className="font-semibold">Zerodha</span>
              <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">Coming Soon</span>
            </div>
            <div className="flex items-center gap-3 text-gray-400">
              <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                <span className="font-bold">A</span>
              </div>
              <span className="font-semibold">Angel One</span>
              <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">Coming Soon</span>
            </div>
            <div className="flex items-center gap-3 text-gray-400">
              <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                <span className="font-bold">U</span>
              </div>
              <span className="font-semibold">Upstox</span>
              <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">Coming Soon</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 relative bg-white">
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-purple-50/50 to-transparent" />
        <div className="container mx-auto px-4 relative z-10">
          <div className="text-center mb-16">
            <span className="inline-block px-4 py-1 rounded-full bg-purple-100 text-purple-700 text-sm font-medium mb-4">
              Features
            </span>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Everything You Need to
              <span className="bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent"> Trade Smarter</span>
            </h2>
            <p className="text-gray-600 max-w-2xl mx-auto">
              Professional-grade tools and strategies, now accessible to every retail trader
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              icon={<BarChart3 className="h-6 w-6" />}
              title="Curated Strategies"
              description="Access professionally developed trading strategies with proven track records. No coding required."
              gradient="from-purple-500 to-purple-600"
            />
            <FeatureCard
              icon={<Shield className="h-6 w-6" />}
              title="Advanced Risk Management"
              description="Built-in safeguards including stop-loss, max drawdown limits, position sizing, and emergency kill switch."
              gradient="from-red-500 to-orange-500"
            />
            <FeatureCard
              icon={<Zap className="h-6 w-6" />}
              title="Lightning Fast Execution"
              description="Sub-10ms order execution with real-time market data streams from leading Indian exchanges."
              gradient="from-yellow-500 to-amber-500"
            />
            <FeatureCard
              icon={<LineChart className="h-6 w-6" />}
              title="Comprehensive Backtesting"
              description="Test strategies against years of historical data before risking real capital. Understand performance metrics."
              gradient="from-green-500 to-emerald-500"
            />
            <FeatureCard
              icon={<Cpu className="h-6 w-6" />}
              title="Automated Execution"
              description="Set it and forget it. Our platform monitors markets 24/7 and executes trades based on your chosen strategies."
              gradient="from-blue-500 to-cyan-500"
            />
            <FeatureCard
              icon={<Lock className="h-6 w-6" />}
              title="Bank-Grade Security"
              description="Your credentials are encrypted. We never store broker passwords. OAuth-based secure authentication."
              gradient="from-pink-500 to-rose-500"
            />
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-24 bg-gradient-to-b from-gray-50 to-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <span className="inline-block px-4 py-1 rounded-full bg-yellow-100 text-yellow-700 text-sm font-medium mb-4">
              How It Works
            </span>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Start Trading in
              <span className="bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent"> 4 Simple Steps</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-4 gap-8 relative">
            {/* Connecting Line */}
            <div className="hidden md:block absolute top-16 left-[12.5%] right-[12.5%] h-0.5 bg-gradient-to-r from-purple-500 via-purple-400 to-yellow-500" />

            <StepCard
              step="01"
              title="Create Account"
              description="Sign up in seconds with email or Google. No credit card required to start."
              icon={<Users className="h-6 w-6" />}
            />
            <StepCard
              step="02"
              title="Connect Broker"
              description="Securely link your Fyers account using OAuth. Your credentials stay safe."
              icon={<Globe className="h-6 w-6" />}
            />
            <StepCard
              step="03"
              title="Choose Strategy"
              description="Browse our curated strategies, review backtests, and select what fits your goals."
              icon={<Target className="h-6 w-6" />}
            />
            <StepCard
              step="04"
              title="Go Live"
              description="Set your capital, risk limits, and toggle ON. Watch your strategy execute automatically."
              icon={<Zap className="h-6 w-6" />}
            />
          </div>
        </div>
      </section>

      {/* Platform Preview Section */}
      <section className="py-24 relative overflow-hidden bg-white">
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-200/40 rounded-full blur-[128px]" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-yellow-200/40 rounded-full blur-[128px]" />
        </div>

        <div className="container mx-auto px-4 relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <span className="inline-block px-4 py-1 rounded-full bg-green-100 text-green-700 text-sm font-medium mb-4">
                Platform Preview
              </span>
              <h2 className="text-4xl md:text-5xl font-bold mb-6">
                Powerful Dashboard,
                <br />
                <span className="bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent">
                  Simple Interface
                </span>
              </h2>
              <p className="text-gray-600 mb-8">
                Monitor your portfolio, track strategy performance, and manage risk - all from one intuitive dashboard.
              </p>

              <ul className="space-y-4">
                <FeatureListItem text="Real-time P&L tracking and position monitoring" />
                <FeatureListItem text="Detailed trade history and performance analytics" />
                <FeatureListItem text="One-click strategy activation and deactivation" />
                <FeatureListItem text="Customizable risk parameters per strategy" />
                <FeatureListItem text="Mobile-responsive design for trading on the go" />
              </ul>

              <div className="mt-8">
                <Link
                  href="/register"
                  className="inline-flex items-center gap-2 text-purple-600 font-medium hover:underline"
                >
                  Explore the platform
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </div>

            <div className="relative">
              {/* Dashboard Preview Image */}
              <div className="relative rounded-2xl overflow-hidden border border-gray-200 shadow-2xl shadow-purple-500/10">
                <img
                  src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=2070&q=80"
                  alt="Trading Dashboard"
                  className="w-full"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-white via-transparent to-transparent" />
              </div>

              {/* Floating Stats Card */}
              <div className="absolute -bottom-6 -left-6 bg-white border border-gray-200 rounded-xl p-4 shadow-xl">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                    <TrendingUp className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Today&apos;s P&L</p>
                    <p className="text-xl font-bold text-green-600">+₹12,450</p>
                  </div>
                </div>
              </div>

              {/* Floating Notification Card */}
              <div className="absolute -top-4 -right-4 bg-white border border-gray-200 rounded-xl p-3 shadow-xl">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <p className="text-sm text-gray-700">Strategy executing...</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-24 bg-gradient-to-b from-gray-50 to-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <span className="inline-block px-4 py-1 rounded-full bg-yellow-100 text-yellow-700 text-sm font-medium mb-4">
              Testimonials
            </span>
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Loved by
              <span className="bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent"> Traders</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <TestimonialCard
              quote="Finally, a platform that makes algo trading accessible. I've been trading manually for years, and this has completely transformed my approach."
              name="Rajesh Kumar"
              title="Retail Trader, Mumbai"
              avatar="RK"
            />
            <TestimonialCard
              quote="The risk management features give me peace of mind. The kill switch has saved me from potential disasters during volatile market days."
              name="Priya Sharma"
              title="Software Engineer, Bangalore"
              avatar="PS"
            />
            <TestimonialCard
              quote="Backtesting before going live is a game changer. I can see exactly how strategies would have performed historically."
              name="Amit Patel"
              title="Business Owner, Delhi"
              avatar="AP"
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-purple-600 via-purple-700 to-purple-800" />
        <div className="absolute inset-0">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-yellow-400/20 rounded-full blur-[128px]" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-purple-400/30 rounded-full blur-[128px]" />
        </div>

        <div className="container mx-auto px-4 relative z-10">
          <div className="max-w-4xl mx-auto text-center">
            <h2 className="text-4xl md:text-6xl font-bold mb-6 text-white">
              Ready to Transform
              <br />
              <span className="text-yellow-400">
                Your Trading?
              </span>
            </h2>
            <p className="text-xl text-purple-100 mb-10">
              Join thousands of traders who are already using ArthaQuant to automate their strategies.
              Start free, no credit card required.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/register"
                className="group flex items-center gap-2 px-10 py-5 text-lg font-semibold bg-white text-purple-700 rounded-full hover:shadow-2xl hover:shadow-white/20 transition-all duration-300"
              >
                Create Free Account
                <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
              </Link>
              <Link
                href="/blog"
                className="flex items-center gap-2 px-10 py-5 text-lg font-semibold text-white border-2 border-white/30 rounded-full hover:bg-white/10 transition-all"
              >
                Read Our Blog
              </Link>
            </div>

            {/* Trust Badges */}
            <div className="flex flex-wrap items-center justify-center gap-8 mt-12 text-purple-200">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                <span className="text-sm">Bank-Grade Security</span>
              </div>
              <div className="flex items-center gap-2">
                <Lock className="h-5 w-5" />
                <span className="text-sm">SEBI Compliant</span>
              </div>
              <div className="flex items-center gap-2">
                <Award className="h-5 w-5" />
                <span className="text-sm">ISO 27001 Certified</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-16 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-12">
            {/* Brand */}
            <div className="md:col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <Image src="/logo.png" alt="ArthaQuant" width={40} height={40} className="h-10 w-10" />
                <span className="text-xl font-bold bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent">ArthaQuant</span>
              </div>
              <p className="text-gray-600 mb-6 max-w-sm">
                Empowering retail traders with institutional-grade algorithmic trading technology.
              </p>
              {/* Social Media Links */}
              <div className="flex items-center gap-4">
                <SocialLink href="https://twitter.com/arthaquant" icon={<Twitter className="h-5 w-5" />} />
                <SocialLink href="https://linkedin.com/company/arthaquant" icon={<Linkedin className="h-5 w-5" />} />
                <SocialLink href="https://youtube.com/@arthaquant" icon={<Youtube className="h-5 w-5" />} />
                <SocialLink href="https://instagram.com/arthaquant" icon={<Instagram className="h-5 w-5" />} />
              </div>
            </div>

            {/* Quick Links */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">Product</h3>
              <ul className="space-y-3 text-gray-600">
                <li><Link href="/about" className="hover:text-purple-600 transition-colors">About Us</Link></li>
                <li><Link href="/blog" className="hover:text-purple-600 transition-colors">Blog</Link></li>
                <li><Link href="/register" className="hover:text-purple-600 transition-colors">Get Started</Link></li>
                <li><Link href="/login" className="hover:text-purple-600 transition-colors">Login</Link></li>
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">Resources</h3>
              <ul className="space-y-3 text-gray-600">
                <li><Link href="/blog" className="hover:text-purple-600 transition-colors">Trading Guides</Link></li>
                <li><Link href="/about" className="hover:text-purple-600 transition-colors">How It Works</Link></li>
                <li><Link href="/blog" className="hover:text-purple-600 transition-colors">Strategy Insights</Link></li>
              </ul>
            </div>

            {/* Contact */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">Contact</h3>
              <ul className="space-y-3 text-gray-600">
                <li>
                  <a
                    href="mailto:info@arthaquant.com"
                    className="flex items-center gap-2 hover:text-purple-600 transition-colors"
                  >
                    <Mail className="h-4 w-4" />
                    info@arthaquant.com
                  </a>
                </li>
              </ul>
              <p className="mt-4 text-sm text-gray-500">
                Have questions? We&apos;re here to help you get started.
              </p>
            </div>
          </div>

          {/* Bottom Bar */}
          <div className="mt-16 pt-8 border-t border-gray-200">
            <div className="flex flex-col md:flex-row justify-between items-center gap-4 text-sm text-gray-500">
              <p>&copy; {new Date().getFullYear()} ArthaQuant. All rights reserved.</p>
              <p>Trading involves risk. Past performance is not indicative of future results.</p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

// Component: Stat Item
function StatItem({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <p className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
        {value}
      </p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  )
}

// Component: Feature Card
function FeatureCard({
  icon,
  title,
  description,
  gradient,
}: {
  icon: React.ReactNode
  title: string
  description: string
  gradient: string
}) {
  return (
    <div className="group p-6 rounded-2xl bg-white border border-gray-200 hover:border-purple-300 transition-all duration-300 hover:shadow-xl hover:shadow-purple-500/10">
      <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform text-white`}>
        {icon}
      </div>
      <h3 className="text-xl font-semibold mb-2 text-gray-900">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  )
}

// Component: Step Card
function StepCard({
  step,
  title,
  description,
  icon,
}: {
  step: string
  title: string
  description: string
  icon: React.ReactNode
}) {
  return (
    <div className="relative text-center">
      {/* Step Number */}
      <div className="w-32 h-32 rounded-full bg-gradient-to-br from-purple-100 to-yellow-100 border-2 border-purple-200 flex items-center justify-center mx-auto mb-6 relative">
        <span className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent">
          {step}
        </span>
        <div className="absolute -bottom-2 -right-2 w-10 h-10 rounded-full bg-white border-2 border-purple-200 flex items-center justify-center text-purple-600">
          {icon}
        </div>
      </div>
      <h3 className="text-xl font-semibold mb-2 text-gray-900">{title}</h3>
      <p className="text-gray-600 text-sm">{description}</p>
    </div>
  )
}

// Component: Feature List Item
function FeatureListItem({ text }: { text: string }) {
  return (
    <li className="flex items-center gap-3">
      <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0" />
      <span className="text-gray-700">{text}</span>
    </li>
  )
}

// Component: Testimonial Card
function TestimonialCard({
  quote,
  name,
  title,
  avatar,
}: {
  quote: string
  name: string
  title: string
  avatar: string
}) {
  return (
    <div className="p-6 rounded-2xl bg-white border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex items-center gap-1 mb-4">
        {[...Array(5)].map((_, i) => (
          <svg key={i} className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        ))}
      </div>
      <p className="text-gray-700 mb-6">&quot;{quote}&quot;</p>
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-yellow-500 flex items-center justify-center text-sm font-semibold text-white">
          {avatar}
        </div>
        <div>
          <p className="font-semibold text-gray-900">{name}</p>
          <p className="text-sm text-gray-500">{title}</p>
        </div>
      </div>
    </div>
  )
}

// Component: Social Link
function SocialLink({ href, icon }: { href: string; icon: React.ReactNode }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 hover:bg-purple-100 hover:text-purple-600 transition-all"
    >
      {icon}
    </a>
  )
}
