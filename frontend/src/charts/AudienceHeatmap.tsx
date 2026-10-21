import { useEffect, useState } from 'react'
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

type ActivityRow = {
    day: string
    values: number[]
    counts: number[]
}

type ActivityHeatmap = {
    hours: string[]
    data: ActivityRow[]
}

type AnalyticsResponse = {
    activity_heatmap?: ActivityHeatmap
}

type CommunityMessageItem = {
    message?: {
        timestamp?: string
    }
}

type CommunityMessagesResponse = {
    messages?: CommunityMessageItem[]
}

type HourlyBarPoint = {
    hour: string
    count: number
}

interface AudienceHeatmapProps {
    refreshKey?: number
}

function AudienceHeatmap({ refreshKey = 0 }: AudienceHeatmapProps) {
    const [hourlyData, setHourlyData] = useState<HourlyBarPoint[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const loadActivity = async () => {
            try {
                const baseUrl = (
                    import.meta.env.VITE_API_URL ||
                    import.meta.env.VITE_MOTOR_API_URL ||
                    'http://127.0.0.1:8002'
                ).replace(/\/$/, '')

                const [analyticsRes, messagesRes] = await Promise.all([
                    fetch(`${baseUrl}/api/community/analytics`),
                    fetch(`${baseUrl}/api/community/messages?limit=500`).catch(() => null),
                ])

                if (!analyticsRes.ok) {
                    throw new Error('No fue posible cargar la actividad de audiencia')
                }

                const result: AnalyticsResponse = await analyticsRes.json()
                const heatmapHours = result?.activity_heatmap?.hours ?? []
                const heatmapRows = result?.activity_heatmap?.data ?? []

                const buckets24 = Array.from({ length: 24 }, (_, h) => ({
                    hour: `${String(h).padStart(2, '0')}:00`,
                    count: 0,
                }))

                let populatedFromMessages = false
                if (messagesRes && messagesRes.ok) {
                    const msgPayload: CommunityMessagesResponse = await messagesRes.json()
                    const msgs = msgPayload?.messages ?? []
                    for (const item of msgs) {
                        const ts = item?.message?.timestamp
                        if (!ts) continue
                        const d = new Date(ts)
                        if (!Number.isNaN(d.getTime())) {
                            const h = d.getHours()
                            buckets24[h].count += 1
                            populatedFromMessages = true
                        }
                    }
                }

                if (populatedFromMessages) {
                    setHourlyData(buckets24)
                } else if (heatmapHours.length > 0 && heatmapRows.length > 0) {
                    const summed = heatmapHours.map((label, idx) => {
                        const totalCount = heatmapRows.reduce((acc, row) => {
                            const c = row.counts?.[idx] ?? row.values?.[idx] ?? 0
                            return acc + Number(c)
                        }, 0)
                        return {
                            hour: label,
                            count: totalCount,
                        }
                    })
                    setHourlyData(summed)
                } else {
                    setHourlyData(buckets24)
                }

                setError(null)
            } catch (err) {
                setError(
                    err instanceof Error
                        ? err.message
                        : 'Error desconocido al cargar la actividad'
                )
            } finally {
                setLoading(false)
            }
        }

        void loadActivity()
    }, [refreshKey])

    const maxCount = hourlyData.reduce((max, item) => Math.max(max, item.count), 0)
    const peakPoint =
        hourlyData.find((item) => item.count === maxCount && maxCount > 0) ||
        hourlyData[0] || { hour: '19:00', count: 0 }

    return (
        <article className="c-card">
            <div className="c-card__header">
                <div>
                    <div className="c-card__title">Actividad de audiencia</div>
                    <div className="c-card__desc">
                        Mensajes promedio por hora del día.
                    </div>
                </div>
                <span className="c-pill c-pill--brand">
                    Peak {peakPoint.hour}
                </span>
            </div>

            {loading && (
                <div className="flex h-56 items-center justify-center text-sm text-slate-500">
                    Cargando actividad...
                </div>
            )}

            {error && (
                <div className="flex h-56 items-center justify-center text-sm text-red-600">
                    {error}
                </div>
            )}

            {!loading && !error && (
                <div className="c-chart c-chart--sm">
                    <ResponsiveContainer width="100%" height={220}>
                        <BarChart
                            data={hourlyData}
                            margin={{ top: 8, right: 8, left: -20, bottom: 0 }}
                        >
                            <CartesianGrid stroke="#f1f5f9" vertical={false} />
                            <XAxis
                                dataKey="hour"
                                axisLine={false}
                                tickLine={false}
                                tick={{ fontSize: 10, fill: '#94a3b8' }}
                                interval={hourlyData.length > 12 ? 2 : 0}
                            />
                            <YAxis
                                axisLine={false}
                                tickLine={false}
                                tick={{ fontSize: 11, fill: '#94a3b8' }}
                                allowDecimals={false}
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
                                formatter={(value) => [`${value} msgs`, 'Actividad']}
                            />
                            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                                {hourlyData.map((entry, idx) => {
                                    const isPeak = maxCount > 0 && entry.count === maxCount
                                    return (
                                        <Cell
                                            key={`bar-${entry.hour}-${idx}`}
                                            fill={isPeak ? '#ff7400' : '#fdba74'}
                                        />
                                    )
                                })}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </article>
    )
}

export default AudienceHeatmap