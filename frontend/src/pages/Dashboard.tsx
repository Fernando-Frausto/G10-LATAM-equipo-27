import { useEffect, useState } from 'react'
import {
  CheckCircle,
  FileText,
  MessageSquare,
  RefreshCw,
  Sparkles,
  Tag,
  Users,
} from 'lucide-react'

import KpiCard from '../components/KpiCard'
import FeaturedStories from '../components/FeaturedStories'
import SentimentChart from '../charts/SentimentChart'
import TopicsChart from '../charts/TopicsChart'
import SentimentEvolution from '../charts/SentimentEvolution'
import AudienceHeatmap from '../charts/AudienceHeatmap'

type DashboardData = {
  messages_processed?: number | null
  messages_change?: number | null
  total_audience?: number | null
  audience_change?: number | null
  positive_sentiment?: number | null
  sentiment_change?: number | null
  topics_detected?: number | null
  new_topics?: number | null
  content_generated?: number | null
  pending_approvals?: number | null
}

const formatPercentageChange = (change: number | null | undefined): string => {
  if (change == null) return 'Sin comparación'
  const sign = change > 0 ? '+' : ''
  return `${sign}${change.toLocaleString('es-CO')}% esta semana`
}

const formatPointsChange = (change: number | null | undefined): string => {
  if (change == null) return 'Sin comparación'
  const sign = change > 0 ? '+' : ''
  return `${sign}${change.toLocaleString('es-CO')} puntos esta semana`
}

function Dashboard() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [refreshing, setRefreshing] = useState(false)
  const [analyticsVersion, setAnalyticsVersion] = useState(0)

  const loadDashboard = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)

    try {
      setError(null)

      const motorUrl = (
        import.meta.env.VITE_MOTOR_API_URL ||
        'http://127.0.0.1:8002'
      ).replace(/\/$/, '')

      const [dashboardResponse, analyticsResponse] = await Promise.all([
        fetch(`${motorUrl}/api/community/dashboard`, {
          cache: 'no-store',
        }),
        fetch(`${motorUrl}/api/community/analytics`, {
          cache: 'no-store',
        }),
      ])

      if (!dashboardResponse.ok || !analyticsResponse.ok) {
        throw new Error('No fue posible actualizar los datos del Motor IA')
      }

      const data: DashboardData = await dashboardResponse.json()
      await analyticsResponse.json()

      setDashboardData(data)
      setAnalyticsVersion((version) => version + 1)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Error desconocido al cargar el dashboard'
      )
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void loadDashboard()
  }, [])

  if (loading) {
    return <div className="p-6 text-slate-500">Cargando dashboard...</div>
  }

  if (!dashboardData) {
    return (
      <div className="p-6 text-red-600">
        {error ?? 'No hay datos disponibles'}
      </div>
    )
  }



  return (
    <div>

      {/* Encabezado */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">
            Dashboard
          </h2>
          <p className="mt-1 text-slate-500">
            Resumen de tu comunidad
          </p>
        </div>

        <button
          type="button"
          onClick={() => void loadDashboard(true)}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={refreshing ? 'animate-spin' : ''}
          />
          {refreshing ? 'Actualizando...' : 'Actualizar datos'}
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-3 text-sm text-red-600">
          {error}. Se muestran los ultimos datos disponibles.
        </p>
      )}


      {/* KPIs */}
      <div className="mt-8 grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">

        <KpiCard
          title="Mensajes procesados"
          value={dashboardData.messages_processed?.toLocaleString("es-CO") ?? "0"}
          description={formatPercentageChange(dashboardData.messages_change)}
          icon={<MessageSquare size={20} />}
        />

        <KpiCard
          title="Total de audiencia"
          value={dashboardData.total_audience?.toLocaleString("es-CO") ?? "0"}
          description={formatPercentageChange(dashboardData.audience_change)}
          icon={<Users size={20} />}
        />

        <KpiCard
          title="Sentimiento positivo"
          value={
            dashboardData.positive_sentiment != null
              ? `${dashboardData.positive_sentiment}%`
              : "0%"
          }
          description={formatPointsChange(dashboardData.sentiment_change)}
          icon={<Sparkles size={20} />}
        />

        <KpiCard
          title="Temas detectados"
          value={dashboardData.topics_detected?.toLocaleString("es-CO") ?? "0"}
          description={`${dashboardData.new_topics ?? 0} nuevos temas`}
          icon={<Tag size={20} />}
        />

        <KpiCard
          title="Contenidos generados"
          value={dashboardData.content_generated?.toLocaleString("es-CO") ?? "0"}
          description="Esta semana"
          icon={<FileText size={20} />}
        />

        <KpiCard
          title="Pendientes"
          value={dashboardData.pending_approvals?.toLocaleString("es-CO") ?? "0"}
          description="Requieren aprobación"
          icon={<CheckCircle size={20} />}
        />

      </div>
      
             
      <FeaturedStories key={`stories-${analyticsVersion}`} />

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">

        <SentimentChart key={`sentiment-${analyticsVersion}`} />

        <TopicsChart key={`topics-${analyticsVersion}`} />

      </div>

      <div className="mt-8">
        <SentimentEvolution key={`evolution-${analyticsVersion}`} />
      </div>
      <div className="mt-8">
        <AudienceHeatmap key={`heatmap-${analyticsVersion}`} />
      </div>

    </div>
  )
}

export default Dashboard