import { updateMessageWorkflow } from '../api/messageWorkflow'
import {
    AlertCircle,
    AlertTriangle,
    Bot,
    ChevronRight,
    Clock3,
    Copy,
    Filter,
    Hash,
    MessageCircle,
    RefreshCw,
    RotateCcw,
    Search,
    Server,
    ShieldAlert,
    Sparkles,
    Tag,
    ThumbsUp,
    X,
} from 'lucide-react'

import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
    }
}

type MessagesApiResponse = {
    total: number
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

    const [analyzingMessageId, setAnalyzingMessageId] =
        useState<number | null>(null)
    const [workflowError, setWorkflowError] =
        useState<string | null>(null)


    const [apiData, setApiData] = useState<MessagesApiResponse>({
        total: 0,
        messages: [],
    })

    const [searchTerm, setSearchTerm] = useState('')
    const [channelFilter, setChannelFilter] = useState('all')
    const [sentimentFilter, setSentimentFilter] = useState('all')
    const [timeFilter, setTimeFilter] = useState('all')
    type StageFilterType =
        | 'all'
        | 'pending_eval'
        | 'pending_copy'
        | 'completos'
        | 'ingesta'
        | 'en_analisis'

    const [curationFilter, setCurationFilter] = useState('all')
    const [stageFilter, setStageFilter] = useState<StageFilterType>('all')
    const [aiModels, setAiModels] = useState<AiModel[]>(DEFAULT_AI_MODELS)
    const [selectedAiBrain, setSelectedAiBrain] = useState<string>('Groq (Llama 3.3)')
    const [dateFrom, setDateFrom] = useState<string>('')
    const [dateTo, setDateTo] = useState<string>('')
    const [onlyPending, setOnlyPending] = useState<boolean>(true)
    const [isEvaluatingBatch, setIsEvaluatingBatch] = useState<boolean>(false)
    const [batchEvalMessage, setBatchEvalMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
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

                return {
                    id: message.message_id,
                    interactionId: message.interaction_id,
                    workflowStage: analysis.workflow_stage,
                    initials,
                    author,
                    guild: message.guild_name || 'Discord',
                    channel: message.channel_name,
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
                        analysis.workflow_stage !== 'ingesta' &&
                        analysis.workflow_stage !== 'en_ingesta' &&
                        (analysis.workflow_stage === 'en_analisis' ||
                            analysis.workflow_stage === 'en_redaccion' ||
                            analysis.workflow_stage === 'en_aprobacion' ||
                            analysis.relevance > 0)
                    ),
                }
            }),
        [apiData.messages]
    )

    const channels = useMemo(
        () =>
            Array.from(
                new Set(
                    messageItems
                        .map((message) => message.channel)
                        .filter(Boolean)
                )
            ).sort(),
        [messageItems]
    )

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



    const pendingInCopy = messageItems.filter((message) => {
        const curation = curationStatus[message.id] ?? 'pending'
        return (
            message.isAnalyzed &&
            !message.author.toLowerCase().includes('cloudedtech community bot') &&
            curation !== 'discarded' &&
            curation !== 'curated' &&
            message.workflowStage !== 'en_aprobacion' &&
            message.workflowStage !== 'en_redaccion'
        )
    }).length

    const priorityIncidents = messageItems.filter((message) =>
        message.isAnalyzed &&
        !message.author.toLowerCase().includes('cloudedtech community bot') &&
        (curationStatus[message.id] ?? 'pending') !== 'discarded' &&
        message.sentiment === 'negative' &&
        message.relevance >= 70
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
        const currentCuration = curationStatus[message.id] ?? 'pending'
        const isCompleted =
            currentCuration === 'curated' ||
            message.workflowStage === 'en_aprobacion' ||
            message.workflowStage === 'en_redaccion'

        const isPendingEval =
            !message.isAnalyzed ||
            message.workflowStage === 'ingesta' ||
            message.workflowStage === 'en_ingesta'

        const isPendingCopy = !isCompleted && !isPendingEval

        // Filtro por etapa de flujo editorial
        if (stageFilter === 'completos') {
            if (!isCompleted) return false
        } else if (stageFilter === 'pending_copy') {
            if (!isPendingCopy) return false
        } else if (stageFilter === 'pending_eval') {
            if (!isPendingEval) return false
        } else if (stageFilter === 'ingesta') {
            if (!isPendingEval) return false
        } else if (stageFilter === 'en_analisis') {
            if (!isPendingCopy) return false
        }
        // Cuando stageFilter === 'all', no se restringe por etapa (muestra todo + completos)

        // Evitar que las respuestas del bot reingresen al flujo editorial.
        if (message.author.toLowerCase().includes('cloudedtech community bot')) {
            return false
        }

        if (curationFilter === 'discarded') {
            if (currentCuration !== 'discarded') {
                return false
            }
        } else {
            if (currentCuration === 'discarded') {
                return false
            }
        }

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
            message.channel === channelFilter

        const matchesSentiment =
            sentimentFilter === 'all' ||
            message.sentiment === sentimentFilter

        const matchesCuration =
            curationFilter === 'all' ||
            currentCuration === curationFilter

        return (
            matchesSearch &&
            matchesChannel &&
            matchesSentiment &&
            matchesCuration &&
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
                    : 'No se pudo guardar la curadur?a',
            )
        } finally {
            setSavingCurationId(null)
        }
    }

    const handleAnalyze = async (message: MessageItem) => {
        if (analyzingMessageId !== null) return

        const currentCuration =
            curationStatus[message.id] ?? 'pending'

        if (currentCuration === 'discarded') {
            return
        }

        setAnalyzingMessageId(message.interactionId)
        setWorkflowError(null)

        try {
            if (
                message.workflowStage === 'ingesta' ||
                message.workflowStage === 'en_ingesta'
            ) {
                await updateMessageWorkflow(
                    message.interactionId,
                    'en_analisis',
                )
            }

            navigate(`/analytics?interaction=${message.interactionId}`, {
        state: {
            source: 'ingesta',
            interaction: {
                id: message.id,
                author: message.author,
                channel: message.channel,
                content: message.message,
                sentiment: message.sentiment,
                sentimentLabel: message.sentimentLabel,
                topic: message.topic,
                keywords: message.keywords,
                relevance: message.relevance,
            },
        },
    })
        } catch (error) {
            setWorkflowError(
                error instanceof Error
                    ? error.message
                    : 'No fue posible enviar el mensaje a Analisis',
            )
        } finally {
            setAnalyzingMessageId(null)
        }
    }

    const [evaluatingMessageId, setEvaluatingMessageId] = useState<number | null>(null)

    const handleEvaluateSingleMessage = async (message: MessageItem) => {
        if (evaluatingMessageId !== null) return

        setEvaluatingMessageId(message.interactionId)
        try {
            await evaluateSingleMessage(message.interactionId, selectedAiBrain)
            await loadMessages()
        } catch (error) {
            console.error('Error al evaluar mensaje con IA:', error)
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
                evaluableCount: 0,
            }
        }

        const fromTimestamp = dateFrom ? new Date(`${dateFrom}T00:00:00`).getTime() : null
        const toTimestamp = dateTo ? new Date(`${dateTo}T23:59:59.999`).getTime() : null

        let totalInRange = 0
        let pendingEvalInRange = 0
        let pendingCopyInRange = 0
        let completedInRange = 0

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

            const st = curationStatus[msg.id] ?? 'pending'
            if (st === 'discarded') {
                continue
            }

            totalInRange++

            const isCompleted =
                st === 'curated' ||
                msg.workflowStage === 'en_aprobacion' ||
                msg.workflowStage === 'en_redaccion'

            const isPendingEval =
                !msg.isAnalyzed ||
                msg.workflowStage === 'ingesta' ||
                msg.workflowStage === 'en_ingesta'

            if (isCompleted) {
                completedInRange++
            } else if (isPendingEval) {
                pendingEvalInRange++
            } else {
                pendingCopyInRange++
            }
        }

        const pendingInRange = pendingEvalInRange
        const evaluableCount = onlyPending ? pendingEvalInRange : totalInRange

        return {
            isDateRangeInverted: false,
            totalInRange,
            pendingInRange,
            pendingEvalInRange,
            pendingCopyInRange,
            completedInRange,
            evaluableCount,
        }
    }, [messageItems, dateFrom, dateTo, onlyPending, curationStatus])

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
            const errMsg = error instanceof Error ? error.message : 'Error desconocido al sincronizar Discord'
            const isConflict = errMsg.includes('409') || errMsg.includes('Sincronización en curso')
            setSyncFeedbackMessage({
                type: isConflict ? 'warning' : 'error',
                text: isConflict
                    ? '⏳ Sincronización en curso. Por favor espera a que finalice el proceso anterior.'
                    : `Error al sincronizar Discord: ${errMsg}`,
            })
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
        setBatchEvalMessage(null)

        try {
            const payload: {
                proveedor: string
                desde?: string
                hasta?: string
                solo_pendientes: boolean
                limite: number
            } = {
                proveedor: selectedAiBrain,
                solo_pendientes: onlyPending,
                limite: 100,
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
            setBatchEvalMessage({
                type: 'error',
                text: error instanceof Error ? error.message : 'Error al evaluar el lote con IA.',
            })
        } finally {
            setIsEvaluatingBatch(false)
        }
    }

    const clearFilters = () => {
        setSearchTerm('')
        setChannelFilter('all')
        setSentimentFilter('all')
        setTimeFilter('all')
        setCurationFilter('all')
        setStageFilter('all')
        setDateFrom('')
        setDateTo('')
        setBatchEvalMessage(null)
        setSyncFeedbackMessage(null)
    }

    return (
        <div className="space-y-6">
            {workflowError && (
                <div
                    role="alert"
                    className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
                >
                    {workflowError}
                </div>
            )}

            {/* Encabezado */}
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-100 text-orange-500">
                        <MessageCircle size={21} />
                    </div>

                    <div>
                        <h2 className="text-2xl font-bold text-slate-900">
                            Ingesta de mensajes
                        </h2>

                        <p className="mt-1 text-sm text-slate-500">
                            Monitoreo, análisis y curaduría de conversaciones de Discord
                        </p>
                    </div>
                </div>

                <div
                    className={`flex items-center gap-2 rounded-lg px-3 py-2 ${
                        apiConnected
                            ? 'bg-emerald-50 text-emerald-700'
                            : 'bg-amber-50 text-amber-700'
                    }`}
                >
                    <div
                        className={`h-2 w-2 rounded-full ${
                            apiConnected
                                ? 'bg-emerald-500'
                                : 'bg-amber-500'
                        }`}
                    />

                    <span className="text-xs font-semibold">
                        {apiConnected
                            ? 'Motor de ingesta conectado'
                            : 'Esperando conexión del Motor IA'}
                    </span>
                </div>
            </div>

            {/* KPIs */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                <KpiCard
                    label="Mensajes analizados"
                    value={analyzedCount}
                    helper={
                        messageItems.length > 0
                            ? `${analyzedCount} de ${messageItems.length} (${messageItems.length - analyzedCount} pendientes)`
                            : 'Sin mensajes'
                    }
                />

                <KpiCard
                    label="Positivos"
                    value={positiveMessages}
                    helper={
                        analyzedCount > 0
                            ? `${Math.round(
                                  (positiveMessages /
                                      analyzedCount) *
                                      100
                              )}% de los analizados`
                            : 'Sin mensajes analizados'
                    }
                    valueClass="text-emerald-600"
                />

                <KpiCard
                    label="Preguntas"
                    value={questionMessages}
                    helper="Detectadas en la ingesta"
                    valueClass="text-blue-600"
                />

                <KpiCard
                    label="Destacados"
                    value={highlightedMessages}
                    helper="Interacciones relevantes"
                    valueClass="text-orange-500"
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

            {/* Estado Discord */}
            <section className="rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-sm">
                            <MessageCircle size={25} />
                        </div>

                        <div>
                            <div className="flex flex-wrap items-baseline gap-2">
                                <span className="text-3xl font-black tracking-tight text-slate-950">
                                    {apiData.total || messageItems.length}
                                </span>

                                <span className="text-sm font-semibold text-slate-500">
                                    Mensajes totales recibidos
                                </span>
                            </div>

                            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                                <span
                                    className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-semibold ${
                                        apiConnected
                                            ? 'bg-emerald-50 text-emerald-700'
                                            : 'bg-amber-50 text-amber-700'
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

                                <span className="text-slate-400">
                                    Datos almacenados en Motor IA
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                        <div className="flex divide-x divide-slate-200 rounded-xl border border-slate-100">
                            <div className="px-6 py-2 text-center">
                                <p className="text-xs font-medium text-slate-500">Pendientes en Copy</p>
                                <p className="mt-1 text-lg font-bold text-orange-500">{pendingInCopy}</p>
                            </div>

                            <div className="px-6 py-2 text-center">
                                <p className="text-xs font-medium text-slate-500">Incidentes prioritarios</p>
                                <p className="mt-1 text-lg font-bold text-rose-600">
                                    {priorityIncidents}
                                </p>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={handleSyncDiscord}
                            disabled={isSyncingDiscord}
                            className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw
                                size={14}
                                className={isSyncingDiscord ? 'animate-spin' : ''}
                            />
                            {isSyncingDiscord ? 'Sincronizando...' : '📥 Sincronizar Discord'}
                        </button>
                    </div>
                </div>
            </section>

            {/* Panel de Evaluación IA por Lotes con Filtro de Fechas */}
            <section className="rounded-2xl border border-purple-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-100 text-purple-600">
                            <Bot size={20} />
                        </div>
                        <div>
                            <h3 className="font-bold text-slate-900">
                                Evaluación por Lote con Inteligencia Artificial
                            </h3>
                            <p className="text-xs text-slate-500">
                                Clasifica sentimiento, relevancia y temas usando los modelos del motor IA
                            </p>
                        </div>
                    </div>

                    {aiModels.length > 0 && (
                        <div className="flex items-center gap-1.5 rounded-lg bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-700">
                            <span className="h-2 w-2 rounded-full bg-purple-500 animate-pulse" />
                            {aiModels.length} cerebros IA disponibles
                        </div>
                    )}
                </div>

                {/* Contador reactivo e indicadores de estado */}
                <div className="mb-4 space-y-2">
                    {batchEvalMetrics.isDateRangeInverted ? (
                        <div
                            role="alert"
                            className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-4 py-2.5 text-xs font-semibold text-rose-700"
                        >
                            <AlertCircle size={16} className="shrink-0 text-rose-600" />
                            <span>La fecha 'Desde' no puede ser posterior a 'Hasta'.</span>
                        </div>
                    ) : (
                        <div className="flex flex-wrap items-center gap-2">
                            <div className="inline-flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-xl border border-purple-100 bg-purple-50/80 px-3.5 py-2 text-xs text-slate-700">
                                <span className="font-bold text-purple-950">
                                    📊 {batchEvalMetrics.totalInRange} mensajes en este rango:
                                </span>
                                <span className="inline-flex items-center gap-1 font-semibold text-amber-700">
                                    <Clock3 size={13} className="shrink-0" />
                                    <strong>{batchEvalMetrics.pendingEvalInRange}</strong> pendientes de evaluar
                                </span>
                                <span className="text-slate-300">·</span>
                                <span className="inline-flex items-center gap-1 font-semibold text-indigo-700">
                                    <Sparkles size={13} className="shrink-0" />
                                    <strong>{batchEvalMetrics.pendingCopyInRange}</strong> pendientes de copy
                                </span>
                                <span className="text-slate-300">·</span>
                                <span className="inline-flex items-center gap-1 font-semibold text-emerald-700">
                                    <ThumbsUp size={13} className="shrink-0" />
                                    <strong>{batchEvalMetrics.completedInRange}</strong> con proceso completo
                                </span>
                            </div>

                            {(dateFrom || dateTo) && (
                                <button
                                    type="button"
                                    onClick={() => {
                                        setDateFrom('')
                                        setDateTo('')
                                    }}
                                    className="inline-flex items-center gap-1.5 rounded-xl border border-purple-200 bg-white px-3 py-1.5 text-xs font-semibold text-purple-700 shadow-sm transition hover:bg-purple-50"
                                    title="Quitar filtro de fechas para ver todos los mensajes"
                                >
                                    <X size={13} />
                                    Mostrar todos los mensajes
                                </button>
                            )}

                            {batchEvalMetrics.evaluableCount === 0 && (
                                <div
                                    role="status"
                                    className="inline-flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800"
                                >
                                    <AlertTriangle size={15} className="shrink-0 text-amber-600" />
                                    <span>
                                        {batchEvalMetrics.totalInRange === 0
                                            ? 'Sin mensajes en este rango de fechas.'
                                            : 'Todos los mensajes de este rango ya fueron evaluados (puedes explorarlos abajo).'}
                                    </span>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {batchEvalMessage && (
                    <div
                        role="alert"
                        className={`mb-4 flex items-center justify-between rounded-xl border px-4 py-3 text-xs font-medium ${
                            batchEvalMessage.type === 'success'
                                ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
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

                <div className="grid grid-cols-1 items-end gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {/* Selector de Cerebro IA */}
                    <div>
                        <label className="mb-1.5 block text-xs font-semibold text-slate-700">
                            Cerebro IA
                        </label>
                        <select
                            value={selectedAiBrain}
                            onChange={(e) => setSelectedAiBrain(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-medium text-slate-700 outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                        >
                            {aiModels.map((m) => (
                                <option key={m.id} value={m.name}>
                                    {m.name} ({m.provider})
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Fecha Desde */}
                    <div>
                        <label className="mb-1.5 block text-xs font-semibold text-slate-700">
                            Desde (opcional)
                        </label>
                        <input
                            type="date"
                            value={dateFrom}
                            onChange={(e) => setDateFrom(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                        />
                    </div>

                    {/* Fecha Hasta */}
                    <div>
                        <label className="mb-1.5 block text-xs font-semibold text-slate-700">
                            Hasta (opcional)
                        </label>
                        <input
                            type="date"
                            value={dateTo}
                            onChange={(e) => setDateTo(e.target.value)}
                            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 outline-none focus:border-purple-400 focus:ring-2 focus:ring-purple-100"
                        />
                    </div>

                    {/* Checkbox y Botón de Acción */}
                    <div className="flex flex-col gap-2">
                        <label className="flex cursor-pointer select-none items-center gap-2 text-xs text-slate-600">
                            <input
                                type="checkbox"
                                checked={onlyPending}
                                onChange={(e) => setOnlyPending(e.target.checked)}
                                className="rounded border-slate-300 text-purple-600 focus:ring-purple-400"
                            />
                            Solo pendientes de evaluar
                        </label>

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
                            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-purple-600 px-4 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                            <RefreshCw
                                size={14}
                                className={isEvaluatingBatch ? 'animate-spin' : ''}
                            />
                            {isEvaluatingBatch ? 'Evaluando con IA...' : 'Evaluar mensajes con IA'}
                        </button>
                    </div>
                </div>
            </section>

            {/* Panel de filtrado */}
            <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex items-center gap-2">
                        <Filter size={17} className="text-orange-500" />
                        <h3 className="font-bold text-slate-900">
                            Panel de filtrado de mensajes
                        </h3>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        <button
                            type="button"
                            onClick={clearFilters}
                            className="rounded-xl bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-200"
                        >
                            Deseleccionar
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1.1fr_1.35fr_1fr]">
                    {/* Tiempo */}
                    <div>
                        <label className="mb-2 block text-xs font-semibold text-slate-600">
                            Filtro de tiempo
                        </label>

                        <div className="grid grid-cols-4 rounded-xl bg-slate-100 p-1">
                            {[
                                ['24h', '24 Horas'],
                                ['week', 'Semana'],
                                ['month', 'Mes'],
                                ['all', 'Todo'],
                            ].map(([value, label]) => (
                                <button
                                    key={value}
                                    type="button"
                                    onClick={() =>
                                        setTimeFilter(value)
                                    }
                                    className={`rounded-lg px-2 py-2 text-[11px] font-semibold transition ${
                                        timeFilter === value
                                            ? 'bg-white text-slate-900 shadow-sm'
                                            : 'text-slate-500'
                                    }`}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Canal */}
                    <div>
                        <label className="mb-2 block text-xs font-semibold text-slate-600">
                            Canales monitoreados
                        </label>

                        <div className="relative">
                            <Hash
                                size={15}
                                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                            />

                            <select
                                value={channelFilter}
                                onChange={(event) =>
                                    setChannelFilter(
                                        event.target.value
                                    )
                                }
                                className="w-full appearance-none rounded-xl border border-slate-200 bg-white py-2.5 pl-9 pr-4 text-xs font-medium text-slate-700 outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
                            >
                                <option value="all">
                                    Todos los canales ({channels.length})
                                </option>

                                {channels.map((channel) => (
                                    <option
                                        key={channel}
                                        value={channel}
                                    >
                                        #{channel}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Búsqueda */}
                    <div>
                        <label className="mb-2 block text-xs font-semibold text-slate-600">
                            Identificación y búsqueda
                        </label>

                        <div className="relative">
                            <Search
                                size={15}
                                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                            />

                            <input
                                type="text"
                                placeholder="Buscar usuario, tema, canal o palabra clave..."
                                value={searchTerm}
                                onChange={(event) =>
                                    setSearchTerm(event.target.value)
                                }
                                className="w-full rounded-xl border border-slate-200 py-2.5 pl-9 pr-4 text-xs outline-none transition focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
                            />
                        </div>
                    </div>

                    {/* Estado */}
                    <div>
                        <label className="mb-2 block text-xs font-semibold text-slate-600">
                            Estado del mensaje
                        </label>

                        <select
                            value={curationFilter}
                            onChange={(event) =>
                                setCurationFilter(event.target.value)
                            }
                            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs font-medium text-slate-700 outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
                        >
                            <option value="all">
                                Todos los estados
                            </option>
                            <option value="pending">
                                Pendientes
                            </option>
                            <option value="curated">
                                Listo / Aprobado
                            </option>
                            <option value="discarded">
                                Descartado
                            </option>
                        </select>
                    </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center gap-3">
                    <select
                        value={sentimentFilter}
                        onChange={(event) =>
                            setSentimentFilter(event.target.value)
                        }
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600 outline-none focus:border-orange-400"
                    >
                        <option value="all">
                            Todos los sentimientos
                        </option>
                        <option value="positive">
                            Positivo
                        </option>
                        <option value="neutral">
                            Neutral
                        </option>
                        <option value="negative">
                            Negativo
                        </option>
                    </select>

                    <select
                        value={stageFilter}
                        onChange={(event) =>
                            setStageFilter(event.target.value as StageFilterType)
                        }
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none focus:border-orange-400"
                    >
                        <option value="all">
                            Etapa: Todas (Todo + Completos)
                        </option>
                        <option value="pending_eval">
                            Etapa: Pendientes de Evaluar
                        </option>
                        <option value="pending_copy">
                            Etapa: Pendientes de Copy
                        </option>
                        <option value="completos">
                            Etapa: Solo Completos
                        </option>
                    </select>
                </div>
            </section>

            {/* Cabecera de cola */}
            <div className="flex flex-col gap-2 px-1 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs font-medium text-slate-500">
                    Mostrando{' '}
                    <span className="font-bold text-slate-700">
                        {filteredMessages.length}
                    </span>{' '}
                    {curationFilter === 'discarded'
                        ? filteredMessages.length === 1
                            ? 'mensaje descartado'
                            : 'mensajes descartados'
                        : stageFilter === 'completos'
                        ? 'mensajes con proceso completo'
                        : stageFilter === 'pending_eval' || stageFilter === 'ingesta'
                        ? 'mensajes pendientes de evaluar'
                        : stageFilter === 'pending_copy' || stageFilter === 'en_analisis'
                        ? 'mensajes en la cola de copy'
                        : 'mensajes en total (todo + completos)'}
                    {(dateFrom || dateTo) && (
                        <span className="ml-1 font-semibold text-purple-700">
                            (en rango: {dateFrom || 'inicio'} a {dateTo || 'hoy'})
                        </span>
                    )}
                </p>

                <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span
                        className={`h-2 w-2 rounded-full ${
                            apiConnected
                                ? 'bg-emerald-500'
                                : 'bg-amber-400'
                        }`}
                    />
                    Actualización en streaming
                    {apiConnected ? ' activa' : ' pendiente'}
                </div>
            </div>

            {curationError && (
                <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                    No se guardó la curaduría: {curationError}
                </div>
            )}

            {/* Mensajes */}
            <div className="space-y-4">
                {filteredMessages.length === 0 && (
                    <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm">
                        <MessageCircle
                            size={36}
                            className="mx-auto text-slate-300"
                        />

                        <h3 className="mt-4 font-semibold text-slate-900">
                            No se encontraron mensajes
                        </h3>

                        <p className="mt-1 text-sm text-slate-500">
                            No hay mensajes disponibles con los filtros seleccionados.
                        </p>
                    </div>
                )}

                {filteredMessages.map((message) => {
                    const status =
                        curationStatus[message.id] || 'pending'

                    return (
                        <article
                            key={message.id}
                            className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md"
                        >
                            <div className="flex flex-col xl:flex-row">
                                {/* Contenido */}
                                <div className="min-w-0 flex-1 p-5">
                                    <div className="flex items-start gap-3">
                                        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700">
                                            {message.initials}
                                        </div>

                                        <div className="min-w-0 flex-1">
                                            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                                                <p className="font-bold text-slate-900">
                                                    {message.author}
                                                </p>

                                                <span className="text-xs text-slate-400">
                                                    @{message.author
                                                        .toLowerCase()
                                                        .replace(
                                                            /\s+/g,
                                                            '_'
                                                        )}
                                                </span>

                                                <span className="rounded-md bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-500">
                                                    {message.classification}
                                                </span>

                                                <span className={`rounded-md px-2 py-1 text-[10px] font-semibold ${
                                                    status === 'curated' || message.workflowStage === 'en_aprobacion' || message.workflowStage === 'en_redaccion'
                                                        ? 'bg-emerald-100 text-emerald-700'
                                                        : !message.isAnalyzed || message.workflowStage === 'ingesta' || message.workflowStage === 'en_ingesta'
                                                        ? 'bg-amber-100 text-amber-700'
                                                        : 'bg-indigo-100 text-indigo-700'
                                                }`}>
                                                    {status === 'curated' || message.workflowStage === 'en_aprobacion' || message.workflowStage === 'en_redaccion'
                                                        ? 'Completo'
                                                        : !message.isAnalyzed || message.workflowStage === 'ingesta' || message.workflowStage === 'en_ingesta'
                                                        ? 'Ingesta / IA'
                                                        : 'Copy'}
                                                </span>

                                                <span className="inline-flex items-center gap-1 rounded-md bg-indigo-50 px-2 py-1 text-[10px] font-semibold text-indigo-600">
                                                    <Hash size={11} />
                                                    {message.channel}
                                                </span>

                                                <span className="inline-flex items-center gap-1 text-[10px] text-slate-400">
                                                    <Clock3 size={11} />
                                                    {message.time}
                                                </span>
                                            </div>

                                            <p className="mt-3 text-sm leading-6 text-slate-700">
                                                {message.message}
                                            </p>

                                            {/* Keywords */}
                                            {message.isAnalyzed && message.keywords.length > 0 && (
                                                <div className="mt-3 flex flex-wrap items-center gap-2">
                                                    <Tag
                                                        size={13}
                                                        className="text-slate-400"
                                                    />

                                                    {message.keywords
                                                        .slice(0, 6)
                                                        .map(
                                                            (
                                                                keyword
                                                            ) => (
                                                                <span
                                                                    key={
                                                                        keyword
                                                                    }
                                                                    className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-medium text-slate-600"
                                                                >
                                                                    #
                                                                    {
                                                                        keyword
                                                                    }
                                                                </span>
                                                            )
                                                        )}
                                                </div>
                                            )}

                                            {/* Reacciones visuales */}
                                            <div className="mt-4 flex flex-wrap gap-2">
                                                {message.isAnalyzed ? (
                                                    <span className="inline-flex items-center gap-1 rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
                                                        <ThumbsUp size={12} />
                                                        Analizado con IA
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex items-center gap-1 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-semibold text-amber-700">
                                                        <Clock3 size={12} />
                                                        Pendiente por Analizar
                                                    </span>
                                                )}

                                                {message.highlight && (
                                                    <span className="rounded-lg border border-orange-200 bg-orange-50 px-2.5 py-1 text-[11px] font-semibold text-orange-700">
                                                        Destacado
                                                    </span>
                                                )}
                                            </div>

                                            {/* Metadatos IA */}
                                            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-slate-100 pt-3 text-[11px]">
                                                {message.isAnalyzed ? (
                                                    <>
                                                        <span className="text-slate-500">
                                                            Tema:{' '}
                                                            <strong className="text-slate-700">
                                                                {message.topic}
                                                            </strong>
                                                        </span>

                                                        <span className="text-slate-500">
                                                            Relevancia:{' '}
                                                            <strong className="text-slate-700">
                                                                {message.relevance}%
                                                            </strong>
                                                        </span>

                                                        <span className="text-slate-500">
                                                            Sentimiento:{' '}
                                                            <strong
                                                                className={
                                                                    message.sentiment ===
                                                                    'positive'
                                                                        ? 'text-emerald-600'
                                                                        : message.sentiment ===
                                                                            'negative'
                                                                          ? 'text-rose-600'
                                                                          : 'text-blue-600'
                                                                }
                                                            >
                                                                {
                                                                    message.sentimentLabel
                                                                }
                                                            </strong>
                                                        </span>
                                                    </>
                                                ) : (
                                                    <span className="inline-flex items-center gap-1.5 text-xs text-amber-700 font-medium italic">
                                                        <span>⚡ Pendiente por Analizar</span>
                                                        <span className="text-slate-300">·</span>
                                                        <span className="text-slate-500 font-normal">
                                                            Mensaje crudo en ingesta. Pulsa &apos;Evaluar IA&apos; para clasificarlo
                                                        </span>
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Acciones */}
                                <aside className="flex shrink-0 flex-col justify-between gap-4 border-t border-slate-100 bg-slate-50/40 p-4 xl:w-56 xl:border-l xl:border-t-0">
                                    <div>
                                        <StatusBadge
                                            status={status}
                                            isAnalyzed={message.isAnalyzed}
                                            workflowStage={message.workflowStage}
                                        />

                                        <div className="mt-3 grid grid-cols-2 gap-1 rounded-xl border border-slate-200 bg-white p-1">
                                            {status === 'discarded' ? (
                                                <button
                                                    type="button"
                                                    title="Restaurar mensaje a pendientes"
                                                    disabled={savingCurationId !== null}
                                                    onClick={() =>
                                                        markCuration(
                                                            message,
                                                            'pending'
                                                        )
                                                    }
                                                    className="flex h-9 items-center justify-center rounded-lg text-emerald-600 transition hover:bg-emerald-50 hover:text-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
                                                >
                                                    <RotateCcw size={15} />
                                                </button>
                                            ) : (
                                                <button
                                                    type="button"
                                                    title="Descartar"
                                                    disabled={savingCurationId !== null}
                                                    onClick={() =>
                                                        markCuration(
                                                            message,
                                                            'discarded'
                                                        )
                                                    }
                                                    className="flex h-9 items-center justify-center rounded-lg text-slate-400 transition hover:bg-rose-50 hover:text-rose-500 disabled:cursor-not-allowed disabled:opacity-50"
                                                >
                                                    <X size={15} />
                                                </button>
                                            )}

                                            <button
                                                type="button"
                                                title="Copiar contenido"
                                                onClick={() =>
                                                    navigator.clipboard.writeText(
                                                        message.message
                                                    )
                                                }
                                                className="flex h-9 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                                            >
                                                <Copy size={15} />
                                            </button>
                                        </div>
                                    </div>

                                    <div className={message.isAnalyzed ? 'grid grid-cols-1 gap-2' : 'grid grid-cols-2 gap-2'}>
                                        {!message.isAnalyzed && (
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    handleEvaluateSingleMessage(message)
                                                }
                                                disabled={
                                                    status === 'discarded' ||
                                                    evaluatingMessageId === message.interactionId
                                                }
                                                title={
                                                    status === 'discarded'
                                                        ? 'Restaura el mensaje para evaluarlo con IA'
                                                        : `Evaluar este mensaje con ${selectedAiBrain}`
                                                }
                                                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-purple-600 px-2.5 py-2.5 text-xs font-bold text-white shadow-sm transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:opacity-50"
                                            >
                                                <Sparkles
                                                    size={13}
                                                    className={
                                                        evaluatingMessageId === message.interactionId
                                                            ? 'animate-spin'
                                                            : ''
                                                    }
                                                />
                                                {evaluatingMessageId === message.interactionId
                                                    ? 'Evaluando...'
                                                    : 'Evaluar IA'}
                                            </button>
                                        )}

                                        <button
                                            type="button"
                                            onClick={() =>
                                                handleAnalyze(message)
                                            }
                                            disabled={
                                                status === 'discarded' ||
                                                analyzingMessageId !== null
                                            }
                                            title={
                                                status === 'discarded'
                                                    ? 'Restaura el mensaje para ver su análisis'
                                                    : 'Ver análisis en Analytics'
                                            }
                                            className="inline-flex w-full items-center justify-center gap-1 rounded-xl bg-slate-100 px-2.5 py-2.5 text-xs font-bold text-slate-700 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-50"
                                        >
                                            Analytics
                                            <ChevronRight
                                                size={14}
                                            />
                                        </button>
                                    </div>
                                </aside>
                            </div>
                        </article>
                    )
                })}
            </div>

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

function KpiCard({
    label,
    value,
    helper,
    valueClass = 'text-slate-900',
}: {
    label: string
    value: number
    helper: string
    valueClass?: string
}) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">{label}</p>

            <p className={`mt-2 text-3xl font-bold ${valueClass}`}>
                {value.toLocaleString('es-CO')}
            </p>

            <p className="mt-1 text-xs text-slate-400">
                {helper}
            </p>
        </div>
    )
}

function StatusBadge({
    status,
    isAnalyzed,
    workflowStage,
}: {
    status: CurationStatus
    isAnalyzed?: boolean
    workflowStage?: string
}) {
    if (status === 'discarded') {
        return (
            <span className="inline-flex w-full items-center justify-center gap-1.5 rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-[11px] font-bold text-rose-700">
                <ShieldAlert size={12} />
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
            <span className="inline-flex w-full items-center justify-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[11px] font-bold text-emerald-700">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Listo / Aprobado
            </span>
        )
    }

    // Si es totalmente crudo y le falta el análisis con IA
    if (!isAnalyzed || workflowStage === 'ingesta' || workflowStage === 'en_ingesta') {
        return (
            <span className="inline-flex w-full items-center justify-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-[11px] font-bold text-amber-700">
                <Clock3 size={12} />
                Falta análisis con IA
            </span>
        )
    }

    // Ya analizado por IA, pero le falta la parte de redacción / copy de Enoc
    return (
        <span className="inline-flex w-full items-center justify-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-[11px] font-bold text-indigo-700">
            <Sparkles size={12} />
            Falta redacción de copy
        </span>
    )
}

export default Messages