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

function FeaturedStories() {
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
    }, [])

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

    const handleGeneratePublication = () => {
        if (isActionDisabled) return
        navigate(`/content?interaction=${targetId}`, { state: { interactionId: targetId } })
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
        <section className="mt-8">

            {/* Encabezado */}
            <div className="mb-4 flex items-center justify-between">

                <div>
                    <h3 className="text-xl font-bold text-slate-900">
                        Historias destacadas
                    </h3>

                    <p className="mt-1 text-sm text-slate-500">
                        Contenido seleccionado por el motor inteligente
                    </p>
                </div>

                <div className="flex gap-2">

                    <button
                        type="button"
                        onClick={handlePrevious}
                        disabled={stories.length <= 1}
                        aria-label="Historia anterior"
                        className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <ArrowLeft size={18} />
                    </button>

                    <button
                        type="button"
                        onClick={handleNext}
                        disabled={stories.length <= 1}
                        aria-label="Historia siguiente"
                        className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-100 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <ArrowRight size={18} />
                    </button>

                </div>

            </div>

            {/* Historia principal */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">

                <div className="flex items-start justify-between gap-6">

                    <div className="flex-1">

                        <div className="flex flex-wrap items-center gap-3">

                            <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
                                {currentStory.type}
                            </span>

                            <span className="text-xs text-slate-400">
                                Seleccionada por IA
                            </span>

                            {isPublished && (
                                <span className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                                    ✓ Publicado en: {publishedPlatforms}
                                </span>
                            )}

                        </div>

                        <h4 className="mt-4 text-xl font-bold text-slate-900">
                            {currentStory.title}
                        </h4>

                        <p className="mt-3 max-w-3xl text-slate-600">
                            "{currentStory.message}"
                        </p>

                        <p className="mt-4 text-sm font-medium text-slate-500">
                            — {currentStory.author}
                        </p>

                    </div>

                    {/* Métricas y Score Ring */}
                    <div className="hidden items-center gap-4 md:flex">

                        <div className="rounded-xl bg-slate-50 p-4 text-center">
                            <Sparkles
                                size={18}
                                className="mx-auto text-orange-500"
                            />

                            <p className="mt-2 text-lg font-bold text-slate-900 tabular-nums">
                                {currentStory.sentiment}%
                            </p>

                            <p className="text-xs text-slate-400">
                                Sentimiento
                            </p>
                        </div>

                        <div className="flex flex-col items-center justify-center rounded-xl bg-slate-50 px-4 py-3 text-center">
                            <div
                                className="score-ring"
                                style={{ '--p': relevanceScore } as React.CSSProperties}
                                title={`Relevancia IA: ${relevanceScore}%`}
                            >
                                <span className="tabular-nums">{relevanceScore}%</span>
                            </div>

                            <p className="mt-1.5 flex items-center gap-1 text-xs text-slate-400">
                                <ThumbsUp size={12} className="text-orange-500" />
                                <span>Relevancia</span>
                            </p>
                        </div>

                    </div>

                </div>

                {/* Acciones */}
                <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">

                    <button
                        type="button"
                        onClick={handleGeneratePublication}
                        disabled={isActionDisabled}
                        className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {actionButtonText}
                    </button>

                </div>

            </div>

            {/* Indicadores */}
            <div className="mt-4 flex justify-center gap-2">

                {stories.map((_, index) => (
                    <button
                        key={index}
                        type="button"
                        onClick={() => setCurrentIndex(index)}
                        aria-label={`Ver historia ${index + 1}`}
                        className={`h-2 rounded-full transition-all ${
                            safeIndex === index
                                ? 'w-6 bg-orange-500'
                                : 'w-2 bg-slate-300'
                        }`}
                    />
                ))}

            </div>

        </section>
    )
}

export default FeaturedStories