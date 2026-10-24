import { useId, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

export interface KpiTrend {
    value: string
    direction?: 'up' | 'down' | 'neutral'
    label?: string
}

export interface KpiCardProps {
    title: string
    value: string
    description?: ReactNode
    icon: ReactNode
    iconKind?: '' | 'indigo' | 'emerald' | 'amber' | 'sky' | 'success' | 'danger' | 'info' | 'accent' | 'neutral'
    trend?: KpiTrend
    actionLink?: {
        label: string
        to: string
    }
    spark?: boolean
    sparkData?: number[]
    sparkColor?: string
}

function buildSparkPaths(values: number[], width = 300, height = 36) {
    const safeValues =
        values && values.length >= 2
            ? values
            : values && values.length === 1
              ? [values[0], values[0]]
              : [10, 12, 11, 14, 13, 16, 18]

    const min = Math.min(...safeValues)
    const max = Math.max(...safeValues)
    const span = max - min || 1
    const pad = 4

    const pts: Array<[number, number]> = safeValues.map((v, i) => {
        const x = (i / (safeValues.length - 1)) * width
        const y = height - pad - ((v - min) / span) * (height - pad * 2)
        return [Number(x.toFixed(1)), Number(y.toFixed(1))]
    })

    let linePath = `M ${pts[0][0]} ${pts[0][1]}`
    for (let i = 0; i < pts.length - 1; i++) {
        const [x0, y0] = pts[i]
        const [x1, y1] = pts[i + 1]
        const cpx = Number(((x0 + x1) / 2).toFixed(1))
        linePath += ` C ${cpx} ${y0}, ${cpx} ${y1}, ${x1} ${y1}`
    }

    const areaPath = `${linePath} L ${width} ${height} L 0 ${height} Z`
    return { linePath, areaPath }
}

function KpiCard({
    title,
    value,
    description,
    icon,
    iconKind = '',
    trend,
    actionLink,
    spark = true,
    sparkData,
    sparkColor = '#ff7400',
}: KpiCardProps) {
    const rawId = useId()
    const gradId = `spark-grad-${rawId.replace(/[^a-zA-Z0-9_-]/g, '')}`
    const { linePath, areaPath } = buildSparkPaths(sparkData || [10, 13, 12, 15, 14, 17, 19])

    const iconBoxClass = iconKind ? `c-iconbox c-iconbox--${iconKind}` : 'c-iconbox'

    return (
        <article className="c-card">
            <div className="c-stat">
                <div>
                    <div className="c-stat__label">{title}</div>
                    <div className="c-stat__value t-kpi tabular-nums">{value}</div>
                    <div className="c-stat__meta">
                        {trend ? (
                            <>
                                <span
                                    className={`c-trend ${
                                        trend.direction === 'down'
                                            ? 'c-trend--down'
                                            : trend.direction === 'neutral'
                                              ? 'c-trend--neutral'
                                              : 'c-trend--up'
                                    }`}
                                >
                                    {trend.direction === 'down' ? (
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                            <polyline points="6 9 12 15 18 9" />
                                        </svg>
                                    ) : trend.direction === 'neutral' ? null : (
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                            <polyline points="18 15 12 9 6 15" />
                                        </svg>
                                    )}
                                    {trend.value}
                                </span>
                                {trend.label && <span>{trend.label}</span>}
                            </>
                        ) : actionLink ? (
                            <Link
                                to={actionLink.to}
                                style={{ color: 'var(--brand-600)', fontWeight: 600 }}
                            >
                                {actionLink.label}
                            </Link>
                        ) : (
                            description && <span>{description}</span>
                        )}
                    </div>
                </div>

                <span className={iconBoxClass} aria-hidden="true">
                    {icon}
                </span>
            </div>

            {spark && (
                <div className="c-stat__spark" aria-hidden="true">
                    <svg viewBox="0 0 300 36" preserveAspectRatio="none">
                        <defs>
                            <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor={sparkColor} stopOpacity="0.22" />
                                <stop offset="100%" stopColor={sparkColor} stopOpacity="0" />
                            </linearGradient>
                        </defs>
                        <path d={areaPath} fill={`url(#${gradId})`} />
                        <path
                            d={linePath}
                            fill="none"
                            stroke={sparkColor}
                            strokeWidth="1.75"
                            strokeLinecap="round"
                        />
                    </svg>
                </div>
            )}
        </article>
    )
}

export default KpiCard