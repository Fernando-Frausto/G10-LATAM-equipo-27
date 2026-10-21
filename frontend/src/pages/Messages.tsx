import {
    AlertCircle,
    AlertTriangle,
    Bot,
    ChevronRight,
    Clock3,
    Copy,
    Inbox,
    MessageSquare,
    RefreshCw,
    RotateCcw,
    Search,
    Server,
    ShieldAlert,
    Smile,
    Sparkles,
    Star,
    ThumbsUp,
    X,
} from 'lucide-react'

import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import KpiCard from '../components/KpiCard'
import { updateMessageCuration } from '../api/messageCuration'
import { syncDiscord } from '../api/discordSync'
import { evaluateSingleMessage } from '../api/communityLive'

type ApiMessage = {
    message: {
        interaction_id: number
        platform: string
        guild_id: string
        guild_name: string
        channel_id: string
        channel_name: string
        message_id: string
        author_id: string
        author_name: string
        content: string
        created_at: string
    }
    analysis: {
        sentiment: 'positive' | 'neutral' | 'negative'
        sentiment_score: number
        relevance: number
        curation_status: CurationStatus
        workflow_stage: string
        topic: string
        keywords: string[]
        highlight: boolean
        is_published?: boolean
        published_platforms?: string[]
    }
}

type MessagesApiResponse = {
    total: number
    omitted_bots_count?: number
    real_messages_count?: number
    messages: ApiMessage[]
}

type CurationStatus = 'pending' | 'curated' | 'discarded'

type MessageItem = {
    id: string
    interactionId: number
    workflowStage: string
    initials: string
    author: string
    guild: string
    channel: string
    time: string
    rawDate: Date
    message: string
    sentiment: 'positive' | 'neutral' | 'negative'
    sentimentLabel: string
    sentimentScore: number
    topic: string
    keywords: string[]
    classification: string
    relevance: number
    highlight: boolean
    isAnalyzed: boolean
    isPublished?: boolean
    publishedPlatforms?: string[]
}

type AiModel = {
    id: string
    provider: string
    name: string
    model: string
    module: string
    available: boolean
}

const DEFAULT_AI_MODELS: AiModel[] = [
    { id: 'groq-llama', provider: 'Groq', name: 'Groq (Llama 3.3)', model: 'llama-3.3-70b-versatile', module: 'cerebro_ia', available: true },
    { id: 'google-gemma', provider: 'Google', name: 'Google Gemma 4', model: 'gemma-4-31b-it', module: 'cerebro_ia_gemma_4', available: true },
    { id: 'google-gemini', provider: 'Google', name: 'Google Gemini Flash Lite', model: 'gemini-2.5-flash-lite', module: 'cerebro_ia_gemini_flash', available: true },
]

const API_BASE_URL =
    (import.meta.env.VITE_API_URL || import.meta.env.VITE_MOTOR_API_URL || 'http://127.0.0.1:8002').replace(/\/$/, '')

