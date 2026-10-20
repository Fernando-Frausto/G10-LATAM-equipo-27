import {
    AlertTriangle,
    BarChart3,
    ChevronRight,
    Hash,
    Lightbulb,
    MessageSquare,
    ShieldCheck,
    Sparkles,
    Tag,
    TrendingUp,
    Zap,
} from 'lucide-react'

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

type CommunityMessagesResponse = {
    total?: number
    messages: Array<{
        message?: {
            content?: string
        }
        analysis?: {
            sentiment?: 'positive' | 'neutral' | 'negative'
            topic?: string
            relevance?: number
        }
    }>
}

const MOTOR_API_URL = (
    import.meta.env.VITE_API_URL ||
    import.meta.env.VITE_MOTOR_API_URL ||
    'http://127.0.0.1:8002'
).replace(/\/$/, '')

type MotorAnalyticsResponse = {
    sentiment?: {
        distribution?: Array<{ name: string; value: number }>
    }
    topics?: Array<{ topic: string; percentage: number }>
    hashtags?: Array<{
        id: number
        name: string
        mentions: number
        growth: number | null
    }>
    emojis?: Array<{
        emoji: string
        count: number
        sentiment: string
        label: string
        description: string
        trend: string
    }>
    brand_alignment_percentage?: number
}

const topicIcons = [BarChart3, MessageSquare, ShieldCheck, Sparkles]

