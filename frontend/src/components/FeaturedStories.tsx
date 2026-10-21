import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    ArrowLeft,
    ArrowRight,
    Sparkles,
    ThumbsUp,
} from 'lucide-react'

import { mockCommunityData } from '../data/mockCommunityData'
import { getCommunityLiveSummary, type CommunityHighlight } from '../api/communityLive'

interface FeaturedStoriesProps {
    refreshKey?: number
}

function FeaturedStories({ refreshKey = 0 }: FeaturedStoriesProps) {
    const navigate = useNavigate()
    const [stories, setStories] = useState<CommunityHighlight[]>(
        mockCommunityData.highlights.map((h) => ({ ...h, color: h.color || 'green' }))
    )
    const [currentIndex, setCurrentIndex] = useState(0)

    useEffect(() => {
        let isMounted = true
        getCommunityLiveSummary().then((summary) => {
            if (isMounted && summary.highlights.length > 0) {
                setStories(summary.highlights)
            }
        })
        return () => {
            isMounted = false
        }
    }, [refreshKey])

    const safeIndex = stories.length > 0 ? Math.min(currentIndex, stories.length - 1) : 0
    const currentStory = stories[safeIndex] || {
        id: 0,
        type: 'Historia destacada',
        title: 'Sin historias',
        message: 'No hay historias disponibles en este momento.',
        author: 'Comunidad',
        channel: '#general',
        sentiment: 0,
        relevance: 0,
        color: 'green',
        is_published: false,
        published_platforms: [],
    }

    const targetId = Number(currentStory.id_mensaje || currentStory.id)
    const isActionDisabled = stories.length === 0 || !targetId || targetId === 0
    const isPublished = Boolean(currentStory.is_published)
    const relevanceScore = Math.max(
        0,
        Math.min(
            100,
            Math.round(
                typeof currentStory.relevance === 'number'
                    ? currentStory.relevance <= 1 && currentStory.relevance > 0
                        ? currentStory.relevance * 100
                        : currentStory.relevance
                    : 0
            )
        )
    )

    const ALL_PLATFORMS = ['Discord', 'LinkedIn', 'X']
    const rawPublishedList = (currentStory.published_platforms || []).map((p) => {
        const lower = p.toLowerCase()
        if (lower === 'discord') return 'Discord'
        if (lower === 'linkedin') return 'LinkedIn'
        if (lower === 'x' || lower === 'twitter') return 'X'
        return p
    })
    const canonicalPublished = ALL_PLATFORMS.filter((p) => rawPublishedList.includes(p))
    const effectivePublished = canonicalPublished.length > 0 ? canonicalPublished : ['Discord']
    const missingPlatforms = ALL_PLATFORMS.filter((p) => !effectivePublished.includes(p))
    const publishedPlatforms = effectivePublished.join(', ')

    const actionButtonText = isActionDisabled
        ? 'Sin historias disponibles'
        : isPublished
            ? missingPlatforms.length > 0
                ? `Publicar en demás redes (${missingPlatforms.join(', ')})`
                : 'Ver publicación en mesa de trabajo'
            : 'Generar publicación'

    const handleGeneratePublication = (customId?: number) => {
        const finalId = customId ?? targetId
        if (!finalId || finalId === 0) return
        navigate(`/content?interaction=${finalId}`, { state: { interactionId: finalId } })
    }

    const handlePrevious = () => {
        setCurrentIndex((previousIndex) =>
            previousIndex === 0
                ? stories.length - 1
                : previousIndex - 1
        )
    }

    const handleNext = () => {
        setCurrentIndex((previousIndex) =>
            previousIndex === stories.length - 1
                ? 0
                : previousIndex + 1
        )
    }

    return (
        <article className="c-card">
            <div className="c-card__header">
                <div>
                    <div className="c-card__title">Historias destacadas</div>
                    <div className="c-card__desc">Mayor puntaje de relevancia.</div>
                </div>

                <div className="flex items-center gap-1.5">
                    <button
                        type="button"
                        onClick={handlePrevious}
                        disabled={stories.length <= 1}
                        aria-label="Historia anterior"
                        className="c-btn c-btn--secondary c-btn--sm"
                    >
                        <ArrowLeft size={14} />
                    </button>
                    <button
                        type="button"
                        onClick={handleNext}
                        disabled={stories.length <= 1}
                        aria-label="Historia siguiente"
                        className="c-btn c-btn--secondary c-btn--sm"
                    >
                        <ArrowRight size={14} />
                    </button>
                </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {/* Tarjeta activa destacada estilo CloudEdTech */}
                <div
                    style={{
                        display: 'flex',
                        gap: '12px',
                        padding: '12px',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '10px',
                        background: 'var(--bg-subtle)',
                        alignItems: 'flex-start',
                    }}
                >
                    <div
                        className="score-ring"
                        style={{ '--p': relevanceScore } as React.CSSProperties}
                        title={`Relevancia IA: ${relevanceScore}%`}
                    >
                        <span className="tabular-nums">{relevanceScore}%</span>
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                flexWrap: 'wrap',
                                marginBottom: '4px',
                            }}
                        >
                            <span className="c-pill c-pill--brand">{currentStory.type}</span>
                            <span
                                className="c-pill"
                                title="Sentimiento positivo"
                                style={{ gap: '4px' }}
                            >
                                <Sparkles size={11} className="text-orange-500" />
                                <span className="tabular-nums">{currentStory.sentiment}%</span>
                            </span>
                            <span
                                className="c-pill"
                                title="Relevancia IA"
                                style={{ gap: '4px' }}
                            >
                                <ThumbsUp size={11} className="text-orange-500" />
                                <span>IA</span>
                            </span>
                            {isPublished && (
                                <span className="c-pill c-pill--success">
                                    ✓ Publicado en: {publishedPlatforms}
                                </span>
                            )}
                        </div>

                        <div
                            style={{
                                fontSize: '13.5px',
                                fontWeight: 600,
                                color: 'var(--text-primary)',
                                lineHeight: 1.35,
                            }}
                        >
                            {currentStory.title}
                        </div>

                        <p
                            style={{
                                marginTop: '4px',
                                fontSize: '12.5px',
                                color: 'var(--text-secondary)',
                                lineHeight: 1.45,
                            }}
                        >
                            "{currentStory.message}"
                        </p>

                        <div
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: '8px',
                                marginTop: '10px',
                                flexWrap: 'wrap',
                            }}
                        >
                            <span style={{ fontSize: '11.5px', color: 'var(--text-muted)' }}>
                                {currentStory.author} · {currentStory.channel || '#general'}
                            </span>

                            <button
                                type="button"
                                onClick={() => handleGeneratePublication()}
                                disabled={isActionDisabled}
                                className="c-btn c-btn--primary c-btn--sm"
                            >
                                {actionButtonText}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Lista rápida de las demás historias destacadas (si hay más de 1) */}
                {stories.slice(0, 3).map((s, idx) => {
                    if (idx === safeIndex) return null
                    const sScore = Math.max(
                        0,
                        Math.min(
                            100,
                            Math.round(
                                typeof s.relevance === 'number'
                                    ? s.relevance <= 1 && s.relevance > 0
                                        ? s.relevance * 100
                                        : s.relevance
                                    : 0
                            )
                        )
                    )
                    return (
                        <div
                            key={`${s.id}-${idx}`}
                            onClick={() => setCurrentIndex(idx)}
                            style={{
                                display: 'flex',
                                gap: '12px',
                                padding: '10px 12px',
                                border: '1px solid var(--border-subtle)',
                                borderRadius: '10px',
                                alignItems: 'center',
                                cursor: 'pointer',
                                background: 'var(--bg-surface)',
                            }}
                        >
                            <div
                                className="score-ring"
                                style={{ '--p': sScore } as React.CSSProperties}
                            >
                                <span className="tabular-nums">{sScore}</span>
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div
                                    style={{
                                        fontSize: '13px',
                                        fontWeight: 600,
                                        color: 'var(--text-primary)',
                                        whiteSpace: 'nowrap',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                    }}
                                >
                                    {s.title}
                                </div>
                                <div
                                    style={{
                                        fontSize: '11.5px',
                                        color: 'var(--text-muted)',
                                        marginTop: '2px',
                                    }}
                                >
                                    {s.author} · {s.channel || '#general'}
                                </div>
                            </div>
                            <span className="c-pill c-pill--brand">{s.type}</span>
                        </div>
                    )
                })}
            </div>
        </article>
    )
}

export default FeaturedStories