function Messages() {
    const navigate = useNavigate()

    const [apiData, setApiData] = useState<MessagesApiResponse>({
        total: 0,
        omitted_bots_count: 0,
        real_messages_count: 0,
        messages: [],
    })

    const [searchTerm, setSearchTerm] = useState('')
    const [channelFilter, setChannelFilter] = useState('all')
    const [sentimentFilter, setSentimentFilter] = useState('all')
    const [topicFilter, setTopicFilter] = useState('all')
    const [classificationFilter, setClassificationFilter] = useState('all')
    const [timeFilter, setTimeFilter] = useState('all')
    const [curationFilter, setCurationFilter] = useState('all')
    const [aiModels, setAiModels] = useState<AiModel[]>(DEFAULT_AI_MODELS)
    const [selectedAiBrain, setSelectedAiBrain] = useState<string>('Groq (Llama 3.3)')
    const [dateFrom, setDateFrom] = useState<string>('')
    const [dateTo, setDateTo] = useState<string>('')
    const [batchLimit, setBatchLimit] = useState<number>(5)
    const [isEvaluatingBatch, setIsEvaluatingBatch] = useState<boolean>(false)
    const [batchEvalMessage, setBatchEvalMessage] = useState<{ type: 'success' | 'error' | 'warning'; text: string } | null>(null)
    const [isSyncingDiscord, setIsSyncingDiscord] = useState<boolean>(false)
    const [syncFeedbackMessage, setSyncFeedbackMessage] = useState<{
        type: 'success' | 'error' | 'warning'
        text: string
    } | null>(null)
    const [curationStatus, setCurationStatus] = useState<
        Record<string, CurationStatus>
    >({})
    const [savingCurationId, setSavingCurationId] = useState<string | null>(null)
    const [curationError, setCurationError] = useState<string | null>(null)
    const [apiConnected, setApiConnected] = useState(false)

    const loadMessages = async () => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/api/community/messages`
            )

            if (!response.ok) {
                throw new Error(`Error HTTP ${response.status}`)
            }

            const data: MessagesApiResponse = await response.json()

            setApiData(data)
            setCurationStatus(
                Object.fromEntries(
                    data.messages.map(({ message, analysis }) => [
                        message.message_id,
                        analysis.curation_status || 'pending',
                    ]),
                ),
            )
            setApiConnected(true)
        } catch (error) {
            console.error('Error cargando mensajes:', error)
            setApiConnected(false)
        }
    }

    useEffect(() => {
        loadMessages()

        const interval = window.setInterval(loadMessages, 5000)

        return () => {
            window.clearInterval(interval)
        }
    }, [])

    useEffect(() => {
        const loadAiModels = async () => {
            try {
                const resp = await fetch(`${API_BASE_URL}/api/v1/ai/models`)
                if (resp.ok) {
                    const data: AiModel[] = await resp.json()
                    if (Array.isArray(data) && data.length > 0) {
                        setAiModels(data)
                    }
                }
            } catch (error) {
                console.error('No fue posible cargar los modelos de IA:', error)
            }
        }

        loadAiModels()
    }, [])

    const messageItems: MessageItem[] = useMemo(
        () =>
            apiData.messages.map(({ message, analysis }) => {
                const author = message.author_name || 'Usuario'

                const initials =
                    author
                        .split(/[\s._-]+/)
                        .filter(Boolean)
                        .slice(0, 2)
                        .map((part) => part[0]?.toUpperCase())
                        .join('') || 'U'

                const createdAt = new Date(message.created_at)

                const sentimentLabel = {
                    positive: 'Positivo',
                    neutral: 'Neutral',
                    negative: 'Negativo',
                }[analysis.sentiment]

                const rawChannel = (message.channel_name || '').replace(/^#/, '').trim()
                const normalizedChannel =
                    rawChannel.toLowerCase() === 'preguntas' || rawChannel.toLowerCase() === 'dudas'
                        ? 'faq'
                        : rawChannel || 'general'

                const isPublished = Boolean(analysis.is_published)
                const publishedPlatforms = Array.isArray(analysis.published_platforms)
                    ? analysis.published_platforms
                    : []

                return {
                    id: message.message_id,
                    interactionId: message.interaction_id,
                    workflowStage: analysis.workflow_stage,
                    initials,
                    author,
                    guild: message.guild_name || 'Discord',
                    channel: normalizedChannel,
                    time: createdAt.toLocaleString('es-CO'),
                    rawDate: createdAt,
                    message: message.content,
                    sentiment: analysis.sentiment,
                    sentimentLabel,
                    sentimentScore: Math.round(Math.max(0, Math.min(1, analysis.sentiment_score)) * 100),
                    topic: analysis.topic,
                    keywords: analysis.keywords || [],
                    classification: analysis.highlight
                        ? 'Destacado'
                        : 'Mensaje',
                    relevance: Math.max(0, Math.min(100, analysis.relevance)),
                    highlight: analysis.highlight,
                    isAnalyzed: Boolean(
                        isPublished ||
                        analysis.workflow_stage === 'publicado' ||
                        (analysis.workflow_stage !== 'ingesta' &&
                            analysis.workflow_stage !== 'en_ingesta' &&
                            (analysis.workflow_stage === 'en_analisis' ||
                                analysis.workflow_stage === 'en_redaccion' ||
                                analysis.workflow_stage === 'en_aprobacion' ||
                                analysis.relevance > 0))
                    ),
                    isPublished,
                    publishedPlatforms,
                }
            }),
        [apiData.messages]
    )

    const PREFERRED_CHANNELS_ORDER = useMemo(
        () => [
            'general',
            'faq',
            'pqrs',
            'chat-egresados',
            'oportunidades-laborales',
        ],
        []
    )

    const channels = useMemo(() => {
        const detected = Array.from(
            new Set(
                messageItems
                    .map((message) => (message.channel || '').replace(/^#/, '').trim())
                    .filter(
                        (ch) =>
                            ch &&
                            !/^\d+$/.test(ch) &&
                            !['preguntas', 'dudas', 'anuncios'].includes(ch.toLowerCase())
                    )
            )
        )
        const allChannels = Array.from(new Set([...PREFERRED_CHANNELS_ORDER, ...detected]))
            .filter((ch) => !['preguntas', 'dudas', 'anuncios'].includes(ch.toLowerCase()))

        return allChannels.sort((a, b) => {
            const cleanA = a.toLowerCase()
            const cleanB = b.toLowerCase()
            const indexA = PREFERRED_CHANNELS_ORDER.indexOf(cleanA)
            const indexB = PREFERRED_CHANNELS_ORDER.indexOf(cleanB)
            if (indexA !== -1 && indexB !== -1) return indexA - indexB
            if (indexA !== -1) return -1
            if (indexB !== -1) return 1
            return cleanA.localeCompare(cleanB)
        })
    }, [messageItems, PREFERRED_CHANNELS_ORDER])

    const topics = useMemo(() => {
        const set = new Set<string>()
        for (const msg of messageItems) {
            if (msg.isAnalyzed && msg.topic && msg.topic.trim() && msg.topic.toLowerCase() !== 'sin tema') {
                set.add(msg.topic.trim())
            }
        }
        return Array.from(set).sort((a, b) => a.localeCompare(b))
    }, [messageItems])

    const classificationChips = useMemo(() => {
        const visibleItems = messageItems.filter(
            (m) => !m.author.toLowerCase().includes('cloudedtech community bot')
        )
        const classes = Array.from(new Set(visibleItems.map((m) => m.classification)))
        return [
            ['all', 'Todas', visibleItems.length] as const,
            ...classes.map(
                (cls) =>
                    [
                        cls,
                        cls,
                        visibleItems.filter((m) => m.classification === cls).length,
                    ] as const
            ),
        ]
    }, [messageItems])

    const getAvatarTone = (name: string) => {
        const tones = ['', 'c-avatar--indigo', 'c-avatar--emerald', 'c-avatar--purple', 'c-avatar--slate']
        const sum = Array.from(name || 'U').reduce((acc, ch) => acc + ch.charCodeAt(0), 0)
        return tones[sum % tones.length]
    }

    const analyzedCount = useMemo(
        () => messageItems.filter((message) => message.isAnalyzed).length,
        [messageItems]
    )

    const positiveMessages = useMemo(
        () =>
            messageItems.filter(
                (message) => message.isAnalyzed && message.sentiment === 'positive'
            ).length,
        [messageItems]
    )

    const questionMessages = messageItems.filter((message) =>
        message.message.trim().endsWith('?')
    ).length

    const highlightedMessages = messageItems.filter(
        (message) => message.highlight
    ).length



    const matchesTimeFilter = (date: Date) => {
        // 1. Rango específico seleccionado por el usuario en 'Desde' y 'Hasta'
        if (dateFrom) {
            const fromTimestamp = new Date(`${dateFrom}T00:00:00`).getTime()
            if (!isNaN(fromTimestamp) && date.getTime() < fromTimestamp) {
                return false
            }
        }

        if (dateTo) {
            const toTimestamp = new Date(`${dateTo}T23:59:59.999`).getTime()
            if (!isNaN(toTimestamp) && date.getTime() > toTimestamp) {
                return false
            }
        }

        // 2. Filtro rápido de botones temporales (24h, semana, mes)
        if (timeFilter === 'all') return true

        const now = new Date()
        const difference = now.getTime() - date.getTime()
        const hours = difference / (1000 * 60 * 60)

        if (timeFilter === '24h') return hours <= 24
        if (timeFilter === 'week') return hours <= 24 * 7
        if (timeFilter === 'month') return hours <= 24 * 30

        return true
    }

    const filteredMessages = messageItems.filter((message) => {
        // Evitar que las respuestas del bot reingresen al flujo editorial.
        if (message.author.toLowerCase().includes('cloudedtech community bot')) {
            return false
        }

        const isMsgPublished = Boolean(message.isPublished) || message.workflowStage === 'publicado'
        const currentCuration = curationStatus[message.id] ?? 'pending'

        // Precedencia humana (HITL):
        // Es descartado si el operador lo descartó explícitamente (curation === 'discarded')
        // O si la IA lo analizó con relevancia < 70, SIEMPRE Y CUANDO el operador NO lo haya curado ni restaurado a 'pending'
        // Y NUNCA si el mensaje ya fue publicado
        const isDiscarded =
            !isMsgPublished &&
            (currentCuration === 'discarded' ||
                (message.isAnalyzed &&
                    message.relevance < 70 &&
                    currentCuration !== 'curated' &&
                    currentCuration !== 'pending'))

        const isCompleted =
            !isDiscarded &&
            (isMsgPublished ||
                currentCuration === 'curated' ||
                message.workflowStage === 'en_aprobacion' ||
                message.workflowStage === 'en_redaccion')

        const isPendingEval =
            !isDiscarded &&
            !isCompleted &&
            (!message.isAnalyzed ||
                message.workflowStage === 'ingesta' ||
                message.workflowStage === 'en_ingesta')

        const isPendingCopy = !isDiscarded && !isCompleted && !isPendingEval

        // Filtro unificado por Estado del mensaje
        if (curationFilter === 'descartados') {
            if (!isDiscarded) return false
        } else if (curationFilter === 'completos') {
            if (!isCompleted) return false
        } else if (curationFilter === 'pending_copy') {
            if (!isPendingCopy) return false
        } else if (curationFilter === 'pending_eval') {
            if (!isPendingEval) return false
        }
        // Cuando curationFilter === 'all', pasan todos los mensajes

        const search = searchTerm.trim().toLowerCase()

        const matchesSearch =
            !search ||
            message.author.toLowerCase().includes(search) ||
            message.message.toLowerCase().includes(search) ||
            message.topic.toLowerCase().includes(search) ||
            message.channel.toLowerCase().includes(search) ||
            message.keywords.some((keyword) =>
                keyword.toLowerCase().includes(search)
            )

        const matchesChannel =
            channelFilter === 'all' ||
            message.channel === channelFilter ||
            (message.channel || '').replace(/^#/, '').toLowerCase() ===
                channelFilter.replace(/^#/, '').toLowerCase()

        const matchesSentiment =
            sentimentFilter === 'all' ||
            message.sentiment === sentimentFilter

        const matchesTopic =
            topicFilter === 'all' ||
            message.topic === topicFilter

        const matchesClassification =
            classificationFilter === 'all' ||
            message.classification === classificationFilter

        return (
            matchesSearch &&
            matchesChannel &&
            matchesSentiment &&
            matchesTopic &&
            matchesClassification &&
            matchesTimeFilter(message.rawDate)
        )
    })

    const markCuration = async (
        message: MessageItem,
        status: CurationStatus,
    ) => {
        if (savingCurationId !== null) return

        setSavingCurationId(message.id)
        setCurationError(null)

        try {
            await updateMessageCuration(message.interactionId, status)
            setCurationStatus((current) => ({
                ...current,
                [message.id]: status,
            }))
        } catch (error) {
            setCurationError(
                error instanceof Error
                    ? error.message
                    : 'No se pudo guardar la curaduría',
            )
        } finally {
            setSavingCurationId(null)
        }
    }

    const [evaluatingMessageId, setEvaluatingMessageId] = useState<number | null>(null)

    const handleEvaluateSingleMessage = async (message: MessageItem) => {
        if (evaluatingMessageId !== null) return

        setEvaluatingMessageId(message.interactionId)
        if (selectedAiBrain.toLowerCase().includes('gemma')) {
            setSyncFeedbackMessage({
                type: 'warning',
                text: `⏳ Evaluando mensaje con Google Gemma 4... Este modelo denso toma entre 30 y 45 segundos. Por favor espera sin cerrar la ventana.`,
            })
        } else {
            setSyncFeedbackMessage(null)
        }
        try {
            const res = await evaluateSingleMessage(message.interactionId, selectedAiBrain)
            await loadMessages()
            if (res.relevancia >= 70) {
                setSyncFeedbackMessage({
                    type: 'success',
                    text: `✅ Mensaje de @${message.author} evaluado (${res.relevancia}% relevancia · ${res.sentimiento}). Pasó a 'Pendientes de Copy' para redacción.`,
                })
            } else {
                setSyncFeedbackMessage({
                    type: 'warning',
                    text: `⚠️ Mensaje de @${message.author} evaluado con ${res.relevancia}% de relevancia (< 70% requerido para Copy). Se movió automáticamente a 'Etapa: Descartados'.`,
                })
            }
        } catch (error) {
            console.error('Error al evaluar mensaje con IA:', error)
            const rawMsg = error instanceof Error ? error.message : 'Error al evaluar el mensaje con IA.'
            const isFetchErr = rawMsg.includes('Failed to fetch')
            setSyncFeedbackMessage({
                type: 'error',
                text: isFetchErr
                    ? `❌ Error de conexión (Failed to fetch): No se pudo comunicar con el backend local (${API_BASE_URL}). Si estás viendo esto en Netlify, accede desde http://localhost:5173/messages y confirma que el backend esté ejecutándose en la terminal.`
                    : `❌ ${rawMsg}`,
            })
        } finally {
            setEvaluatingMessageId(null)
        }
    }

    const batchEvalMetrics = useMemo(() => {
        const isDateRangeInverted = Boolean(dateFrom && dateTo && dateFrom > dateTo)
        if (isDateRangeInverted) {
            return {
                isDateRangeInverted: true,
                totalInRange: 0,
                pendingInRange: 0,
                pendingEvalInRange: 0,
                pendingCopyInRange: 0,
                completedInRange: 0,
                discardedInRange: 0,
                evaluableCount: 0,
            }
        }

        const fromTimestamp = dateFrom ? new Date(`${dateFrom}T00:00:00`).getTime() : null
        const toTimestamp = dateTo ? new Date(`${dateTo}T23:59:59.999`).getTime() : null

        let totalInRange = 0
        let pendingEvalInRange = 0
        let pendingCopyInRange = 0
        let completedInRange = 0
        let discardedInRange = 0

        for (const msg of messageItems) {
            if (msg.author.toLowerCase().includes('cloudedtech community bot')) {
                continue
            }

            const msgTime = msg.rawDate.getTime()
            if (fromTimestamp !== null && !isNaN(fromTimestamp) && msgTime < fromTimestamp) {
                continue
            }
            if (toTimestamp !== null && !isNaN(toTimestamp) && msgTime > toTimestamp) {
                continue
            }

            totalInRange++

            const isMsgPublished = Boolean(msg.isPublished) || msg.workflowStage === 'publicado'
            const st = curationStatus[msg.id] ?? 'pending'
            if (!isMsgPublished && st === 'discarded') {
                discardedInRange++
                continue
            }

            const isCompleted =
                isMsgPublished ||
                st === 'curated' ||
                msg.workflowStage === 'en_aprobacion' ||
                msg.workflowStage === 'en_redaccion'

            const isPendingEval =
                !isCompleted &&
                (!msg.isAnalyzed ||
                    msg.workflowStage === 'ingesta' ||
                    msg.workflowStage === 'en_ingesta')

            if (isCompleted) {
                completedInRange++
            } else if (isPendingEval) {
                pendingEvalInRange++
            } else {
                pendingCopyInRange++
            }
        }

        const pendingInRange = pendingEvalInRange
        const evaluableCount = pendingEvalInRange

        return {
            isDateRangeInverted: false,
            totalInRange,
            pendingInRange,
            pendingEvalInRange,
            pendingCopyInRange,
            completedInRange,
            discardedInRange,
            evaluableCount,
        }
    }, [messageItems, dateFrom, dateTo, curationStatus])

    useEffect(() => {
        const count = batchEvalMetrics.evaluableCount
        if (count > 0 && count < 5) {
            setBatchLimit(count)
        } else if (count >= 5) {
            if (batchLimit !== 1 && batchLimit !== 5 && batchLimit !== 10 && batchLimit !== count) {
                setBatchLimit(5)
            }
        }
    }, [batchEvalMetrics.evaluableCount, batchLimit])

    const handleSyncDiscord = async () => {
        if (isSyncingDiscord) return

        setIsSyncingDiscord(true)
        setSyncFeedbackMessage(null)

        try {
            const resp = await syncDiscord()
            if (resp.exito) {
                const metricas = `Nuevas: ${resp.guardadas_nuevas} | Omitidas: ${resp.repetidas_omitidas} | Total: ${resp.total_recibidas}`
                setSyncFeedbackMessage({
                    type: 'success',
                    text: `✅ ${resp.mensaje || 'Sincronización exitosa'} (${metricas})`,
                })
                await loadMessages()
            } else {
                setSyncFeedbackMessage({
                    type: 'warning',
                    text: resp.mensaje || 'Respuesta de sincronización sin éxito.',
                })
            }
        } catch (error) {
            const err = error as Error & { status?: number; codigoError?: string }
            const errMsg = err.message || 'Error desconocido al sincronizar Discord'
            const isConflict = err.status === 409 || errMsg.includes('409') || errMsg.includes('Sincronizaci')
            const isRateLimit =
                err.status === 429 ||
                err.codigoError === 'RATE_LIMIT_CLOUDFLARE_1015' ||
                errMsg.includes('429') ||
                errMsg.includes('1015') ||
                errMsg.toLowerCase().includes('rate limit') ||
                errMsg.toLowerCase().includes('too many requests')

            if (isConflict) {
                setSyncFeedbackMessage({
                    type: 'warning',
                    text: '⏳ Sincronización en curso. Por favor espera a que finalice el proceso anterior.',
                })
            } else if (isRateLimit) {
                setSyncFeedbackMessage({
                    type: 'warning',
                    text: '⚠️ Discord o Cloudflare ha limitado temporalmente la IP del servidor en la nube (Error 1015 / Rate Limit). Sincroniza desde tu entorno local o intenta en unos minutos.',
                })
            } else {
                setSyncFeedbackMessage({
                    type: 'error',
                    text: `Error al sincronizar Discord: ${errMsg}`,
                })
            }
        } finally {
            setIsSyncingDiscord(false)
        }
    }

    const handleEvaluateBatch = async () => {
        if (
            isEvaluatingBatch ||
            batchEvalMetrics.evaluableCount === 0 ||
            batchEvalMetrics.isDateRangeInverted
        ) {
            return
        }

        if (batchEvalMetrics.isDateRangeInverted) {
            setBatchEvalMessage({
                type: 'error',
                text: 'La fecha "Desde" no puede ser posterior a la fecha "Hasta".',
            })
            return
        }

        setIsEvaluatingBatch(true)
        if (selectedAiBrain.toLowerCase().includes('gemma')) {
            setBatchEvalMessage({
                type: 'warning',
                text: '⏳ Evaluando lote con Google Gemma 4... Este modelo denso toma ~30-45s por mensaje. Por favor espera a que finalice.',
            })
        } else {
            setBatchEvalMessage(null)
        }

        try {
            const payload: {
                proveedor: string
                desde?: string
                hasta?: string
                solo_pendientes: boolean
                limite: number
            } = {
                proveedor: selectedAiBrain,
                solo_pendientes: true,
                limite: batchLimit,
            }
            if (dateFrom) payload.desde = dateFrom
            if (dateTo) payload.hasta = dateTo

            const resp = await fetch(`${API_BASE_URL}/api/v1/ai/evaluate-batch`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            })

            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}))
                throw new Error(errData.detail || `Error HTTP ${resp.status}`)
            }

            const result = await resp.json()
            setBatchEvalMessage({
                type: 'success',
                text: `Evaluación completada: ${result.evaluados ?? 0} mensajes evaluados exitosamente con ${result.proveedor || selectedAiBrain}.`,
            })

            await loadMessages()
        } catch (error) {
            const rawMsg = error instanceof Error ? error.message : 'Error al evaluar el lote con IA.'
            const isFetchErr = rawMsg.includes('Failed to fetch')
            setBatchEvalMessage({
                type: 'error',
                text: isFetchErr
                    ? `Error de conexión (Failed to fetch): No se pudo comunicar con el backend local (${API_BASE_URL}). Si estás en Netlify, accede desde http://localhost:5173/messages y confirma que el backend esté ejecutándose en la terminal.`
                    : rawMsg,
            })
        } finally {
            setIsEvaluatingBatch(false)
        }
    }

    const clearFilters = () => {
        setSearchTerm('')
        setChannelFilter('all')
        setSentimentFilter('all')
        setTopicFilter('all')
        setClassificationFilter('all')
        setTimeFilter('all')
        setCurationFilter('all')
        setDateFrom('')
        setDateTo('')
        setBatchEvalMessage(null)
        setSyncFeedbackMessage(null)
    }

    return (
        <div className="space-y-6">

            {/* Encabezado */}
            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight t-page t-page--xl">
                        Ingesta de mensajes
                    </h1>

                    <p className="mt-1 text-sm text-slate-500">
                        Monitoreo, análisis y curaduría de conversaciones de Discord
                    </p>
                </div>

                {/* Sección compacta: Mensajes totales recibidos, telemetría y sincronización */}
                <div className="flex flex-wrap items-center gap-3">
                    <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200/90 bg-white px-4 py-2.5 shadow-sm tabular-nums">
                        <div>
                            <div className="flex items-baseline gap-1.5">
                                <span className="text-2xl font-black tracking-tight text-slate-950">
                                    {(apiData.total || messageItems.length).toLocaleString('es-CO')}
                                </span>
                                <span className="text-xs font-semibold text-slate-500">
                                    Mensajes totales recibidos
                                </span>
                            </div>

                            <div className="flex items-center gap-1.5 text-[11px]">
                                <span
                                    className={`inline-flex items-center gap-1 font-semibold ${
                                        apiConnected
                                            ? 'text-emerald-700'
                                            : 'text-amber-700'
                                    }`}
                                >
                                    <span
                                        className={`h-1.5 w-1.5 rounded-full ${
                                            apiConnected
                                                ? 'bg-emerald-500'
                                                : 'bg-amber-500'
                                        }`}
                                    />
                                    {apiConnected
                                        ? 'Conexión a Discord activa'
                                        : 'Conexión pendiente'}
                                </span>
                                <span className="text-slate-400">· Datos en Motor IA</span>
                            </div>
                        </div>

                        <div className="hidden h-8 w-px bg-slate-200 sm:block" />

                        <div className="flex divide-x divide-slate-100 text-center">
                            <div className="px-2.5">
                                <p className="text-[10px] font-medium text-slate-400">Bots omitidos</p>
                                <p className="text-sm font-bold text-slate-600">
                                    {(apiData.omitted_bots_count ?? 0).toLocaleString('es-CO')}
                                </p>
                            </div>

                            <div className="px-2.5">
                                <p className="text-[10px] font-medium text-slate-400">Reales detectados</p>
                                <p className="text-sm font-bold text-emerald-600">
                                    {(apiData.real_messages_count ?? apiData.total ?? messageItems.length).toLocaleString('es-CO')}
                                </p>
                            </div>
                        </div>
                    </div>

                    <button
                        type="button"
                        onClick={handleSyncDiscord}
                        disabled={isSyncingDiscord}
                        className="c-btn c-btn--primary inline-flex items-center gap-2"
                        style={{ height: '2.625rem' }}
                    >
                        <RefreshCw
                            size={14}
                            className={isSyncingDiscord ? 'animate-spin' : ''}
                        />
                        <span>{isSyncingDiscord ? 'Sincronizando...' : 'Sincronizar Discord'}</span>
                    </button>
                </div>
            </div>

            {/* KPIs */}
            <div className="l-grid l-grid--4 tabular-nums" id="msg-summary">
                <KpiCard
                    title="Analizados"
                    value={analyzedCount.toLocaleString('es-CO')}
                    description="Últimos 30 días"
                    icon={<Inbox size={18} />}
                    iconKind=""
                    spark={false}
                />

                <KpiCard
                    title="Positivos"
                    value={positiveMessages.toLocaleString('es-CO')}
                    description={
                        <>
                            <b className="t-success font-semibold text-emerald-600">
                                {analyzedCount > 0
                                    ? Math.round(
                                          (positiveMessages / analyzedCount) *
                                              100
                                      )
                                    : 0}
                                %
                            </b>{' '}
                            del total
                        </>
                    }
                    icon={<Smile size={18} />}
                    iconKind="success"
                    spark={false}
                />

                <KpiCard
                    title="Preguntas"
                    value={questionMessages.toLocaleString('es-CO')}
                    description="Candidatas a FAQ"
                    icon={<MessageSquare size={18} />}
                    iconKind="info"
                    spark={false}
                />

                <KpiCard
                    title="Destacados"
                    value={highlightedMessages.toLocaleString('es-CO')}
                    description="Relevancia ≥ 85"
                    icon={<Star size={18} />}
                    iconKind=""
                    spark={false}
                />
            </div>

            {/* Feedback de Sincronización Discord */}
            {syncFeedbackMessage && (
                <div
                    role="alert"
                    className={`flex items-center justify-between rounded-xl border px-4 py-3 text-xs font-medium ${
                        syncFeedbackMessage.type === 'success'
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                            : syncFeedbackMessage.type === 'warning'
                            ? 'border-amber-200 bg-amber-50 text-amber-800'
                            : 'border-rose-200 bg-rose-50 text-rose-700'
                    }`}
                >
                    <span>{syncFeedbackMessage.text}</span>
                    <button
                        type="button"
                        onClick={() => setSyncFeedbackMessage(null)}
                        className="ml-2 text-slate-400 hover:text-slate-600"
                    >
                        <X size={14} />
                    </button>
                </div>
            )}

            {/* Panel de Evaluación IA por Lotes con Filtro de Fechas (compacto - CommunityLab DS) */}
            <section className="c-card" style={{ padding: '1rem 1.25rem' }}>
                {/* Encabezado compacto */}
                <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-purple-100 text-purple-600">
                            <Bot size={20} />
                        </div>
                        <div className="min-w-0">
                            <h3 className="text-sm font-bold text-slate-900">
                                Evaluación por Lote con Inteligencia Artificial
                            </h3>
                            <p className="text-[11px] text-slate-500">
                                Clasifica sentimiento, relevancia y temas usando los modelos del motor IA
                            </p>
                        </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5">
                        {aiModels.length > 0 && (
                            <span className="c-pill c-pill--accent tabular-nums">
                                <span className="h-1.5 w-1.5 rounded-full bg-purple-500 animate-pulse" />
                                {aiModels.length} cerebros IA disponibles
                            </span>
                        )}

                        <span className={`c-pill ${apiConnected ? 'c-pill--success' : 'c-pill--warning'}`}>
                            <span
                                className={`h-1.5 w-1.5 rounded-full ${
                                    apiConnected ? 'bg-emerald-500' : 'bg-amber-500'
                                }`}
                            />
                            {apiConnected
                                ? 'Motor de ingesta conectado'
                                : 'Esperando conexión del Motor IA'}
                        </span>
                    </div>
                </div>

                {/* Controles en una sola fila */}
                <div className="mt-3 grid grid-cols-1 items-end gap-2.5 sm:grid-cols-2 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto]">
                    {/* Selector de Cerebro IA */}
                    <div className="min-w-0">
                        <label className="mb-1 block text-[11px] font-semibold text-slate-600">
                            Cerebro IA
                        </label>
                        <select
                            value={selectedAiBrain}
                            onChange={(e) => setSelectedAiBrain(e.target.value)}
                            className="c-select"
                            style={{ padding: '0.45rem 2rem 0.45rem 0.75rem', fontSize: '0.75rem' }}
                        >
                            {aiModels.map((m) => (
                                <option key={m.id} value={m.name}>
                                    {m.name} ({m.provider})
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Fecha Desde */}
                    <div className="min-w-0">
                        <label className="mb-1 block text-[11px] font-semibold text-slate-600">
                            Desde (opcional)
                        </label>
                        <input
                            type="date"
                            value={dateFrom}
                            onChange={(e) => setDateFrom(e.target.value)}
                            className="c-input"
                            style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
                        />
                    </div>

                    {/* Fecha Hasta */}
                    <div className="min-w-0">
                        <label className="mb-1 block text-[11px] font-semibold text-slate-600">
                            Hasta (opcional)
                        </label>
                        <input
                            type="date"
                            value={dateTo}
                            onChange={(e) => setDateTo(e.target.value)}
                            className="c-input"
                            style={{ padding: '0.4rem 0.75rem', fontSize: '0.75rem' }}
                        />
                    </div>

                    {/* Selector de tamaño de lote */}
                    <div className="min-w-0">
                        <label className="mb-1 block text-[11px] font-semibold text-slate-600">
                            Tamaño del lote
                        </label>
                        <select
                            value={batchEvalMetrics.evaluableCount === 0 ? 0 : batchLimit}
                            onChange={(e) => setBatchLimit(Number(e.target.value))}
                            disabled={batchEvalMetrics.evaluableCount === 0 || isEvaluatingBatch}
                            className="c-select disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                            style={{ padding: '0.45rem 2rem 0.45rem 0.75rem', fontSize: '0.75rem' }}
                        >
                            {batchEvalMetrics.evaluableCount === 0 ? (
                                <option value={0} disabled>Sin pendientes</option>
                            ) : (
                                <>
                                    <option value={1}>1 mensaje</option>
                                    {batchEvalMetrics.evaluableCount > 1 && batchEvalMetrics.evaluableCount < 5 && (
                                        <option value={batchEvalMetrics.evaluableCount}>
                                            Evaluar todos ({batchEvalMetrics.evaluableCount})
                                        </option>
                                    )}
                                    <option value={5}>5 mensajes</option>
                                    {batchEvalMetrics.evaluableCount > 5 && batchEvalMetrics.evaluableCount < 10 && (
                                        <option value={batchEvalMetrics.evaluableCount}>
                                            Evaluar todos ({batchEvalMetrics.evaluableCount})
                                        </option>
                                    )}
                                    <option value={10}>10 mensajes</option>
                                </>
                            )}
                        </select>
                    </div>

                    {/* Botón de Acción */}
                    <button
                        type="button"
                        disabled={
                            isEvaluatingBatch ||
                            batchEvalMetrics.evaluableCount === 0 ||
                            batchEvalMetrics.isDateRangeInverted
                        }
                        onClick={handleEvaluateBatch}
                        title={
                            batchEvalMetrics.isDateRangeInverted
                                ? "La fecha 'Desde' no puede ser posterior a 'Hasta'"
                                : batchEvalMetrics.evaluableCount === 0
                                ? "No hay mensajes para evaluar con los criterios actuales"
                                : undefined
                        }
                        className="c-btn c-btn--primary inline-flex items-center justify-center gap-2 whitespace-nowrap"
                        style={{ height: '2.125rem', fontSize: '0.75rem' }}
                    >
                        <RefreshCw
                            size={14}
                            className={isEvaluatingBatch ? 'animate-spin' : ''}
                        />
                        <span>{isEvaluatingBatch ? 'Evaluando con IA...' : 'Evaluar mensajes con IA'}</span>
                    </button>
                </div>

                {selectedAiBrain.toLowerCase().includes('gemma') && (
                    <p className="mt-1.5 text-[11px] font-medium text-amber-700">
                        ⚠️ Google Gemma 4 es un modelo denso (31B) y puede demorar entre 30 y 45s. Para respuesta inmediata usa Groq.
                    </p>
                )}

                {/* Franja de estado: cobertura IA + conteos del rango */}
                <div className="mt-3 rounded-xl border border-slate-100 bg-slate-50/70 px-3 py-2">
                    {batchEvalMetrics.isDateRangeInverted ? (
                        <div
                            role="alert"
                            className="flex items-center gap-2 text-xs font-semibold text-rose-700"
                        >
                            <AlertCircle size={15} className="shrink-0 text-rose-600" />
                            <span>La fecha 'Desde' no puede ser posterior a 'Hasta'.</span>
                        </div>
                    ) : (
                        <div className="flex flex-col gap-2 xl:flex-row xl:items-center xl:gap-4">
                            {/* Medidor de Progreso de Evaluación (.c-meter) */}
                            <div className="shrink-0 xl:w-80">
                                <div className="mb-1 flex items-center justify-between gap-2 text-[11px]">
                                    <span className="font-semibold text-slate-600">
                                        Cobertura de evaluación IA en el rango seleccionado
                                    </span>
                                    <span className="font-bold text-slate-800 tabular-nums whitespace-nowrap">
                                        {Math.max(0, batchEvalMetrics.totalInRange - batchEvalMetrics.pendingEvalInRange)} / {batchEvalMetrics.totalInRange} evaluados (
                                        {batchEvalMetrics.totalInRange > 0
                                            ? Math.round(
                                                  ((batchEvalMetrics.totalInRange - batchEvalMetrics.pendingEvalInRange) /
                                                      batchEvalMetrics.totalInRange) *
                                                      100
                                              )
                                            : 0}
                                        %)
                                    </span>
                                </div>
                                <div className="c-meter">
                                    <div
                                        className="c-meter__bar"
                                        style={{
                                            width: `${
                                                batchEvalMetrics.totalInRange > 0
                                                    ? Math.min(
                                                          100,
                                                          Math.round(
                                                              ((batchEvalMetrics.totalInRange - batchEvalMetrics.pendingEvalInRange) /
                                                                  batchEvalMetrics.totalInRange) *
                                                                  100
                                                          )
                                                      )
                                                    : 0
                                            }%`,
                                        }}
                                    />
                                </div>
                            </div>

                            <div className="hidden h-8 w-px bg-slate-200 xl:block" />

                            {/* Contador reactivo e indicadores de estado */}
                            <div className="flex flex-1 flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-700 tabular-nums">
                                <span className="font-bold text-slate-900">
                                    📊 {batchEvalMetrics.totalInRange} mensajes en este rango:
                                </span>
                                <span className="inline-flex items-center gap-1 font-semibold text-amber-700">
                                    <Clock3 size={12} className="shrink-0" />
                                    <strong>{batchEvalMetrics.pendingEvalInRange}</strong> pendientes de evaluar
                                </span>
                                <span className="inline-flex items-center gap-1 font-semibold text-indigo-700">
                                    <Sparkles size={12} className="shrink-0" />
                                    <strong>{batchEvalMetrics.pendingCopyInRange}</strong> Pendientes de publicar
                                </span>
                                <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                                    <ThumbsUp size={12} className="shrink-0" />
                                    <strong>{batchEvalMetrics.completedInRange}</strong> con proceso completo
                                </span>
                                <span className="inline-flex items-center gap-1 font-semibold text-rose-700">
                                    <X size={12} className="shrink-0" />
                                    <strong>{batchEvalMetrics.discardedInRange}</strong> descartados
                                </span>
                            </div>

                            {(dateFrom || dateTo) && (
                                <button
                                    type="button"
                                    onClick={() => {
                                        setDateFrom('')
                                        setDateTo('')
                                    }}
                                    className="c-btn c-btn--secondary c-btn--sm shrink-0"
                                    title="Quitar filtro de fechas para ver todos los mensajes"
                                >
                                    <X size={12} />
                                    Mostrar todos los mensajes
                                </button>
                            )}
                        </div>
                    )}

                    {!batchEvalMetrics.isDateRangeInverted && batchEvalMetrics.evaluableCount === 0 && (
                        <div
                            role="status"
                            className="mt-1.5 flex items-center gap-1.5 text-[11px] font-medium text-amber-800"
                        >
                            <AlertTriangle size={13} className="shrink-0 text-amber-600" />
                            <span>
                                {batchEvalMetrics.totalInRange === 0
                                    ? 'Sin mensajes en este rango de fechas.'
                                    : 'Todos los mensajes de este rango ya fueron evaluados (puedes explorarlos abajo).'}
                            </span>
                        </div>
                    )}
                </div>

                {batchEvalMessage && (
                    <div
                        role="alert"
                        className={`mt-3 flex items-center justify-between rounded-xl border px-3 py-2 text-xs font-medium ${
                            batchEvalMessage.type === 'success'
                                ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                                : batchEvalMessage.type === 'warning'
                                ? 'border-amber-200 bg-amber-50 text-amber-800'
                                : 'border-rose-200 bg-rose-50 text-rose-700'
                        }`}
                    >
                        <span>{batchEvalMessage.text}</span>
                        <button
                            type="button"
                            onClick={() => setBatchEvalMessage(null)}
                            className="ml-2 text-slate-400 hover:text-slate-600"
                        >
                            <X size={14} />
                        </button>
                    </div>
                )}
            </section>

            {/* Sección unificada: Panel de filtrado de mensajes + Lista de mensajes (CommunityLab DS) */}
            <article className="c-card c-card--flush">
                <div className="c-card__section">
                    <div className="c-card__header" style={{ marginBottom: 'var(--space-4)' }}>
                        <div>
                            <h2 className="t-card">Panel de filtrado de mensajes</h2>
                            <p className="c-card__desc tabular-nums">
                                Mostrando{' '}
                                <strong className="font-bold text-slate-900" id="msg-count">
                                    {filteredMessages.length}
                                </strong>{' '}
                                {curationFilter === 'descartados'
                                    ? filteredMessages.length === 1
                                        ? 'mensaje descartado que coincide con los filtros.'
                                        : 'mensajes descartados que coinciden con los filtros.'
                                    : curationFilter === 'completos'
                                    ? 'mensajes con proceso completo que coinciden con los filtros.'
                                    : curationFilter === 'pending_eval'
                                    ? 'mensajes pendientes de evaluar que coinciden con los filtros.'
                                    : curationFilter === 'pending_copy'
                                    ? 'mensajes en la cola de publicación que coinciden con los filtros.'
                                    : 'mensajes en total (Todos los mensajes) que coinciden con los filtros.'}
                                {(dateFrom || dateTo) && (
                                    <span className="ml-1 font-semibold text-purple-700">
                                        (en rango: {dateFrom || 'inicio'} a {dateTo || 'hoy'})
                                    </span>
                                )}
                            </p>
                        </div>

                        <div className="l-cluster">
                            <span className="c-pill c-pill--outline">
                                <span
                                    className={`h-1.5 w-1.5 rounded-full ${
                                        apiConnected ? 'bg-emerald-500' : 'bg-amber-400'
                                    }`}
                                />
                                Actualización en streaming {apiConnected ? 'activa' : 'pendiente'}
                            </span>

                            <button
                                className="c-btn c-btn--ghost c-btn--sm"
                                type="button"
                                id="msg-reset"
                                onClick={clearFilters}
                            >
                                Limpiar filtros
                            </button>
                        </div>
                    </div>

                    <div className="c-toolbar">
                        {/* Buscar */}
                        <div className="c-field" style={{ flexBasis: '16rem' }}>
                            <label className="c-label sr-only" htmlFor="msg-q">
                                Buscar
                            </label>
                            <div className="c-input-group">
                                <Search size={15} className="icon" />
                                <input
                                    id="msg-q"
                                    type="text"
                                    className="c-input"
                                    placeholder="Buscar por autor o contenido…"
                                    value={searchTerm}
                                    onChange={(event) => setSearchTerm(event.target.value)}
                                />
                            </div>
                        </div>

                        {/* Canal */}
                        <div className="c-field">
                            <label className="c-label sr-only" htmlFor="msg-channel">
                                Canal
                            </label>
                            <select
                                id="msg-channel"
                                className="c-select"
                                value={channelFilter}
                                onChange={(event) => setChannelFilter(event.target.value)}
                            >
                                <option value="all">
                                    Todos los canales ({channels.length})
                                </option>
                                {channels.map((channel) => (
                                    <option key={channel} value={channel}>
                                        #{channel}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Sentimiento */}
                        <div className="c-field">
                            <label className="c-label sr-only" htmlFor="msg-sent">
                                Sentimiento
                            </label>
                            <select
                                id="msg-sent"
                                className="c-select"
                                value={sentimentFilter}
                                onChange={(event) => setSentimentFilter(event.target.value)}
                            >
                                <option value="all">Todo sentimiento</option>
                                <option value="positive">Positivo</option>
                                <option value="neutral">Neutral</option>
                                <option value="negative">Negativo</option>
                            </select>
                        </div>

                        {/* Tema */}
                        <div className="c-field">
                            <label className="c-label sr-only" htmlFor="msg-topic">
                                Tema
                            </label>
                            <select
                                id="msg-topic"
                                className="c-select"
                                value={topicFilter}
                                onChange={(event) => setTopicFilter(event.target.value)}
                            >
                                <option value="all">Todos los temas</option>
                                {topics.map((topic) => (
                                    <option key={topic} value={topic}>
                                        {topic}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {/* Estado del mensaje */}
                        <div className="c-field">
                            <label className="c-label sr-only" htmlFor="msg-status">
                                Estado del mensaje
                            </label>
                            <select
                                id="msg-status"
                                aria-label="Estado del mensaje"
                                className="c-select"
                                value={curationFilter}
                                onChange={(event) => setCurationFilter(event.target.value)}
                            >
                                <option value="all">Todos los estados</option>
                                <option value="pending_eval">Pendientes de evaluar</option>
                                <option value="pending_copy">Pendientes de publicar</option>
                                <option value="completos">Proceso completo</option>
                                <option value="descartados">Descartado</option>
                            </select>
                        </div>
                    </div>

                    <div className="l-cluster" id="msg-chips" style={{ marginTop: 'var(--space-4)' }}>
                        {classificationChips.map(([val, label, count]) => (
                            <button
                                key={val}
                                type="button"
                                onClick={() => setClassificationFilter(val)}
                                className={`c-chip${classificationFilter === val ? ' is-active' : ''}`}
                            >
                                {label} <span className="c-chip__n">{count}</span>
                            </button>
                        ))}

                        <span className="mx-1 h-4 w-px bg-slate-200" aria-hidden="true" />

                        {[
                            ['all', 'Todo el tiempo'],
                            ['24h', '24 Horas'],
                            ['week', 'Semana'],
                            ['month', 'Mes'],
                        ].map(([value, label]) => (
                            <button
                                key={value}
                                type="button"
                                onClick={() => setTimeFilter(value)}
                                className={`c-chip${timeFilter === value ? ' is-active' : ''}`}
                            >
                                {label}
                            </button>
                        ))}
                    </div>

                    {curationError && (
                        <div
                            role="alert"
                            className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-700"
                        >
                            No se guardó la curaduría: {curationError}
                        </div>
                    )}
                </div>

                {/* Lista de Mensajes (#msg-list) */}
                <div id="msg-list" className="max-h-[min(850px,70vh)] overflow-y-auto">
                    {filteredMessages.length === 0 && (
                        <div className="c-empty">
                            <div className="c-empty__icon">
                                <Search size={22} />
                            </div>
                            <p className="c-empty__title">No se encontraron mensajes</p>
                            <p className="c-empty__text">
                                Prueba con otros filtros o limpia la búsqueda.
                            </p>
                        </div>
                    )}

                    {filteredMessages.map((message) => {
                        const isMsgPublished =
                            Boolean(message.isPublished) || message.workflowStage === 'publicado'
                        const currentCuration = curationStatus[message.id] ?? 'pending'
                        const status = isMsgPublished
                            ? 'curated'
                            : currentCuration === 'discarded' ||
                              (message.isAnalyzed &&
                                  message.relevance < 70 &&
                                  currentCuration !== 'curated' &&
                                  currentCuration !== 'pending')
                            ? 'discarded'
                            : currentCuration

                        const ALL_PLATFORMS = ['Discord', 'LinkedIn', 'X'] as const
                        const rawPublished = (message.publishedPlatforms || []).map((p) => {
                            const lower = p.toLowerCase()
                            if (lower === 'discord') return 'Discord'
                            if (lower === 'linkedin') return 'LinkedIn'
                            if (lower === 'x' || lower === 'twitter') return 'X'
                            return p
                        })
                        const canonicalPublished = ALL_PLATFORMS.filter((p) =>
                            rawPublished.includes(p)
                        )
                        const effectivePublished =
                            canonicalPublished.length > 0 ? canonicalPublished : ['Discord']
                        const missingPlatforms = ALL_PLATFORMS.filter(
                            (p) => !effectivePublished.includes(p)
                        )
                        const publishedPlatformsText = effectivePublished.join(', ')

                        const actionButtonLabel = !isMsgPublished
                            ? 'Generar publicación'
                            : missingPlatforms.length > 0
                            ? `Publicar en demás redes (${missingPlatforms.join(', ')})`
                            : 'Ver en mesa de trabajo'

                        const relevanceScore = message.relevance
                        const sentimentPillClass =
                            message.sentiment === 'positive'
                                ? 'c-pill--success'
                                : message.sentiment === 'negative'
                                ? 'c-pill--danger'
                                : ''

                        return (
                            <div
                                key={message.id}
                                className="c-msg flex-col xl:flex-row xl:items-start"
                            >
                                <div className="flex min-w-0 flex-1 items-start gap-3">
                                    <span className={`c-avatar ${getAvatarTone(message.author)}`}>
                                        {message.initials}
                                    </span>

                                    <div className="c-msg__body">
                                        <div className="c-msg__head">
                                            <span className="c-msg__author">{message.author}</span>
                                            <span className="t-caption text-slate-400">
                                                @{message.author.toLowerCase().replace(/\s+/g, '_')}
                                            </span>
                                            <span className="c-tag c-tag--channel">
                                                {message.channel.replace(/^#/, '')}
                                            </span>
                                            <span
                                                className={`c-pill ${
                                                    isMsgPublished ||
                                                    status === 'curated' ||
                                                    message.workflowStage === 'en_aprobacion' ||
                                                    message.workflowStage === 'en_redaccion'
                                                        ? 'c-pill--success'
                                                        : !message.isAnalyzed ||
                                                          message.workflowStage === 'ingesta' ||
                                                          message.workflowStage === 'en_ingesta'
                                                        ? 'c-pill--warning'
                                                        : 'c-pill--info'
                                                }`}
                                            >
                                                {isMsgPublished
                                                    ? 'Publicado'
                                                    : status === 'curated' ||
                                                      message.workflowStage === 'en_aprobacion' ||
                                                      message.workflowStage === 'en_redaccion'
                                                    ? 'Completo'
                                                    : !message.isAnalyzed ||
                                                      message.workflowStage === 'ingesta' ||
                                                      message.workflowStage === 'en_ingesta'
                                                    ? 'Ingesta / IA'
                                                    : 'Publicar'}
                                            </span>
                                            <span className="c-msg__time tabular-nums">
                                                {message.time}
                                            </span>
                                        </div>

                                        <p className="c-msg__text">{message.message}</p>

                                        <div className="c-msg__meta">
                                            {message.isAnalyzed ? (
                                                <>
                                                    <span
                                                        className={`c-pill c-pill--dot ${sentimentPillClass}`}
                                                    >
                                                        {message.sentimentLabel}
                                                    </span>
                                                    <span className="c-pill c-pill--brand">
                                                        {message.topic}
                                                    </span>
                                                    <span className="c-pill c-pill--outline">
                                                        {message.classification}
                                                    </span>
                                                    <span className="c-pill c-pill--success">
                                                        <ThumbsUp size={11} />
                                                        Analizado con IA
                                                    </span>
                                                    {message.highlight && (
                                                        <span className="c-pill c-pill--brand">
                                                            Destacado
                                                        </span>
                                                    )}
                                                    {isMsgPublished && (
                                                        <span className="c-pill c-pill--success">
                                                            ✓ Publicado en: {publishedPlatformsText}
                                                        </span>
                                                    )}
                                                    {message.keywords.slice(0, 6).map((keyword) => (
                                                        <span key={keyword} className="c-tag">
                                                            #{keyword}
                                                        </span>
                                                    ))}
                                                </>
                                            ) : (
                                                <>
                                                    <span className="c-pill c-pill--warning c-pill--dot">
                                                        <Clock3 size={11} />
                                                        Pendiente por Analizar
                                                    </span>
                                                    <span className="c-pill c-pill--outline">
                                                        {message.classification}
                                                    </span>
                                                    <span className="t-caption italic text-slate-500">
                                                        ⚡ Pendiente por Analizar · Mensaje crudo en ingesta. Pulsa &apos;Evaluar con IA&apos; para clasificarlo
                                                    </span>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Columna derecha: Relevancia, Estado y Botones de Acción (CommunityLab DS) */}
                                <aside className="c-msg__score w-full shrink-0 gap-2 border-t border-slate-100 pt-3 xl:w-64 xl:border-l xl:border-t-0 xl:pl-4 xl:pt-0">
                                    <div className="flex w-full items-center justify-between gap-2.5">
                                        <div className="min-w-0 flex-1">
                                            <StatusBadge
                                                status={status}
                                                isAnalyzed={message.isAnalyzed}
                                                isPublished={isMsgPublished}
                                                workflowStage={message.workflowStage}
                                            />
                                        </div>

                                        {message.isAnalyzed && (
                                            <div className="flex shrink-0 items-center gap-2">
                                                <div className="flex flex-col items-end gap-0.5">
                                                    <div className="flex items-baseline gap-1">
                                                        <b>{relevanceScore}</b>
                                                        <span className="t-caption">relevancia</span>
                                                    </div>
                                                    <div
                                                        className="c-progress c-progress--sm"
                                                        style={{ width: '3.75rem' }}
                                                    >
                                                        <div
                                                            className="c-progress__bar"
                                                            style={{ width: `${relevanceScore}%` }}
                                                        />
                                                    </div>
                                                </div>
                                                <div
                                                    className="score-ring"
                                                    style={
                                                        { '--p': relevanceScore } as React.CSSProperties
                                                    }
                                                    title={`Relevancia IA: ${relevanceScore}%`}
                                                >
                                                    <span className="tabular-nums">
                                                        {relevanceScore}%
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex w-full items-center gap-1.5">
                                        {status === 'discarded' ? (
                                            <button
                                                type="button"
                                                title="Restaurar mensaje a pendientes"
                                                aria-label="Restaurar mensaje a pendientes"
                                                disabled={savingCurationId !== null}
                                                onClick={() => markCuration(message, 'pending')}
                                                className="c-btn c-btn--secondary c-btn--icon c-btn--sm text-emerald-600 hover:text-emerald-700"
                                            >
                                                <RotateCcw size={14} />
                                            </button>
                                        ) : (
                                            <button
                                                type="button"
                                                title={
                                                    isMsgPublished
                                                        ? 'Mensaje ya publicado (no se puede descartar)'
                                                        : 'Descartar'
                                                }
                                                aria-label="Descartar"
                                                disabled={savingCurationId !== null || isMsgPublished}
                                                onClick={() => markCuration(message, 'discarded')}
                                                className="c-btn c-btn--secondary c-btn--icon c-btn--sm hover:text-rose-600"
                                            >
                                                <X size={14} />
                                            </button>
                                        )}

                                        <button
                                            type="button"
                                            title="Copiar contenido"
                                            aria-label="Copiar contenido"
                                            onClick={() =>
                                                navigator.clipboard.writeText(message.message)
                                            }
                                            className="c-btn c-btn--secondary c-btn--icon c-btn--sm"
                                        >
                                            <Copy size={14} />
                                        </button>

                                        {!message.isAnalyzed && (
                                            <button
                                                type="button"
                                                onClick={() => handleEvaluateSingleMessage(message)}
                                                disabled={
                                                    status === 'discarded' ||
                                                    evaluatingMessageId === message.interactionId
                                                }
                                                title={
                                                    status === 'discarded'
                                                        ? 'Restaura el mensaje para evaluarlo con IA'
                                                        : `Evaluar este mensaje con ${selectedAiBrain}`
                                                }
                                                className="c-btn c-btn--primary c-btn--sm flex-1 justify-center"
                                            >
                                                <Sparkles
                                                    size={13}
                                                    className={
                                                        evaluatingMessageId === message.interactionId
                                                            ? 'animate-spin'
                                                            : ''
                                                    }
                                                />
                                                <span>
                                                    {evaluatingMessageId === message.interactionId
                                                        ? 'Evaluando...'
                                                        : 'Evaluar con IA'}
                                                </span>
                                            </button>
                                        )}

                                        {message.isAnalyzed && (
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    navigate(
                                                        `/content?interaction=${message.interactionId}`,
                                                        {
                                                            state: {
                                                                interactionId: message.interactionId,
                                                            },
                                                        }
                                                    )
                                                }
                                                disabled={status === 'discarded' && !isMsgPublished}
                                                title={
                                                    status === 'discarded' && !isMsgPublished
                                                        ? 'Restaura el mensaje para generar publicación'
                                                        : actionButtonLabel
                                                }
                                                className="c-btn c-btn--primary c-btn--sm flex-1 justify-center"
                                            >
                                                <span className="truncate">{actionButtonLabel}</span>
                                                <ChevronRight size={14} className="shrink-0" />
                                            </button>
                                        )}
                                    </div>
                                </aside>
                            </div>
                        )
                    })}
                </div>
            </article>

            {/* Nota integración */}
            <div className="flex items-start gap-3 rounded-xl border border-blue-100 bg-blue-50/60 p-4">
                <Server
                    size={17}
                    className="mt-0.5 shrink-0 text-blue-600"
                />

                <div>
                    <p className="text-xs font-semibold text-blue-900">
                        Flujo de ingesta CloudEdTech
                    </p>

                    <p className="mt-1 text-xs leading-5 text-blue-700">
                        Las acciones de curaduría son visuales mientras se
                        completa la integración definitiva con el backend.
                        Analizar dirige la interacción seleccionada al tablero
                        de Análisis. La respuesta directa se habilitará cuando
                        se defina el flujo correspondiente con Discord.
                    </p>
                </div>
            </div>
        </div>
    )
}


function StatusBadge({
    status,
    isAnalyzed,
    isPublished,
    workflowStage,
}: {
    status: CurationStatus
    isAnalyzed?: boolean
    isPublished?: boolean
    workflowStage?: string
}) {
    if (isPublished || workflowStage === 'publicado') {
        return (
            <span className="c-pill c-pill--success c-pill--dot w-full justify-center">
                Proceso completo
            </span>
        )
    }

    if (status === 'discarded') {
        return (
            <span className="c-pill c-pill--danger w-full justify-center">
                <ShieldAlert size={11} />
                Descartado
            </span>
        )
    }

    if (
        status === 'curated' ||
        workflowStage === 'en_aprobacion' ||
        workflowStage === 'en_redaccion'
    ) {
        return (
            <span className="c-pill c-pill--success c-pill--dot w-full justify-center">
                Listo / Aprobado
            </span>
        )
    }

    // Si es totalmente crudo y le falta el análisis con IA
    if (!isAnalyzed || workflowStage === 'ingesta' || workflowStage === 'en_ingesta') {
        return (
            <span className="c-pill c-pill--warning w-full justify-center">
                <Clock3 size={11} />
                Falta análisis con IA
            </span>
        )
    }

    // Ya analizado por IA, pero le falta la parte de redacción / publicación
    return (
        <span className="c-pill c-pill--info w-full justify-center">
            <Sparkles size={11} />
            Falta redacción de publicación
        </span>
    )
}

export default Messages
