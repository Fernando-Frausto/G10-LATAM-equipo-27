import { useEffect, useId, useState } from 'react'
import {
    Area,
    AreaChart,
    CartesianGrid,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'

type EvolutionItem = {
    day: string
    date: string
    positive: number
    neutral?: number
    negative?: number
    messages: number
}

type SentimentDistItem = {
    name: string
    value: number
}

type AnalyticsResponse = {
    sentiment: {
        distribution?: SentimentDistItem[]
        evolution: EvolutionItem[]
    }
}

interface SentimentEvolutionProps {
    days?: number
    refreshKey?: number
}

function SentimentEvolution({ days = 30, refreshKey = 0 }: SentimentEvolutionProps) {
    const [data, setData] = useState<Array<EvolutionItem & { neutral: number; negative: number }>>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const rawId = useId()
    const gradId = `pos-grad-${rawId.replace(/[^a-zA-Z0-9_-]/g, '')}`

    useEffect(() => {
        const loadEvolution = async () => {
            try {
                const baseUrl = (
                    import.meta.env.VITE_API_URL ||
                    import.meta.env.VITE_MOTOR_API_URL ||
                    'http://127.0.0.1:8002'
                ).replace(/\/$/, '')

                const response = await fetch(`${baseUrl}/api/community/analytics`)

                if (!response.ok) {
                    throw new Error('No fue posible cargar la evolución del sentimiento')
                }

                const result: AnalyticsResponse = await response.json()
                const rawEvolution = result?.sentiment?.evolution ?? []
                const dist = result?.sentiment?.distribution ?? []

                const distNeutral =
                    dist.find((d) => d.name.toLowerCase().includes('neutral'))?.value ?? 30
                const distNegative =
                    dist.find((d) => d.name.toLowerCase().includes('negativ'))?.value ?? 10
                const nonPosTotal = distNeutral + distNegative || 1
                const neutralShare = distNeutral / nonPosTotal

                const enriched = rawEvolution.map((item) => {
                    const pos = Math.max(0, Math.min(100, Number(item.positive ?? 0)))
                    const remainder = Math.max(0, 100 - pos)
                    const neu =
                        typeof item.neutral === 'number'
                            ? item.neutral
                            : Math.round(remainder * neutralShare)
                    const neg =
                        typeof item.negative === 'number'
                            ? item.negative
                            : Math.max(0, remainder - neu)
                    return {
                        ...item,
                        positive: pos,
                        neutral: neu,
                        negative: neg,
                    }
                })

                setData(enriched)
                setError(null)
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Error desconocido al cargar la evolución'
                )
            } finally {
                setLoading(false)
            }
        }

        void loadEvolution()
    }, [refreshKey])

    const visibleData = days > 0 ? data.slice(-days) : data

    return (
        <article className="c-card">
            <div className="c-card__header">
                <div>
                    <div className="c-card__title">Evolución del sentimiento</div>
                    <div className="c-card__desc">% de mensajes por sentimiento.</div>
                </div>
            </div>

            {loading && (
                <div className="flex h-56 items-center justify-center text-sm text-slate-500">
                    Cargando evolución...
                </div>
            )}

            {error && (
                <div className="flex h-56 items-center justify-center text-sm text-red-600">
                    {error}
                </div>
            )}

            {!loading && !error && (
                <>
                    <div className="c-chart c-chart--sm">
                        <ResponsiveContainer width="100%" height={220}>
                            <AreaChart
                                data={visibleData}
                                margin={{ top: 8, right: 10, left: -16, bottom: 0 }}
                            >
                                <defs>
                                    <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.22} />
                                        <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid stroke="#f1f5f9" vertical={false} />
                                <XAxis
                                    dataKey="date"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                                    tickFormatter={(value: string) => {
                                        if (!value || !value.includes('-')) return value
                                        const parts = value.split('-')
                                        return `${parts[2]}/${parts[1]}`
                                    }}
                                />
                                <YAxis
                                    domain={[0, 100]}
                                    tickFormatter={(value) => `${value}%`}
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fontSize: 11, fill: '#94a3b8' }}
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
                                    labelFormatter={(value) => `Fecha: ${value}`}
                                    formatter={(value, name) => {
                                        const label =
                                            name === 'positive'
                                                ? 'Positivo'
                                                : name === 'neutral'
                                                  ? 'Neutral'
                                                  : 'Negativo'
                                        return [`${value}%`, label]
                                    }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="positive"
                                    stroke="#10b981"
                                    strokeWidth={2}
                                    fill={`url(#${gradId})`}
                                    dot={false}
                                    activeDot={{ r: 4 }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="neutral"
                                    stroke="#94a3b8"
                                    strokeWidth={2}
                                    fill="transparent"
                                    dot={false}
                                    activeDot={{ r: 4 }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="negative"
                                    stroke="#f43f5e"
                                    strokeWidth={2}
                                    fill="transparent"
                                    dot={false}
                                    activeDot={{ r: 4 }}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="c-legend">
                        <span className="c-legend__item">
                            <span
                                className="c-legend__swatch"
                                style={{ background: '#10b981' }}
                            />
                            Positivo
                        </span>
                        <span className="c-legend__item">
                            <span
                                className="c-legend__swatch"
                                style={{ background: '#94a3b8' }}
                            />
                            Neutral
                        </span>
                        <span className="c-legend__item">
                            <span
                                className="c-legend__swatch"
                                style={{ background: '#f43f5e' }}
                            />
                            Negativo
                        </span>
                    </div>
                </>
            )}
        </article>
    )
}

export default SentimentEvolution