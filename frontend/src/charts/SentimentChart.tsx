import { useEffect, useState } from 'react'
import {
    Cell,
    Pie,
    PieChart,
    ResponsiveContainer,
    Tooltip,
} from 'recharts'

type SentimentItem = {
    name: string
    value: number
}

type AnalyticsResponse = {
    sentiment: {
        distribution: SentimentItem[]
    }
}

interface SentimentChartProps {
    refreshKey?: number
}

const COLOR_BY_NAME: Record<string, string> = {
    positivo: '#10b981',
    positive: '#10b981',
    neutral: '#94a3b8',
    pregunta: '#6366f1',
    preguntas: '#6366f1',
    negativo: '#f43f5e',
    negative: '#f43f5e',
}

const FALLBACK_COLORS = ['#10b981', '#94a3b8', '#6366f1', '#f43f5e']

function getSegmentColor(name: string, index: number): string {
    const key = (name || '').trim().toLowerCase()
    return COLOR_BY_NAME[key] || FALLBACK_COLORS[index % FALLBACK_COLORS.length]
}

function SentimentChart({ refreshKey = 0 }: SentimentChartProps) {
    const [data, setData] = useState<SentimentItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [activeIndex, setActiveIndex] = useState<number>(0)

    useEffect(() => {
        const loadSentiment = async () => {
            try {
                const baseUrl = (
                    import.meta.env.VITE_API_URL ||
                    import.meta.env.VITE_MOTOR_API_URL ||
                    'http://127.0.0.1:8002'
                ).replace(/\/$/, '')

                const response = await fetch(`${baseUrl}/api/community/analytics`)

                if (!response.ok) {
                    throw new Error('No fue posible cargar el sentimiento')
                }

                const result: AnalyticsResponse = await response.json()
                const dist = result?.sentiment?.distribution ?? []
                setData(dist)
                setActiveIndex(0)
                setError(null)
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Error desconocido al cargar el sentimiento'
                )
            } finally {
                setLoading(false)
            }
        }

        void loadSentiment()
    }, [refreshKey])

    const safeData =
        data.length > 0
            ? data
            : [
                  { name: 'Positivo', value: 0 },
                  { name: 'Neutral', value: 0 },
                  { name: 'Negativo', value: 0 },
              ]

    const currentItem = safeData[activeIndex] || safeData[0]

    return (
        <article className="c-card">
            <div className="c-card__header">
                <div>
                    <div className="c-card__title">Sentimiento de la comunidad</div>
                    <div className="c-card__desc">Pasa el mouse por cada segmento.</div>
                </div>
            </div>

            {loading && (
                <div className="flex h-52 items-center justify-center text-sm text-slate-500">
                    Cargando sentimiento...
                </div>
            )}

            {error && (
                <div className="flex h-52 items-center justify-center text-sm text-red-600">
                    {error}
                </div>
            )}

            {!loading && !error && (
                <>
                    <div className="c-chart c-chart--donut">
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie
                                    data={safeData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={64}
                                    outerRadius={86}
                                    paddingAngle={3}
                                    dataKey="value"
                                    stroke="none"
                                    onMouseEnter={(_, index) => setActiveIndex(index)}
                                    onMouseLeave={() => setActiveIndex(0)}
                                >
                                    {safeData.map((entry, index) => (
                                        <Cell
                                            key={`cell-${entry.name}`}
                                            fill={getSegmentColor(entry.name, index)}
                                            opacity={activeIndex === index ? 1 : 0.85}
                                            style={{ cursor: 'pointer', outline: 'none' }}
                                        />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value) => [`${value}%`, 'Porcentaje']}
                                    contentStyle={{
                                        backgroundColor: '#0f172a',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: '#ffffff',
                                        fontSize: '12px',
                                    }}
                                    itemStyle={{ color: '#ffffff' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>

                        <div className="c-chart__center">
                            <b className="tabular-nums">{currentItem?.value ?? 0}%</b>
                            <span>{currentItem?.name ?? 'Positivo'}</span>
                        </div>
                    </div>

                    <div className="c-legend c-legend--stack">
                        {safeData.map((item, index) => {
                            const color = getSegmentColor(item.name, index)
                            return (
                                <div
                                    key={item.name}
                                    className="c-legend__item"
                                    onMouseEnter={() => setActiveIndex(index)}
                                    onMouseLeave={() => setActiveIndex(0)}
                                >
                                    <span
                                        className="c-legend__swatch"
                                        style={{ background: color }}
                                    />
                                    <span>{item.name}</span>
                                    <span className="c-legend__value tabular-nums">
                                        {item.value}%
                                    </span>
                                </div>
                            )
                        })}
                    </div>
                </>
            )}
        </article>
    )
}

export default SentimentChart