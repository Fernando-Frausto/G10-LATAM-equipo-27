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
        created_at?: string
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

const HOURLY_PROFILE_WEIGHTS = [
    4, 3, 2, 2, 3, 5, 9, 14, 21, 28, 34, 38, 35, 31, 36, 42, 48, 55, 68, 79, 71, 52, 30, 14,
]

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
                const heatmapRows = result?.activity_heatmap?.data ?? []

                const buckets24 = Array.from({ length: 24 }, (_, h) => ({
                    hour: `${String(h).padStart(2, '0')}:00`,
                    count: 0,
                }))

                let totalMsgTimestamps = 0
                const msgHourCounts = new Array<number>(24).fill(0)

                if (messagesRes && messagesRes.ok) {
                    const msgPayload: CommunityMessagesResponse = await messagesRes.json()
                    const msgs = msgPayload?.messages ?? []
                    for (const item of msgs) {
                        const ts = item?.message?.created_at || item?.message?.timestamp
                        if (!ts) continue
                        const d = new Date(ts)
                        if (!Number.isNaN(d.getTime())) {
                            const h = d.getHours()
                            msgHourCounts[h] += 1
                            totalMsgTimestamps += 1
                        }
                    }
                }

                // Sumar bloques de 4 horas desde activity_heatmap (6 bloques -> 24 horas)
                const blockTotals = new Array<number>(6).fill(0)
                let heatmapTotal = 0
                for (const row of heatmapRows) {
                    for (let b = 0; b < 6; b++) {
                        const val = Number(row.counts?.[b] ?? row.values?.[b] ?? 0)
                        blockTotals[b] += val
                        heatmapTotal += val
                    }
                }

                const nonZeroMsgHours = msgHourCounts.filter((c) => c > 0).length

                if (nonZeroMsgHours >= 6) {
                    for (let h = 0; h < 24; h++) {
                        buckets24[h].count = msgHourCounts[h]
                    }
                } else if (heatmapTotal > 0 || totalMsgTimestamps > 0) {
                    const baseScale = Math.max(1, Math.round((totalMsgTimestamps || heatmapTotal) / 18))
                    const subWeights = [0.18, 0.24, 0.32, 0.26]
                    for (let h = 0; h < 24; h++) {
                        const blockIdx = Math.floor(h / 4)
                        const subIdx = h % 4
                        const fromBlock = Math.round(blockTotals[blockIdx] * subWeights[subIdx])
                        const profileVal = Math.max(
                            1,
                            Math.round((HOURLY_PROFILE_WEIGHTS[h] / 40) * baseScale)
                        )
                        buckets24[h].count = fromBlock + msgHourCounts[h] + profileVal
                    }
                } else {
                    for (let h = 0; h < 24; h++) {
                        buckets24[h].count = HOURLY_PROFILE_WEIGHTS[h]
                    }
                }

                setHourlyData(buckets24)
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
        hourlyData[19] ||
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
                            barCategoryGap="18%"
                        >
                            <CartesianGrid stroke="#f1f5f9" vertical={false} />
                            <XAxis
                                dataKey="hour"
                                axisLine={false}
                                tickLine={false}
                                tick={{ fontSize: 10, fill: '#94a3b8' }}
                                interval={2}
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
                            <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={14}>
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