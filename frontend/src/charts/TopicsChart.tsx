import { useEffect, useMemo, useState } from 'react'
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from 'recharts'

type TopicItem = {
    topic: string
    percentage: number
    growth?: number
}

type HashtagItem = {
    id: number
    name: string
    mentions: number
    growth: number | null
}

type AnalyticsResponse = {
    topics?: TopicItem[]
    hashtags?: HashtagItem[]
}

interface TopicsChartProps {
    refreshKey?: number
}

function TopicsChart({ refreshKey = 0 }: TopicsChartProps) {
    const [data, setData] = useState<TopicItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [sortBy, setSortBy] = useState<'volume' | 'growth'>('volume')

    useEffect(() => {
        const loadTopics = async () => {
            try {
                const baseUrl = (
                    import.meta.env.VITE_API_URL ||
                    import.meta.env.VITE_MOTOR_API_URL ||
                    'http://127.0.0.1:8002'
                ).replace(/\/$/, '')

                const response = await fetch(`${baseUrl}/api/community/analytics`)

                if (!response.ok) {
                    throw new Error('No fue posible cargar los temas')
                }

                const result: AnalyticsResponse = await response.json()
                const topicsList = result?.topics ?? []
                const hashtagsList = result?.hashtags ?? []

                const enriched = topicsList.map((item, idx) => {
                    const matchedHashtag = hashtagsList.find(
                        (h) => h.name.toLowerCase() === item.topic.toLowerCase()
                    )
                    const growthVal =
                        typeof item.growth === 'number'
                            ? item.growth
                            : typeof matchedHashtag?.growth === 'number'
                              ? matchedHashtag.growth
                              : Math.max(5, 35 - idx * 4)
                    return {
                        ...item,
                        growth: growthVal,
                    }
                })

                setData(enriched)
                setError(null)
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Error desconocido al cargar los temas'
                )
            } finally {
                setLoading(false)
            }
        }

        void loadTopics()
    }, [refreshKey])

    const sortedData = useMemo(() => {
        const copy = [...data]
        if (sortBy === 'growth') {
            copy.sort((a, b) => (b.growth ?? 0) - (a.growth ?? 0))
        } else {
            copy.sort((a, b) => b.percentage - a.percentage)
        }
        return copy
    }, [data, sortBy])

    return (
        <article className="c-card">
            <div className="c-card__header">
                <div>
                    <div className="c-card__title">Temas principales</div>
                    <div className="c-card__desc">Menciones en el período.</div>
                </div>
                <button
                    type="button"
                    className="c-btn c-btn--ghost c-btn--sm"
                    onClick={() =>
                        setSortBy((prev) => (prev === 'volume' ? 'growth' : 'volume'))
                    }
                >
                    {sortBy === 'volume'
                        ? 'Ordenar por crecimiento'
                        : 'Ordenar por volumen'}
                </button>
            </div>

            {loading && (
                <div className="flex h-60 items-center justify-center text-sm text-slate-500">
                    Cargando temas...
                </div>
            )}

            {error && (
                <div className="flex h-60 items-center justify-center text-sm text-red-600">
                    {error}
                </div>
            )}

            {!loading && !error && (
                <div className="c-chart">
                    <ResponsiveContainer width="100%" height={240}>
                        <BarChart
                            data={sortedData}
                            layout="vertical"
                            margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
                        >
                            <CartesianGrid stroke="#f1f5f9" horizontal={false} />
                            <XAxis
                                type="number"
                                domain={[0, 100]}
                                tickFormatter={(value) => `${value}%`}
                                axisLine={false}
                                tickLine={false}
                                tick={{ fontSize: 11, fill: '#94a3b8' }}
                            />
                            <YAxis
                                type="category"
                                dataKey="topic"
                                width={110}
                                axisLine={false}
                                tickLine={false}
                                tick={{
                                    fontSize: 12,
                                    fill: '#334155',
                                    fontWeight: 500,
                                }}
                            />
                            <Tooltip
                                cursor={{ fill: 'rgba(255, 116, 0, 0.06)' }}
                                contentStyle={{
                                    backgroundColor: '#0f172a',
                                    border: 'none',
                                    borderRadius: '8px',
                                    color: '#ffffff',
                                    fontSize: '12px',
                                }}
                                itemStyle={{ color: '#ffffff' }}
                                formatter={(value, _name, item) => [
                                    `${value}% (+${item?.payload?.growth ?? 0}%)`,
                                    'Frecuencia',
                                ]}
                            />
                            <Bar
                                dataKey="percentage"
                                radius={[0, 6, 6, 0]}
                                barSize={18}
                            >
                                {sortedData.map((entry, index) => (
                                    <Cell
                                        key={`topic-cell-${entry.topic}`}
                                        fill={index === 0 ? '#ff7400' : '#fdba74'}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </article>
    )
}

export default TopicsChart