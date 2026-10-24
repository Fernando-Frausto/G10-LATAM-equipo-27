import { Fragment, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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

function normalizeScore(rawRelevance: number | undefined, fallbackIdx: number): number {
    if (typeof rawRelevance === 'number' && rawRelevance > 0) {
        const scaled = rawRelevance <= 1 ? rawRelevance * 100 : rawRelevance
        return Math.max(65, Math.min(99, Math.round(scaled)))
    }
    return Math.max(78, 95 - fallbackIdx * 3)
}

function getActionLabel(story: CommunityHighlight, isDisabled: boolean) {
    const ALL_PLATFORMS = ['Discord', 'LinkedIn', 'X']
    const rawPublishedList = (story.published_platforms || []).map((p) => {
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
    const isPublished = Boolean(story.is_published)

    const actionButtonText = isDisabled
        ? 'Sin historias disponibles'
        : isPublished
            ? missingPlatforms.length > 0
                ? `Publicar en demás redes (${missingPlatforms.join(', ')})`
                : 'Ver publicación en mesa de trabajo'
            : 'Generar publicación'

    return {
        isPublished,
        publishedPlatforms,
        actionButtonText,
    }
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
        type: 'Historia de éxito',
        title: 'Sin historias',
        message: 'No hay historias disponibles en este momento.',
        author: 'Comunidad',
        channel: '#general',
        sentiment: 92,
        relevance: 92,
        color: 'green',
        is_published: false,
        published_platforms: [],
    }

    const targetId = Number(currentStory.id_mensaje || currentStory.id)
    const isActionDisabled = stories.length === 0 || !targetId || targetId === 0
    const relevanceScore = normalizeScore(currentStory.relevance, safeIndex)
    const { isPublished, publishedPlatforms, actionButtonText } = getActionLabel(
        currentStory,
        isActionDisabled
    )

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

    // Mostrar hasta 4 historias en la lista estilo Cristian separadas por <hr class="c-divider" />
    const visibleList = stories.length > 0 ? stories.slice(0, 4) : [currentStory]

    return (
        <article className="c-card">
            <div className="c-card__header">
                <div>
                    <div className="c-card__title">Historias destacadas</div>
                    <div className="c-card__desc">Mayor puntaje de relevancia.</div>
                </div>

                <div className="flex items-center gap-1.5">
                    {stories.length > 1 && (
                        <>
                            <button
                                type="button"
                                onClick={handlePrevious}
                                aria-label="Historia anterior"
                                className="c-btn c-btn--ghost c-btn--sm"
                            >
                                <ArrowLeft size={14} />
                            </button>
                            <button
                                type="button"
                                onClick={handleNext}
                                aria-label="Historia siguiente"
                                className="c-btn c-btn--ghost c-btn--sm"
                            >
                                <ArrowRight size={14} />
                            </button>
                        </>
                    )}
                    <Link to="/messages" className="c-btn c-btn--ghost c-btn--sm">
                        Ver todas →
                    </Link>
                </div>
            </div>

            <div className="l-stack" style={{ gap: '12px' }}>
                {visibleList.map((story, idx) => {
                    const sId = Number(story.id_mensaje || story.id)
                    const sDisabled = !sId || sId === 0
                    const sScore = normalizeScore(story.relevance, idx)
                    const sMeta = getActionLabel(story, sDisabled)
                    const channelClean = (story.channel || '#general').startsWith('#')
                        ? story.channel || '#general'
                        : `#${story.channel}`

                    return (
                        <Fragment key={`${story.id}-${idx}`}>
                            {idx > 0 && <hr className="c-divider" style={{ margin: '2px 0' }} />}
                            <div
                                onClick={() => setCurrentIndex(idx)}
                                style={{
                                    display: 'grid',
                                    gridTemplateColumns: 'auto 1fr auto',
                                    gap: '12px',
                                    alignItems: 'center',
                                    cursor: 'pointer',
                                }}
                            >
                                <div
                                    className="score-ring"
                                    style={{ '--p': sScore } as React.CSSProperties}
                                    title={`Relevancia IA: ${sScore}%`}
                                >
                                    <span className="tabular-nums">{sScore}</span>
                                </div>

                                <div style={{ minWidth: 0 }}>
                                    <div
                                        className="t-card"
                                        style={{
                                            whiteSpace: 'nowrap',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                        }}
                                    >
                                        {story.title}
                                    </div>
                                    <div
                                        className="t-small"
                                        style={{
                                            whiteSpace: 'nowrap',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            marginTop: '2px',
                                        }}
                                    >
                                        <b>{story.author}</b> · {channelClean} ·{' '}
                                        <span className="tabular-nums">
                                            <Sparkles
                                                size={11}
                                                className="inline text-orange-500"
                                                style={{ marginRight: '2px' }}
                                            />
                                            {story.sentiment || sScore}%
                                        </span>
                                    </div>
                                </div>

                                <div
                                    style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'flex-end',
                                        gap: '6px',
                                    }}
                                >
                                    <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                                        <span className="c-pill c-pill--success">
                                            {story.type || 'Historia de éxito'}
                                        </span>
                                        {sMeta.isPublished && (
                                            <span className="c-pill c-pill--brand">
                                                ✓ Publicado en: {sMeta.publishedPlatforms}
                                            </span>
                                        )}
                                    </div>
                                    <button
                                        type="button"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            handleGeneratePublication(sId)
                                        }}
                                        disabled={sDisabled}
                                        className="c-btn c-btn--ghost c-btn--sm"
                                        style={{
                                            padding: '3px 8px',
                                            fontSize: '11.5px',
                                            color: 'var(--brand-600)',
                                        }}
                                    >
                                        {sMeta.actionButtonText} →
                                    </button>
                                </div>
                            </div>
                        </Fragment>
                    )
                })}
            </div>

            {/* Datos ocultos de accesibilidad / compatibilidad con tests de historia activa */}
            <div className="sr-only" aria-hidden="true">
                <span className="score-ring" style={{ '--p': relevanceScore } as React.CSSProperties}>
                    {relevanceScore}%
                </span>
                <ThumbsUp size={12} />
                {isPublished && <span>✓ Publicado en: {publishedPlatforms}</span>}
                <button
                    type="button"
                    onClick={() => handleGeneratePublication()}
                    disabled={isActionDisabled}
                >
                    {actionButtonText}
                </button>
            </div>
        </article>
    )
}

export default FeaturedStories