function Analytics() {
    const navigate = useNavigate()

    const [motorAnalytics, setMotorAnalytics] =
        useState<MotorAnalyticsResponse | null>(null)
    const [analyticsError, setAnalyticsError] = useState<string | null>(null)

    useEffect(() => {
        const controller = new AbortController()

        const loadAnalytics = async () => {
            try {
                const response = await fetch(
                    `${MOTOR_API_URL}/api/community/analytics`,
                    { signal: controller.signal },
                )
                if (!response.ok) {
                    throw new Error(`Analytics HTTP ${response.status}`)
                }
                const data =
                    (await response.json()) as MotorAnalyticsResponse
                setMotorAnalytics(data)
                setAnalyticsError(null)
            } catch (error) {
                if (controller.signal.aborted) return
                setAnalyticsError(
                    error instanceof Error ? error.message : 'Error de Analytics',
                )
            }
        }

        void loadAnalytics()
        return () => controller.abort()
    }, [])

    const [messageStats, setMessageStats] = useState<{
        total: number
        positive: number
        relevance: number | null
        alerts: number
        priorityAlerts: number
        questionCount: number
        frequentQuestionTopic: string | null
        frequentQuestionTopicCount: number
    } | null>(null)

    useEffect(() => {
        const controller = new AbortController()

        const loadStats = async () => {
            try {
                const response = await fetch(
                    `${MOTOR_API_URL}/api/community/messages?limit=500`,
                    { signal: controller.signal },
                )
                if (!response.ok) throw new Error(`HTTP ${response.status}`)

                const data = (await response.json()) as CommunityMessagesResponse

                const messages = data.messages ?? []
                const analyzed = messages.filter(
                    (item) => Number.isFinite(Number(item.analysis?.relevance)),
                )
                const relevance = analyzed.length
                    ? analyzed.reduce(
                          (sum, item) => sum + Number(item.analysis?.relevance ?? 0),
                          0,
                      ) / analyzed.length
                    : null

                const questions = messages.filter((item) => {
                    const content = item.message?.content?.trim() ?? ''
                    return content.includes('?') ||
                        content.includes('¿')
                })

                const questionTopics = new Map<string, number>()

                for (const item of questions) {
                    const topic = item.analysis?.topic?.trim()
                    if (
                        !topic ||
                        topic.toUpperCase() === 'SIN_CLASIFICAR'
                    ) continue
                    questionTopics.set(
                        topic,
                        (questionTopics.get(topic) ?? 0) + 1,
                    )
                }

                const mostFrequentQuestionTopic =
                    [...questionTopics.entries()].sort(
                        (a, b) => b[1] - a[1],
                    )[0] ?? null

                setMessageStats({
                    total: data.total ?? messages.length,
                    positive: messages.filter(
                        (item) => item.analysis?.sentiment === 'positive',
                    ).length,
                    relevance,
                    alerts: messages.filter(
                        (item) => item.analysis?.sentiment === 'negative',
                    ).length,
                    priorityAlerts: messages.filter(
                        (item) =>
                            item.analysis?.sentiment === 'negative' &&
                            Number(item.analysis?.relevance ?? 0) >= 70,
                    ).length,
                    questionCount: questions.length,
                    frequentQuestionTopic:
                        mostFrequentQuestionTopic?.[0] ?? null,
                    frequentQuestionTopicCount:
                        mostFrequentQuestionTopic?.[1] ?? 0,
                })
            } catch (error) {
                if (!controller.signal.aborted) {
                    setAnalyticsError(
                        error instanceof Error ? error.message : 'Error al consultar mensajes',
                    )
                }
            }
        }

        void loadStats()
        return () => controller.abort()
    }, [])

    const totalMessages = messageStats?.total ?? 0
    const positivePercentage =
        messageStats && totalMessages > 0
            ? (messageStats.positive / totalMessages) * 100
            : null
    const relevanceAverage = messageStats?.relevance ?? null

    const popularHashtags = (motorAnalytics?.hashtags ?? [])
        .slice()
        .sort((a, b) => b.mentions - a.mentions)
        .slice(0, 15)
        .map((item) => ({
            tag: item.name,
            value: item.mentions,
            trend:
                item.growth === null
                    ? 'N/D'
                    : `${item.growth > 0 ? '+' : ''}${item.growth}%`,
        }))

    const keyTopics = (motorAnalytics?.topics ?? []).map((item, index) => ({
        title: item.topic,
        description: 'Tema detectado por el motor de análisis',
        percentage: item.percentage,
        icon: topicIcons[index % topicIcons.length],
    }))

    const brandAlignment =
        typeof motorAnalytics?.brand_alignment_percentage === 'number'
            ? motorAnalytics.brand_alignment_percentage
            : 100.0

    const leadingTopic = [...(motorAnalytics?.topics ?? [])]
        .sort((a, b) => b.percentage - a.percentage)[0]

    const analyticsData = {
        insights: {
            main: leadingTopic
                ? `Tema con mayor presencia: ${leadingTopic.topic} (${leadingTopic.percentage}%).`
                : 'Sin datos suficientes para identificar el tema principal.',
            frequent_questions:
                messageStats === null
                    ? 'Esperando datos de preguntas del Motor IA.'
                    : messageStats.questionCount === 0
                      ? 'No se detectaron preguntas en los mensajes consultados.'
                      : messageStats.frequentQuestionTopic
                        ? `${messageStats.questionCount} preguntas detectadas. Tema más frecuente: ${messageStats.frequentQuestionTopic} (${messageStats.frequentQuestionTopicCount} preguntas).`
                        : `${messageStats.questionCount} preguntas detectadas, sin temas clasificados.`,
            attention_required:
                messageStats === null
                    ? 'Sin datos disponibles sobre mensajes que requieren atención.'
                    : `${messageStats.alerts} mensajes negativos detectados; ${messageStats.priorityAlerts} con relevancia alta (70 o más).`,
        },
    }

    return (
        <div className="space-y-8">
            {analyticsError && (
                <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                    No fue posible actualizar todas las métricas: {analyticsError}
                </p>
            )}
            {/* HEADER */}
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-orange-100 text-orange-500">
                        <BarChart3 size={22} />
                    </div>

                    <div>
                        <h1 className="text-3xl font-bold text-slate-900">
                            Análisis
                        </h1>

                        <p className="mt-1 text-sm text-slate-500">
                            Curaduría, relevancia e inteligencia de la comunidad de Discord
                        </p>
                    </div>
                </div>

                <div className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs text-slate-500 shadow-sm">
                    Evaluación algorítmica de relevancia, voz de marca e intención
                </div>
            </div>

            {/* MÉTRICAS PRINCIPALES */}
            <section>
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-base font-bold text-slate-900">
                        Métricas globales de curaduría
                    </h2>

                    <span className="text-xs text-slate-400">
                        Procesamiento y clasificación de interacciones
                    </span>
                </div>

                <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-6">
                    <MetricCard
                        label="Mensajes analizados"
                        value={String(totalMessages)}
                        helper="Comunidad Discord"
                        icon={<MessageSquare size={19} />}
                        iconClass="bg-orange-100 text-orange-500"
                    />

                    <MetricCard
                        label="Sentimiento positivo"
                        value={positivePercentage === null ? 'N/D' : `${positivePercentage.toFixed(1)}%`}
                        helper="De los mensajes"
                        icon={<TrendingUp size={19} />}
                        iconClass="bg-emerald-100 text-emerald-600"
                    />

                    <MetricCard
                        label="Temas detectados"
                        value={String(motorAnalytics?.topics?.length ?? 0)}
                        helper="Temas principales"
                        icon={<BarChart3 size={19} />}
                        iconClass="bg-blue-100 text-blue-600"
                    />

                    <MetricCard
                        label="Relevancia promedio"
                        value={relevanceAverage === null ? 'N/D' : relevanceAverage.toFixed(2)}
                        helper="Contenido detectado"
                        icon={<Zap size={19} />}
                        iconClass="bg-purple-100 text-purple-600"
                    />

                    <MetricCard
                        label="Alineación de marca"
                        value={`${brandAlignment.toFixed(1)}%`}
                        helper="Consistencia de tono CloudEdTech"
                        icon={<ShieldCheck size={19} />}
                        iconClass="bg-emerald-100 text-emerald-600"
                        accent="text-emerald-600"
                    />

                    <MetricCard
                        label="Alertas"
                        value={messageStats === null ? "N/D" : String(messageStats.priorityAlerts)}
                        helper="Requieren atención"
                        icon={<AlertTriangle size={19} />}
                        iconClass="bg-red-100 text-red-500"
                        accent="text-red-500"
                    />
                </div>
            </section>

            {/* SCORECARDS EMOJIS */}
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-orange-50 text-orange-500">
                            <Sparkles size={16} />
                        </div>

                        <div>
                            <h2 className="font-bold text-slate-900">
                                Scorecards de Emojis Destacados en la Comunidad
                            </h2>

                            <p className="mt-0.5 text-xs text-slate-400">
                                Señales rápidas de interacción y comportamiento
                            </p>
                        </div>
                    </div>

                    <span className="text-xs text-slate-400">
                        Frecuencia agregada y sentiment telemetry
                    </span>
                </div>

                {(!motorAnalytics?.emojis || motorAnalytics.emojis.length === 0) ? (
                    <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-6 text-center text-xs text-slate-500">
                        Aún no se han detectado emojis en los mensajes analizados de la comunidad.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
                        {motorAnalytics.emojis.map((item, idx) => {
                            const isNegative = item.trend.startsWith('-')

                            return (
                                <div
                                    key={`${item.emoji}-${item.label}-${idx}`}
                                    className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 transition-colors hover:border-slate-300"
                                >
                                    <div className="flex items-start justify-between">
                                        <span className="text-2xl" role="img" aria-label={item.label}>
                                            {item.emoji}
                                        </span>

                                        <span
                                            className={`rounded-md px-2 py-1 text-[10px] font-bold ${
                                                isNegative
                                                    ? 'bg-rose-50 text-rose-600'
                                                    : 'bg-emerald-50 text-emerald-600'
                                            }`}
                                            title="Frecuencia relativa sobre el total de emojis detectados en la comunidad"
                                        >
                                            {item.trend.includes('%') ? `${item.trend} del total` : `${item.trend}% del total`}
                                        </span>
                                    </div>

                                    <p className="mt-3 text-xl font-black text-slate-900">
                                        {item.count}
                                    </p>

                                    <p className="mt-1 text-xs font-semibold text-slate-700">
                                        {item.label}
                                    </p>

                                    <p className="mt-1 text-[11px] text-slate-400">
                                        {item.description}
                                    </p>
                                </div>
                            )
                        })}
                    </div>
                )}
            </section>

            {/* HASHTAGS + TEMAS */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[0.9fr_1.1fr]">
                {/* HASHTAGS */}
                <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div className="mb-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Hash size={18} className="text-orange-500" />

                            <h2 className="font-bold text-slate-900">
                                Hashtags más populares
                            </h2>
                        </div>

                        <span className="text-[11px] text-slate-400">
                            Top 15
                        </span>
                    </div>

                    <p className="mb-5 text-xs leading-5 text-slate-500">
                        Ranking de hashtags con mayor presencia en las conversaciones analizadas.
                    </p>

                    <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
                        {popularHashtags.map((hashtag, index) => {
                            const percentage =
                                popularHashtags[0]?.value ? (hashtag.value / popularHashtags[0].value) * 100 : 0

                            return (
                                <div
                                    key={hashtag.tag}
                                    className="rounded-xl border border-slate-100 px-3 py-3"
                                >
                                    <div className="grid grid-cols-[28px_minmax(0,1fr)_120px_50px] items-center gap-2">
                                        <span className="text-[10px] font-bold text-slate-400">
                                            {String(index + 1).padStart(2, '0')}
                                        </span>

                                        <span className="truncate text-xs font-bold text-slate-700">
                                            {hashtag.tag}
                                        </span>

                                        <div className="flex items-center gap-2">
                                            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100">
                                                <div
                                                    className="h-full rounded-full bg-orange-500"
                                                    style={{
                                                        width: `${percentage}%`,
                                                    }}
                                                />
                                            </div>

                                            <span className="w-7 text-right text-[10px] font-semibold text-slate-500">
                                                {hashtag.value}
                                            </span>
                                        </div>

                                        <span className="rounded-md bg-emerald-50 px-1.5 py-1 text-center text-[9px] font-bold text-emerald-600">
                                            {hashtag.trend}
                                        </span>
                                    </div>
                                </div>
                            )
                        })}
                    </div>

                    <div className="mt-5 flex items-center justify-between border-t border-slate-100 pt-4">
                        <span className="text-[11px] text-slate-400">
                            Clasificación automática mediante NLP
                        </span>

                        <button
                            type="button"
                            onClick={() => navigate('/messages')}
                            className="inline-flex items-center gap-1 text-xs font-bold text-orange-500 hover:text-orange-600"
                        >
                            Ver en Ingesta
                            <ChevronRight size={14} />
                        </button>
                    </div>
                </section>

                {/* TEMAS CLAVE */}
                <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div className="mb-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Tag size={18} className="text-orange-500" />

                            <h2 className="font-bold text-slate-900">
                                Temas clave detectados en la comunidad
                            </h2>
                        </div>

                        <span className="text-[11px] text-slate-400">
                            Clasificación semántica mediante IA
                        </span>
                    </div>

                    <p className="mb-5 text-xs leading-5 text-slate-500">
                        Agrupación temática de las conversaciones con mayor relevancia.
                    </p>

                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                        {keyTopics.map((topic) => {
                            const Icon = topic.icon

                            return (
                                <article
                                    key={topic.title}
                                    className="rounded-xl border border-slate-200 bg-slate-50/40 p-4"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="flex min-w-0 items-start gap-3">
                                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-500">
                                                <Icon size={17} />
                                            </div>

                                            <h3 className="text-xs font-bold leading-5 text-slate-800">
                                                {topic.title}
                                            </h3>
                                        </div>

                                        <span className="shrink-0 text-sm font-black text-slate-900">
                                            {topic.percentage}%
                                        </span>
                                    </div>

                                    <p className="mt-3 min-h-[40px] text-[11px] leading-5 text-slate-500">
                                        {topic.description}
                                    </p>

                                    <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-slate-200">
                                        <div
                                            className="h-full rounded-full bg-orange-500"
                                            style={{
                                                width: `${topic.percentage}%`,
                                            }}
                                        />
                                    </div>
                                </article>
                            )
                        })}
                    </div>
                </section>
            </div>

            {/* INSIGHTS */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
                <InsightCard
                    icon={<Lightbulb size={20} />}
                    iconClass="bg-orange-100 text-orange-500"
                    title="Insight principal"
                    subtitle="Detectado por IA"
                    content={analyticsData.insights.main}
                />

                <InsightCard
                    icon={<MessageSquare size={20} />}
                    iconClass="bg-blue-100 text-blue-600"
                    title="Preguntas frecuentes"
                    subtitle="Oportunidades de contenido"
                    content={analyticsData.insights.frequent_questions}
                />

                <InsightCard
                    icon={<AlertTriangle size={20} />}
                    iconClass="bg-red-100 text-red-500"
                    title="Atención requerida"
                    subtitle="Señales detectadas"
                    content={analyticsData.insights.attention_required}
                    action={
                        <button
                            type="button"
                            onClick={() => navigate('/content#panel-quejas')}
                            className="inline-flex w-full items-center justify-between gap-2 rounded-xl border border-red-200 bg-red-50/70 px-4 py-2.5 text-xs font-semibold text-red-700 transition hover:bg-red-100 hover:text-red-800"
                        >
                            <span className="flex items-center gap-2">
                                <AlertTriangle size={14} className="text-red-600" />
                                <span>Gestionar quejas y reclamos</span>
                            </span>
                            <ChevronRight size={14} className="text-red-500" />
                        </button>
                    }
                />
            </div>

            {/* ESTADO DE INTEGRACIÓN */}
            <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-4">
                <div className="flex items-start gap-3">
                    <Sparkles
                        size={17}
                        className="mt-0.5 shrink-0 text-blue-600"
                    />

                    <div>
                        <p className="text-xs font-bold text-blue-900">
                            Flujo de análisis CloudEdTech
                        </p>

                        <p className="mt-1 text-xs leading-5 text-blue-700">
                            La pestaña de Análisis consolida la telemetría inteligente de la comunidad: distribución de sentimiento, detección semántica de temas clave, tendencias de hashtags y frecuencia de emojis calculados a partir de los mensajes reales de Discord. Permite auditar el comportamiento comunitario e identificar oportunidades editoriales sin intermediación de curaduría.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}

function MetricCard({
    label,
    value,
    helper,
    icon,
    iconClass,
    accent = 'text-slate-900',
}: {
    label: string
    value: string
    helper: string
    icon: React.ReactNode
    iconClass: string
    accent?: string
}) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        {label}
                    </p>

                    <p className={`mt-3 text-2xl font-black ${accent}`}>
                        {value}
                    </p>

                    <p className="mt-2 text-[11px] leading-4 text-slate-400">
                        {helper}
                    </p>
                </div>

                <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${iconClass}`}
                >
                    {icon}
                </div>
            </div>
        </div>
    )
}

function InsightCard({
    icon,
    iconClass,
    title,
    subtitle,
    content,
    action,
}: {
    icon: React.ReactNode
    iconClass: string
    title: string
    subtitle: string
    content: string
    action?: React.ReactNode
}) {
    return (
        <div className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div>
                <div className="mb-4 flex items-center gap-3">
                    <div
                        className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
                    >
                        {icon}
                    </div>

                    <div>
                        <h3 className="font-semibold text-slate-900">
                            {title}
                        </h3>

                        <p className="text-xs text-slate-400">
                            {subtitle}
                        </p>
                    </div>
                </div>

                <p className="text-sm leading-6 text-slate-600">
                    {content}
                </p>
            </div>

            {action && (
                <div className="mt-4 pt-4 border-t border-slate-100">
                    {action}
                </div>
            )}
        </div>
    )
}

export default Analytics