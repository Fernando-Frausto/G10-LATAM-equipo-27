import {
    AlertTriangle,
    ChevronRight,
    Lightbulb,
    MessageSquare,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Bar,
    BarChart,
    CartesianGrid,
    PolarAngleAxis,
    PolarGrid,
    PolarRadiusAxis,
    Radar,
    RadarChart,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'
import SentimentEvolution from '../charts/SentimentEvolution'

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

function Analytics() {
    const navigate = useNavigate()

    const [periodDays, setPeriodDays] = useState<7 | 30 | 90>(30)
    const [hashtagMode, setHashtagMode] = useState<'count' | 'change'>('count')
    const [showRelevance, setShowRelevance] = useState(true)
    const [showParticipation, setShowParticipation] = useState(true)
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
                    return content.includes('?') || content.includes('¿')
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

    const interactionIndex =
        totalMessages > 0
            ? Math.min(
                  100,
                  Math.round(
                      (((messageStats?.positive ?? 0) +
                          (messageStats?.questionCount ?? 0) +
                          (messageStats?.alerts ?? 0)) /
                          totalMessages) *
                          100,
                  ),
              )
            : 0

    const metrics = [
        {
            label: 'Tasa de sentimiento positivo',
            value: positivePercentage !== null ? Math.round(positivePercentage) : 0,
            suffix: '%',
            kind: 'success' as const,
            progress: positivePercentage !== null ? Math.min(100, Math.max(0, Math.round(positivePercentage))) : 0,
            note:
                totalMessages > 0
                    ? `${messageStats?.positive ?? 0} de ${totalMessages} mensajes`
                    : 'Sin datos suficientes',
        },
        {
            label: 'Índice de interacción',
            value: interactionIndex,
            suffix: '%',
            kind: undefined,
            progress: interactionIndex,
            note: 'Participación en hilos y canales',
        },
        {
            label: 'Relevancia promedio',
            value: relevanceAverage !== null ? Math.round(relevanceAverage) : 0,
            suffix: '%',
            kind: 'info' as const,
            progress: relevanceAverage !== null ? Math.min(100, Math.max(0, Math.round(relevanceAverage))) : 0,
            note: `${motorAnalytics?.topics?.length ?? 0} temas detectados`,
        },
        {
            label: 'Alertas activas',
            value: messageStats?.priorityAlerts ?? messageStats?.alerts ?? 0,
            suffix: '',
            kind: 'danger' as const,
            progress: Math.min(
                100,
                Math.round(
                    ((messageStats?.priorityAlerts ?? messageStats?.alerts ?? 0) /
                        Math.max(10, (messageStats?.alerts ?? 0) + 5)) *
                        100,
                ),
            ),
            note: 'Requieren intervención',
        },
    ]

    const leadingTopic = [...(motorAnalytics?.topics ?? [])].sort(
        (a, b) => b.percentage - a.percentage,
    )[0]

    const analyticsData = {
        insights: {
            main: leadingTopic
                ? `Tema con mayor presencia: ${leadingTopic.topic} (${leadingTopic.percentage}%). Las conversaciones sobre este tema generan una alta participación comunitaria.`
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

    const displayEmojis = useMemo(() => {
        return (motorAnalytics?.emojis ?? []).slice(0, 6)
    }, [motorAnalytics?.emojis])

    const hashtagChartData = useMemo(() => {
        const raw = (motorAnalytics?.hashtags ?? []).slice(0, 8)
        const list = raw.map((h) => ({
            label: h.name.startsWith('#') ? h.name : `#${h.name}`,
            value:
                hashtagMode === 'count'
                    ? h.mentions
                    : Math.abs(h.growth ?? Math.round(h.mentions * 4)),
        }))
        list.sort((a, b) => b.value - a.value)
        return list
    }, [motorAnalytics?.hashtags, hashtagMode])

    const radarTopicsData = useMemo(() => {
        const raw = (motorAnalytics?.topics ?? []).slice(0, 6)
        if (raw.length === 0) return []
        const maxVal = Math.max(...raw.map((t) => t.percentage), 1)
        return raw.map((t) => ({
            name: t.topic.charAt(0).toUpperCase() + t.topic.slice(1).toLowerCase(),
            relevance: Math.round(Math.min(100, Math.max(25, t.percentage * 2.3))),
            participation: Math.round((t.percentage / maxVal) * 100),
        }))
    }, [motorAnalytics?.topics])

    return (
        <section data-view="analytics" aria-labelledby="t-analytics">
            {analyticsError && (
                <p
                    role="alert"
                    className="mb-6 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700"
                >
                    No fue posible actualizar todas las métricas: {analyticsError}
                </p>
            )}

            {/* ========== CABECERA DE PÁGINA (Cristian Design System 1:1) ========== */}
            <div className="l-page-head">
                <div className="l-page-head__text">
                    <h1 className="t-page t-page--xl text-3xl font-bold tracking-tight text-slate-900" id="t-analytics">
                        Análisis
                    </h1>
                    <p className="mt-1 text-sm text-slate-500">
                        Curaduría automática de conversaciones: sentimiento, temas, emojis y hashtags.
                    </p>
                </div>
                <div className="l-page-head__actions">
                    <div
                        className="c-segmented"
                        data-period="analytics"
                        role="group"
                        aria-label="Período"
                    >
                        <button
                            type="button"
                            className={periodDays === 7 ? 'is-active' : ''}
                            onClick={() => setPeriodDays(7)}
                        >
                            7d
                        </button>
                        <button
                            type="button"
                            className={periodDays === 30 ? 'is-active' : ''}
                            onClick={() => setPeriodDays(30)}
                        >
                            30d
                        </button>
                        <button
                            type="button"
                            className={periodDays === 90 ? 'is-active' : ''}
                            onClick={() => setPeriodDays(90)}
                        >
                            90d
                        </button>
                    </div>
                </div>
            </div>

            {/* ========== CONTENEDOR PRINCIPAL L-STACK ========== */}
            <div className="l-stack">
                {/* BLOQUE 1: Métricas globales de curaduría */}
                <article className="c-card c-card--lg">
                    <h2 className="t-card">Métricas globales de curaduría</h2>
                    <p className="c-card__desc">
                        Calculadas sobre todos los mensajes procesados del período.
                    </p>
                    <div className="l-grid l-grid--4" style={{ marginTop: 'var(--space-5)' }}>
                        {metrics.map((m) => (
                            <div
                                key={m.label}
                                className="flex flex-col gap-2 min-w-0"
                                style={{ minHeight: '105px', height: 'auto', overflow: 'visible' }}
                            >
                                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                    {m.label}
                                </span>
                                <span
                                    className="font-extrabold tabular-nums text-slate-900 leading-tight"
                                    style={{ fontSize: 'var(--text-3xl, 1.875rem)' }}
                                >
                                    {m.value}
                                    {m.suffix}
                                </span>
                                <div
                                    className={`c-progress c-progress--sm w-full ${
                                        m.kind ? `c-progress--${m.kind}` : ''
                                    }`}
                                    style={{
                                        height: '0.375rem',
                                        borderRadius: '9999px',
                                        background: 'var(--slate-100, #f1f5f9)',
                                        overflow: 'hidden',
                                    }}
                                >
                                    <div
                                        className="c-progress__bar"
                                        style={{
                                            width: `${m.progress}%`,
                                            height: '100%',
                                            borderRadius: 'inherit',
                                        }}
                                    />
                                </div>
                                <span className="text-xs text-slate-400 mt-0.5">{m.note}</span>
                            </div>
                        ))}
                    </div>
                </article>

                {/* BLOQUE 2: Evolución del sentimiento + Insight destacado unificado */}
                <div className="l-grid l-grid--main-side">
                    <SentimentEvolution days={periodDays} />

                    {/* Tarjeta unificada: Insight principal, Preguntas frecuentes y Atención requerida con estilo brand de Insight principal */}
                    <article className="c-card c-card--brand flex flex-col justify-between">
                        <div>
                            <div
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 'var(--space-3)',
                                    marginBottom: 'var(--space-5)',
                                }}
                            >
                                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-orange-500/30 bg-orange-500/20 text-orange-400">
                                    <Lightbulb size={20} />
                                </span>
                                <div>
                                    <h2 className="t-card text-base font-bold" style={{ color: '#ffffff' }}>
                                        Insight destacado
                                    </h2>
                                    <p className="text-xs text-orange-300">
                                        Curaduría y señales comunitarias prioritarias
                                    </p>
                                </div>
                            </div>

                            <div className="l-stack l-stack--sm">
                                {/* 1. Insight principal */}
                                <div className="rounded-xl border border-slate-800 bg-white/[0.04] p-3.5 transition hover:border-slate-700">
                                    <div className="flex items-center gap-2.5">
                                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-orange-500/30 bg-orange-500/20 text-orange-400">
                                            <Lightbulb size={15} />
                                        </span>
                                        <div>
                                            <p className="text-sm font-semibold text-white">
                                                Insight principal
                                            </p>
                                            <p className="text-[11px] font-medium text-orange-300">
                                                Señal dominante detectada
                                            </p>
                                        </div>
                                    </div>
                                    <p className="mt-2 text-xs leading-relaxed text-slate-200 tabular-nums">
                                        {analyticsData.insights.main}
                                    </p>
                                </div>

                                {/* 2. Preguntas frecuentes */}
                                <div className="rounded-xl border border-slate-800 bg-white/[0.04] p-3.5 transition hover:border-slate-700">
                                    <div className="flex items-center gap-2.5">
                                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-blue-500/30 bg-blue-500/20 text-blue-400">
                                            <MessageSquare size={15} />
                                        </span>
                                        <div>
                                            <p className="text-sm font-semibold text-white">
                                                Preguntas frecuentes
                                            </p>
                                            <p className="text-[11px] font-medium text-blue-300">
                                                Oportunidades de contenido
                                            </p>
                                        </div>
                                    </div>
                                    <p className="mt-2 text-xs leading-relaxed text-slate-200 tabular-nums">
                                        {analyticsData.insights.frequent_questions}
                                    </p>
                                </div>

                                {/* 3. Atención requerida */}
                                <div className="rounded-xl border border-red-500/30 bg-red-950/20 p-3.5 transition hover:border-red-500/50">
                                    <div className="flex items-center gap-2.5">
                                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-red-500/30 bg-red-500/20 text-red-400">
                                            <AlertTriangle size={15} />
                                        </span>
                                        <div>
                                            <p className="text-sm font-semibold text-white">
                                                Atención requerida
                                            </p>
                                            <p className="text-[11px] font-medium text-red-300">
                                                Señales detectadas
                                            </p>
                                        </div>
                                    </div>
                                    <p className="mt-2 text-xs leading-relaxed text-slate-200 tabular-nums">
                                        {analyticsData.insights.attention_required}
                                    </p>

                                    <button
                                        type="button"
                                        onClick={() => navigate('/content#panel-quejas')}
                                        className="mt-3.5 inline-flex w-full cursor-pointer items-center justify-between gap-2 rounded-xl border border-red-500/30 bg-red-950/50 px-3.5 py-2.5 text-xs font-semibold text-red-200 transition hover:bg-red-900/60 hover:text-white"
                                    >
                                        <span className="flex items-center gap-2">
                                            <AlertTriangle size={14} className="text-red-400" />
                                            <span>Gestionar quejas y reclamos</span>
                                        </span>
                                        <ChevronRight size={14} className="text-red-400" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </article>
                </div>

                {/* BLOQUE 3: Scorecards de Emojis Destacados */}
                <article className="c-card c-card--lg">
                    <div className="c-card__header">
                        <div>
                            <h2 className="t-card">
                                Scorecards de Emojis Destacados en la Comunidad
                            </h2>
                            <p className="c-card__desc">
                                Reacciones más usadas y su variación.
                            </p>
                        </div>
                    </div>
                    {displayEmojis.length === 0 ? (
                        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-6 text-center text-xs text-slate-500">
                            Aún no se han detectado emojis en los mensajes analizados de la comunidad.
                        </div>
                    ) : (
                        <div className="l-grid l-grid--6" id="an-emojis">
                            {displayEmojis.map((e, idx) => {
                                const isNegative = String(e.trend || '').startsWith('-')
                                const cleanTrend = String(e.trend || '0%').replace(/^[+-]/, '')
                                return (
                                    <div
                                        key={`${e.emoji}-${idx}`}
                                        className="c-card c-card--muted emoji-card"
                                    >
                                        <div className="emoji-card__e">{e.emoji}</div>
                                        <p
                                            className="t-kpi font-extrabold tabular-nums"
                                            style={{
                                                fontSize: 'var(--text-2xl)',
                                                marginTop: 'var(--space-3)',
                                            }}
                                        >
                                            {e.count}
                                        </p>
                                        <p
                                            className="t-caption capitalize text-slate-500"
                                            style={{ textTransform: 'capitalize' }}
                                        >
                                            {e.label || 'Reacción'}
                                        </p>
                                        <p
                                            style={{
                                                marginTop: 'var(--space-2)',
                                                fontSize: 'var(--text-xs)',
                                            }}
                                        >
                                            <span
                                                className={`c-trend c-trend--${
                                                    isNegative ? 'down' : 'up'
                                                }`}
                                            >
                                                {isNegative ? '▼ ' : '▲ '}
                                                {isNegative ? '-' : '+'}
                                                {cleanTrend}
                                            </span>
                                        </p>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </article>

                {/* BLOQUE 4: Hashtags más populares + Temas clave */}
                <div className="l-grid l-grid--halves">
                    {/* Hashtags más populares */}
                    <article className="c-card">
                        <div className="c-card__header">
                            <div>
                                <h2 className="t-card">Hashtags más populares</h2>
                                <p className="c-card__desc">Volumen de uso en el período.</p>
                            </div>
                            <div
                                className="c-segmented"
                                id="an-hash-mode"
                                role="group"
                                aria-label="Métrica"
                            >
                                <button
                                    type="button"
                                    className={hashtagMode === 'count' ? 'is-active' : ''}
                                    onClick={() => setHashtagMode('count')}
                                >
                                    Volumen
                                </button>
                                <button
                                    type="button"
                                    className={hashtagMode === 'change' ? 'is-active' : ''}
                                    onClick={() => setHashtagMode('change')}
                                >
                                    Crecimiento
                                </button>
                            </div>
                        </div>
                        <div className="c-chart">
                            <ResponsiveContainer width="100%" height={280}>
                                <BarChart
                                    data={hashtagChartData}
                                    layout="vertical"
                                    margin={{ top: 8, right: 24, left: 16, bottom: 8 }}
                                >
                                    <CartesianGrid stroke="#f1f5f9" horizontal={false} />
                                    <XAxis
                                        type="number"
                                        tick={{ fontSize: 11, fill: '#94a3b8' }}
                                        axisLine={false}
                                        tickLine={false}
                                    />
                                    <YAxis
                                        type="category"
                                        dataKey="label"
                                        tick={{ fontSize: 11, fill: '#475569', fontWeight: 600 }}
                                        axisLine={false}
                                        tickLine={false}
                                        width={145}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: '#0f172a',
                                            border: 'none',
                                            borderRadius: '8px',
                                            color: '#ffffff',
                                            fontSize: '12px',
                                        }}
                                        itemStyle={{ color: '#ffffff' }}
                                        formatter={(val) => [
                                            hashtagMode === 'count'
                                                ? `${val} usos`
                                                : `+${val}%`,
                                            hashtagMode === 'count'
                                                ? 'Volumen'
                                                : 'Crecimiento',
                                        ]}
                                    />
                                    <Bar
                                        dataKey="value"
                                        fill="#ff7400"
                                        radius={[0, 4, 4, 0]}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </article>

                    {/* Temas clave detectados en la comunidad */}
                    <article className="c-card">
                        <div className="c-card__header">
                            <div>
                                <h2 className="t-card">
                                    Temas clave detectados en la comunidad
                                </h2>
                                <p className="c-card__desc">
                                    Relevancia vs. participación (normalizado 0–100).
                                </p>
                            </div>
                        </div>
                        <div className="c-chart">
                            <ResponsiveContainer width="100%" height={250}>
                                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarTopicsData}>
                                    <PolarGrid stroke="#e2e8f0" />
                                    <PolarAngleAxis
                                        dataKey="name"
                                        tick={{ fontSize: 11, fill: '#475569', fontWeight: 600 }}
                                    />
                                    <PolarRadiusAxis
                                        angle={30}
                                        domain={[0, 100]}
                                        tick={{ fontSize: 9, fill: '#94a3b8' }}
                                        axisLine={false}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: '#0f172a',
                                            border: 'none',
                                            borderRadius: '8px',
                                            color: '#ffffff',
                                            fontSize: '12px',
                                        }}
                                        itemStyle={{ color: '#ffffff' }}
                                        formatter={(val, name) => [`${val}%`, name]}
                                    />
                                    {showRelevance && (
                                        <Radar
                                            name="Relevancia"
                                            dataKey="relevance"
                                            stroke="#ff7400"
                                            fill="#ff7400"
                                            fillOpacity={0.25}
                                        />
                                    )}
                                    {showParticipation && (
                                        <Radar
                                            name="Participación"
                                            dataKey="participation"
                                            stroke="#6366f1"
                                            fill="#6366f1"
                                            fillOpacity={0.2}
                                        />
                                    )}
                                </RadarChart>
                            </ResponsiveContainer>
                        </div>
                        <div
                            id="lg-an-topics"
                            className="c-legend"
                            style={{ justifyContent: 'center', marginTop: 'var(--space-4)' }}
                        >
                            <button
                                type="button"
                                className={`c-legend__item cursor-pointer transition ${
                                    !showRelevance ? 'is-off opacity-40 line-through' : ''
                                }`}
                                onClick={() => setShowRelevance((prev) => !prev)}
                                title={
                                    showRelevance
                                        ? 'Ocultar serie de Relevancia'
                                        : 'Mostrar serie de Relevancia'
                                }
                            >
                                <span
                                    className="c-legend__swatch"
                                    style={{ background: '#ff7400' }}
                                />
                                <span className="font-semibold text-slate-700">Relevancia</span>
                                {!showRelevance && (
                                    <span className="text-[10px] font-normal text-slate-400">
                                        (oculta)
                                    </span>
                                )}
                            </button>
                            <button
                                type="button"
                                className={`c-legend__item cursor-pointer transition ${
                                    !showParticipation ? 'is-off opacity-40 line-through' : ''
                                }`}
                                onClick={() => setShowParticipation((prev) => !prev)}
                                title={
                                    showParticipation
                                        ? 'Ocultar serie de Participación'
                                        : 'Mostrar serie de Participación'
                                }
                            >
                                <span
                                    className="c-legend__swatch"
                                    style={{ background: '#6366f1' }}
                                />
                                <span className="font-semibold text-slate-700">Participación</span>
                                {!showParticipation && (
                                    <span className="text-[10px] font-normal text-slate-400">
                                        (oculta)
                                    </span>
                                )}
                            </button>
                        </div>
                    </article>
                </div>
            </div>
        </section>
    )
}

export default Analytics
