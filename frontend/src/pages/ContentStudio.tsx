import {
  AlertTriangle,
  BriefcaseBusiness,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Copy,
  Cpu,
  FileText,
  Layers,
  Megaphone,
  MessageCircle,
  Pencil,
  RotateCcw,
  Search,
  Send,
  Sparkles,
  Upload,
  X,
  XCircle,
} from 'lucide-react'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'

import {
  createContentDraft,
  executeMototradisPipeline,
  generateAnnouncement,
  generateComplaintResponse,
  generateMototradisChannelCopy,
  getAnnouncementWebhookStatus,
  getComplaintPublishPreview,
  getMototradisCheckpoint,
  getPublishedComplaintIds,
  publishAnnouncement,
  publishComplaintResponse,
  publishMototradisChannel,
  regenerateContent,
  runMototradisMassProcess,
  getMototradisMassQueueStatus,
  submitMototradisHitlDecision,
} from '../api/contentWorkflow'
import type {
  AIProviderOption,
  AnnouncementWebhookStatus,
  ComplaintPublishPreview,
  MototradisCheckpointState,
  MototradisMassResult,
  MototradisModelosUtilizados,
} from '../api/contentWorkflow'
import { getCommunityLiveSummary } from '../api/communityLive'
import { updateMessageWorkflow } from '../api/messageWorkflow'

const AI_PROVIDERS = [
  'Groq (Llama 3.3)',
  'Google Gemma 4',
  'Google Gemini Flash Lite',
] as const

type DiscordAttachment = {
  id: string
  filename: string
  content_type: string | null
  size: number
  url: string
}

type WorkflowMessage = {
  interactionId: number
  author: string
  channel: string
  content: string
  topic: string
  sentiment: string
  relevance: number
  attachments: DiscordAttachment[]
  isPublished?: boolean
  publishedPlatforms?: string[]
}

type WorkflowMessagesResponse = {
  messages: Array<{
    message: {
      interaction_id: number
      author_name: string
      channel_name: string
      content: string
      attachments?: DiscordAttachment[]
    }
    analysis: {
      workflow_stage: string
      topic: string
      sentiment: string
      relevance: number
      curation_status?: string
      is_published?: boolean
      published_platforms?: string[]
    }
  }>
}

type ContentFormat = 'linkedin' | 'x' | 'discord'

type DraftState = {
  interactionId?: number
  attachments?: DiscordAttachment[]
  content: string
  submitted: boolean
  submitting?: boolean
  regenerating?: boolean
  error?: string
  savedId?: number
}

function buildDefaultDrafts(
  message?: WorkflowMessage | null,
): Record<ContentFormat, DraftState> {
  return {
    linkedin: {
      interactionId: message?.interactionId,
      content: '',
      submitted: false,
    },
    x: {
      interactionId: message?.interactionId,
      content: '',
      submitted: false,
    },
    discord: {
      interactionId: message?.interactionId,
      attachments: message?.attachments ? [...message.attachments] : [],
      content: '',
      submitted: false,
    },
  }
}

function isOmittedByOrchestrator(text?: string): boolean {
  if (!text) return false
  const t = text.trim()
  return (
    t.startsWith('El orquestador omitió') ||
    t.startsWith('El orquestador no priorizó') ||
    t.startsWith('ℹ️ El orquestador')
  )
}

function ContentStudio() {
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [manualIdInput, setManualIdInput] = useState('')
  const [manualIdError, setManualIdError] = useState<string | null>(null)

  const interactionParam =
    searchParams.get('interaction') ||
    (location.state as { interactionId?: number | string } | null)?.interactionId
  const targetInteractionId = interactionParam
    ? parseInt(String(interactionParam), 10)
    : null

  const [activeFormat, setActiveFormat] =
    useState<ContentFormat>('linkedin')
  const [workspaceModalChannel, setWorkspaceModalChannel] = useState<
    'linkedin' | 'x' | 'discord' | 'all' | null
  >(null)
  const [copiedFormat, setCopiedFormat] =
    useState<ContentFormat | null>(null)
  const [showDiscordFiles, setShowDiscordFiles] =
    useState(false)
  const [drafts, setDrafts] = useState<
    Record<ContentFormat, DraftState>
  >(() => buildDefaultDrafts(null))

  const [workflowMessages, setWorkflowMessages] =
    useState<WorkflowMessage[]>([])
  const [allFetchedMessages, setAllFetchedMessages] =
    useState<WorkflowMessage[]>([])
  const [pinnedSearchMessage, setPinnedSearchMessage] =
    useState<WorkflowMessage | null>(null)
  const [activeWorkbenchMessage, setActiveWorkbenchMessage] =
    useState<WorkflowMessage | null>(null)
  const [selectedMessageId, setSelectedMessageId] =
    useState<number | null>(null)
  const selectedWorkflowId = selectedMessageId
  const setSelectedWorkflowId = setSelectedMessageId

  const [workflowLoading, setWorkflowLoading] = useState(true)
  const [workflowError, setWorkflowError] = useState('')

  // Pestañas de organización visual (Design System de Cristian): Bandeja, Anuncios oficiales y Quejas y soporte
  const [activeContentTab, setActiveContentTab] = useState<
    'inbox' | 'announcements' | 'complaints'
  >(() => (location.hash === '#panel-quejas' ? 'complaints' : 'inbox'))

  const originalMessageRef = useRef<HTMLElement | null>(null)
  const trayCardRefs = useRef<Record<number, HTMLButtonElement | null>>({})

  const displayedTrayMessages = useMemo<WorkflowMessage[]>(() => {
    if (
      pinnedSearchMessage &&
      !workflowMessages.some(
        (m) => m.interactionId === pinnedSearchMessage.interactionId,
      )
    ) {
      return [pinnedSearchMessage, ...workflowMessages]
    }
    return workflowMessages
  }, [pinnedSearchMessage, workflowMessages])

  const scrollTrayCardIntoView = (interactionId: number) => {
    setTimeout(() => {
      const cardEl = trayCardRefs.current[interactionId]
      if (cardEl && typeof cardEl.scrollIntoView === 'function') {
        cardEl.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'center',
        })
      }
    }, 80)
  }

  // Estados de Anuncios Oficiales (Discord Webhook)
  const [announcementStatus, setAnnouncementStatus] =
    useState<AnnouncementWebhookStatus | null>(null)
  const [announcementStatusLoading, setAnnouncementStatusLoading] =
    useState(true)
  const [selectedAnnouncementModel, setSelectedAnnouncementModel] =
    useState<string>('gemini')
  const [selectedDiscordChannel, setSelectedDiscordChannel] =
    useState<string>('webhook')
  const [draftText, setDraftText] = useState('')
  const [isGeneratingAnnouncement, setIsGeneratingAnnouncement] =
    useState(false)
  const [announcementGenerateError, setAnnouncementGenerateError] =
    useState('')
  const [finalAnnouncement, setFinalAnnouncement] = useState('')
  const [announcementPublishSuccess, setAnnouncementPublishSuccess] =
    useState('')
  const [announcementPublishError, setAnnouncementPublishError] =
    useState('')
  const [isPublishingAnnouncement, setIsPublishingAnnouncement] =
    useState(false)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    let isMounted = true
    getAnnouncementWebhookStatus()
      .then((status) => {
        if (isMounted) {
          setAnnouncementStatus(status)
          if (status.channels && status.channels.length > 0) {
            const defaultChan = status.channels.find((c) => c.id === 'webhook') || status.channels[0]
            if (defaultChan) {
              setSelectedDiscordChannel(defaultChan.id)
            }
          }
        }
      })
      .catch((err) => {
        console.error('Error al consultar estado del webhook de anuncios:', err)
        if (isMounted) {
          setAnnouncementStatus({
            configured: false,
            channel_hint: 'notificaciones',
            max_characters_recommended: 1500,
            max_characters_limit: 2000,
            warning: 'No se pudo conectar con el servicio de anuncios',
          })
        }
      })
      .finally(() => {
        if (isMounted) {
          setAnnouncementStatusLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setWorkspaceModalChannel(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    const loadWorkflowMessages = async () => {
      setWorkflowLoading(true)
      setWorkflowError('')

      try {
        const motorApiUrl = (
          import.meta.env.VITE_API_URL ||
          import.meta.env.VITE_MOTOR_API_URL ||
          'http://127.0.0.1:8002'
        ).replace(/\/$/, '')

        const response = await fetch(
          `${motorApiUrl}/api/community/messages?limit=500`,
          { signal: controller.signal },
        )

        if (!response.ok) {
          throw new Error('No se pudo consultar el Motor IA')
        }

        const data: WorkflowMessagesResponse = await response.json()

        const allMapped: WorkflowMessage[] = data.messages.map((item) => ({
          interactionId: item.message.interaction_id,
          author: item.message.author_name || 'Usuario',
          channel: item.message.channel_name,
          content: item.message.content,
          attachments: Array.isArray(item.message.attachments)
            ? item.message.attachments
            : [],
          topic: item.analysis.topic,
          sentiment: item.analysis.sentiment,
          relevance: item.analysis.relevance,
          isPublished: Boolean(item.analysis.is_published),
          publishedPlatforms: item.analysis.published_platforms || [],
        }))

        let messages = data.messages
          .filter(
            (item) =>
              (item.analysis.relevance >= 70 || item.analysis.curation_status === 'curated') &&
              item.analysis.curation_status !== 'discarded' &&
              !item.analysis.is_published &&
              (!item.analysis.published_platforms || item.analysis.published_platforms.length === 0),
          )
          .map((item) => ({
            interactionId: item.message.interaction_id,
            author: item.message.author_name || 'Usuario',
            channel: item.message.channel_name,
            content: item.message.content,
            attachments: Array.isArray(item.message.attachments)
              ? item.message.attachments
              : [],
            topic: item.analysis.topic,
            sentiment: item.analysis.sentiment,
            relevance: item.analysis.relevance,
            isPublished: Boolean(item.analysis.is_published),
            publishedPlatforms: item.analysis.published_platforms || [],
          }))
          .sort((a, b) => b.interactionId - a.interactionId)

        let targetMsg: WorkflowMessage | null = null
        let isPinnedTarget = false
        if (targetInteractionId && !Number.isNaN(targetInteractionId)) {
          const foundInTray = messages.find(
            (m) => m.interactionId === targetInteractionId,
          )

          if (foundInTray) {
            targetMsg = foundInTray
            isPinnedTarget = false
          } else {
            const foundInAll = allMapped.find(
              (item) => item.interactionId === targetInteractionId,
            )
            if (foundInAll) {
              targetMsg = foundInAll
              isPinnedTarget = true
            } else {
              try {
                const liveSummary = await getCommunityLiveSummary()
                const highlight = liveSummary.highlights?.find(
                  (h) => (h.id_mensaje ?? Number(h.id)) === targetInteractionId,
                )
                if (highlight) {
                  targetMsg = {
                    interactionId: highlight.id_mensaje ?? Number(highlight.id),
                    author: highlight.author || 'Usuario',
                    channel: (highlight.channel || 'general').replace(/^#/, ''),
                    content: highlight.message || '',
                    attachments: [],
                    topic: highlight.title || 'Historia destacada',
                    sentiment:
                      typeof highlight.sentiment === 'number'
                        ? highlight.sentiment >= 0.5
                          ? 'positive'
                          : highlight.sentiment <= -0.5
                          ? 'negative'
                          : 'neutral'
                        : String(highlight.sentiment || 'neutral'),
                    relevance:
                      typeof highlight.relevance === 'number'
                        ? Math.round(
                            highlight.relevance <= 1
                              ? highlight.relevance * 100
                              : highlight.relevance,
                          )
                        : 80,
                    isPublished: Boolean(highlight.is_published),
                    publishedPlatforms: highlight.published_platforms || [],
                  }
                  isPinnedTarget = true
                }
              } catch (err) {
                console.error(
                  'Error al consultar live-summary para interacción:',
                  err,
                )
              }
            }
          }
        }

        if (!controller.signal.aborted) {
          setAllFetchedMessages(allMapped)
          setWorkflowMessages(messages)
          setPinnedSearchMessage(isPinnedTarget ? targetMsg : null)

          const initialMsg = targetMsg || messages[0] || null
          const initialSelectedId = initialMsg?.interactionId ?? null

          setSelectedMessageId(initialSelectedId)
          setActiveWorkbenchMessage(initialMsg)

          if (initialMsg) {
            setDrafts(buildDefaultDrafts(initialMsg))
            if (targetMsg) {
              setManualIdError(null)
              scrollTrayCardIntoView(targetMsg.interactionId)
              setTimeout(() => {
                originalMessageRef.current?.scrollIntoView({
                  behavior: 'smooth',
                  block: 'start',
                })
              }, 100)
            }
          }
          if (targetInteractionId && !targetMsg) {
            setManualIdError(`Mensaje #${targetInteractionId} no encontrado`)
          }
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setWorkflowError(
            error instanceof Error
              ? error.message
              : 'No fue posible cargar los mensajes',
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setWorkflowLoading(false)
        }
      }
    }

    void loadWorkflowMessages()

    return () => controller.abort()
  }, [targetInteractionId])

  useEffect(() => {
    if (!targetInteractionId || Number.isNaN(targetInteractionId)) return
    setActiveContentTab('inbox')
    setManualIdInput(String(targetInteractionId))
  }, [targetInteractionId])

  const PREFERRED_ANNOUNCEMENT_CHANNELS_ORDER = useMemo(
    () => [
      'general',
      'faq',
      'pqrs',
      'chat-egresados',
      'oportunidades-laborales',
    ],
    [],
  )

  const availableDiscordChannels = useMemo<Array<{ id: string; name: string }>>(() => {
    const rawList: Array<{ id: string; name: string }> = (
      announcementStatus?.channels && announcementStatus.channels.length > 0
        ? announcementStatus.channels
        : [
            { id: 'webhook', name: '#notificaciones (Predeterminado)' },
            { id: '1550016804418621452', name: '#general' },
            { id: '1551309664397033513', name: '#faq' },
            { id: '1559244209884504245', name: '#pqrs' },
            { id: '1551309281041715230', name: '#chat-egresados' },
            { id: '1551309330198953994', name: '#oportunidades-laborales' },
          ]
    ).filter((ch) => !ch.name.toLowerCase().includes('anuncios'))

    const rawNotif =
      rawList.find(
        (c) => c.id === 'webhook' || c.name.toLowerCase().includes('notificaciones'),
      )
    const notifOption = {
      id: rawNotif?.id || 'webhook',
      name: '#notificaciones (Predeterminado)',
    }

    const otherChannels = rawList.filter(
      (c) => c.id !== notifOption.id && !c.name.toLowerCase().includes('notificaciones'),
    )

    otherChannels.sort((a, b) => {
      const cleanA = a.name.replace(/^#/, '').toLowerCase().trim()
      const cleanB = b.name.replace(/^#/, '').toLowerCase().trim()
      const indexA = PREFERRED_ANNOUNCEMENT_CHANNELS_ORDER.indexOf(cleanA)
      const indexB = PREFERRED_ANNOUNCEMENT_CHANNELS_ORDER.indexOf(cleanB)
      if (indexA !== -1 && indexB !== -1) return indexA - indexB
      if (indexA !== -1) return -1
      if (indexB !== -1) return 1
      return cleanA.localeCompare(cleanB)
    })

    return [notifOption, ...otherChannels]
  }, [announcementStatus, PREFERRED_ANNOUNCEMENT_CHANNELS_ORDER])

  const selectedTargetChannelName =
    availableDiscordChannels.find((c) => c.id === selectedDiscordChannel)?.name ||
    '#notificaciones'

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.txt') && !file.name.endsWith('.md')) {
      setAnnouncementPublishError('Solo se admiten archivos .txt o .md')
      return
    }

    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result
      if (typeof text === 'string') {
        setFinalAnnouncement(text)
        setAnnouncementPublishError('')
        setAnnouncementPublishSuccess('')
      }
    }
    reader.onerror = () => {
      setAnnouncementPublishError('Error al leer el archivo seleccionado.')
    }
    reader.readAsText(file, 'utf-8')
    e.target.value = ''
  }

  const handleGenerateAnnouncement = async () => {
    const borrador = draftText.trim()
    if (!borrador || borrador.length > 10000) return

    setIsGeneratingAnnouncement(true)
    setAnnouncementGenerateError('')

    try {
      const result = await generateAnnouncement(borrador, selectedAnnouncementModel)
      setFinalAnnouncement(result.anuncio_generado)
    } catch (error) {
      setAnnouncementGenerateError(
        error instanceof Error
          ? error.message
          : 'No fue posible generar el anuncio con IA.',
      )
    } finally {
      setIsGeneratingAnnouncement(false)
    }
  }

  const handleConfirmPublish = async () => {
    const content = finalAnnouncement.trim()
    if (!content || content.length > 2000 || !announcementStatus?.configured)
      return

    setIsPublishingAnnouncement(true)
    setAnnouncementPublishError('')
    setAnnouncementPublishSuccess('')

    try {
      const res = await publishAnnouncement(content, true, selectedDiscordChannel)
      setShowConfirmModal(false)
      const targetLabel = res.canal_destino || selectedTargetChannelName
      setAnnouncementPublishSuccess(
        `✓ Anuncio publicado exitosamente en ${targetLabel}. (ID #${res.id_contenido ?? 'auditado'}, ${res.caracteres} caracteres).`,
      )
      setFinalAnnouncement('')
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : 'Error al publicar anuncio en Discord.'
      const isRateLimit =
        errMsg.includes('429') ||
        errMsg.includes('1015') ||
        errMsg.toLowerCase().includes('rate limit') ||
        errMsg.toLowerCase().includes('too many requests')
      setAnnouncementPublishError(
        isRateLimit
          ? '⚠️ Discord ha limitado temporalmente el envío por límite de peticiones de Cloudflare (Error 1015 / 429). Tu borrador se mantiene intacto. Intenta en unos minutos o realiza la publicación desde tu entorno local.'
          : errMsg
      )
      setShowConfirmModal(false)
    } finally {
      setIsPublishingAnnouncement(false)
    }
  }

  const selectedWorkflowMessage =
    activeWorkbenchMessage && activeWorkbenchMessage.interactionId === selectedWorkflowId
      ? activeWorkbenchMessage
      : workflowMessages.find(
          (item) => item.interactionId === selectedWorkflowId,
        ) ?? activeWorkbenchMessage ?? null

  const [complaintAiProvider, setComplaintAiProvider] =
    useState<string>('Groq (Llama 3.3)')
  const [workspaceAiProvider, setWorkspaceAiProvider] =
    useState<string>('Groq (Llama 3.3)')

  const [activeComplaint, setActiveComplaint] = useState<number | null>(null)
  const activeComplaintRef = useRef<number | null>(null)
  const complaintRequestRef = useRef(0)
  const [complaintResponse, setComplaintResponse] = useState('')
  const [complaintGenerating, setComplaintGenerating] = useState(false)
  const [complaintGenerationError, setComplaintGenerationError] = useState('')
  const [complaintPublishing, setComplaintPublishing] = useState(false)
  const [complaintPublishError, setComplaintPublishError] = useState('')
  const [complaintPublishSuccess, setComplaintPublishSuccess] = useState('')
  const complaintPublishingRef = useRef(false)
  const complaintPublishLockedIds = useRef(new Set<number>())

  const [complaintDestination, setComplaintDestination] =
    useState<ComplaintPublishPreview | null>(null)
  const [complaintDestinationLoading, setComplaintDestinationLoading] =
    useState(false)
  const [complaintDestinationError, setComplaintDestinationError] =
    useState('')
  const complaintDestinationRequestRef = useRef(0)

  useEffect(() => {
    const interaccionId = activeComplaint
    const requestId = ++complaintDestinationRequestRef.current

    setComplaintDestination(null)
    setComplaintDestinationError('')

    if (interaccionId === null) {
      setComplaintDestinationLoading(false)
      return
    }

    setComplaintDestinationLoading(true)

    void getComplaintPublishPreview(interaccionId)
      .then((destino) => {
        if (complaintDestinationRequestRef.current !== requestId) return

        setComplaintDestination(destino)
      })
      .catch((error: unknown) => {
        if (complaintDestinationRequestRef.current !== requestId) return

        setComplaintDestinationError(
          error instanceof Error
            ? error.message
            : 'No fue posible verificar el destino de Discord.',
        )
      })
      .finally(() => {
        if (complaintDestinationRequestRef.current !== requestId) return

        setComplaintDestinationLoading(false)
      })

    return () => {
      if (complaintDestinationRequestRef.current === requestId) {
        complaintDestinationRequestRef.current += 1
      }
    }
  }, [activeComplaint])

  void setComplaintDestination
  void setComplaintDestinationLoading
  void setComplaintDestinationError
  void complaintDestinationRequestRef
  void complaintDestination
  void complaintDestinationLoading
  void complaintDestinationError



  type Complaint = {
    id: number
    texto: string
    autor: string | null
    canal: string | null
    sentimiento: string | null
    relevancia: number | null
    clasificacion: string
  }

  const [complaints, setComplaints] = useState<Complaint[]>([])
  const [complaintsLoading, setComplaintsLoading] = useState(true)
  const [complaintsError, setComplaintsError] = useState('')

  useEffect(() => {
    const controller = new AbortController()

    const cargarQuejas = async () => {
      try {
        setComplaintsLoading(true)
        setComplaintsError('')

        const motorApiUrl = (
          import.meta.env.VITE_API_URL ||
          import.meta.env.VITE_MOTOR_API_URL ||
          'http://127.0.0.1:8002'
        ).replace(/\/$/, '')

        const response = await fetch(
          `${motorApiUrl}/api/community/complaints`,
          { signal: controller.signal }
        )

        if (!response.ok) {
          throw new Error(`Error HTTP ${response.status}`)
        }

        const data: { items: Complaint[] } = await response.json()

        const publishedIds = await getPublishedComplaintIds()
        const publishedSet = new Set(publishedIds)

        if (!controller.signal.aborted) {
          setComplaints(
            data.items.filter((complaint) => !publishedSet.has(complaint.id))
          )
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setComplaintsError(
            error instanceof Error
              ? error.message
              : 'No se pudieron cargar las posibles quejas.'
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setComplaintsLoading(false)
        }
      }
    }

    void cargarQuejas()

    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (location.hash === '#panel-quejas') {
      setActiveContentTab('complaints')
      const timer = setTimeout(() => {
        const el = document.getElementById('panel-quejas')
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
      }, 150)
      return () => clearTimeout(timer)
    }
  }, [location.hash, complaintsLoading])

  const discordFiles = (drafts.discord.attachments ?? []).filter(
    (file) =>
      file.filename.trim().length > 0 &&
      /^https:\/\//i.test(file.url),
  )

  const formatDiscordFileSize = (bytes: number) => {
    if (!Number.isFinite(bytes) || bytes < 0) return 'Tamaño desconocido'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const updateContent = (
    format: ContentFormat,
    content: string,
  ) => {
    setDrafts((current) => ({
      ...current,
      [format]: {
        ...current[format],
        content,
      },
    }))
  }

  const prepareWorkflowContent = (chosenMessage?: WorkflowMessage) => {
    const message = chosenMessage ?? selectedWorkflowMessage
    if (!message) return
    setActiveWorkbenchMessage(message)
    const source = message.content.trim()

    if (!source) return

    setDrafts(buildDefaultDrafts(message))
    setActiveFormat('linkedin')
    setShowDiscordFiles(false)
  }

  const handleCopy = async (format: ContentFormat) => {
    await navigator.clipboard.writeText(
      drafts[format].content,
    )

    setCopiedFormat(format)

    setTimeout(() => {
      setCopiedFormat(null)
    }, 2000)
  }

  const handleLoadById = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const raw = manualIdInput.trim()
    if (!raw) return
    const idNum = parseInt(raw, 10)
    if (Number.isNaN(idNum) || idNum <= 0) {
      setManualIdError('Ingresa un número de ID válido')
      return
    }
    setManualIdError(null)

    const inNaturalQueue = workflowMessages.find(
      (m) => m.interactionId === idNum,
    )
    if (inNaturalQueue) {
      setPinnedSearchMessage(null)
      setSelectedMessageId(inNaturalQueue.interactionId)
      setActiveWorkbenchMessage(inNaturalQueue)
      setDrafts(buildDefaultDrafts(inNaturalQueue))
      setSearchParams({ interaction: String(idNum) })
      scrollTrayCardIntoView(inNaturalQueue.interactionId)
      setTimeout(() => {
        originalMessageRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }, 100)
      return
    }

    let resolved: WorkflowMessage | null =
      allFetchedMessages.find((m) => m.interactionId === idNum) ?? null

    if (!resolved) {
      try {
        const liveSummary = await getCommunityLiveSummary()
        const highlight = liveSummary.highlights?.find(
          (h) => (h.id_mensaje ?? Number(h.id)) === idNum,
        )
        if (highlight) {
          resolved = {
            interactionId: highlight.id_mensaje ?? Number(highlight.id),
            author: highlight.author || 'Usuario',
            channel: (highlight.channel || 'general').replace(/^#/, ''),
            content: highlight.message || '',
            attachments: [],
            topic: highlight.title || 'Historia destacada',
            sentiment:
              typeof highlight.sentiment === 'number'
                ? highlight.sentiment >= 0.5
                  ? 'positive'
                  : highlight.sentiment <= -0.5
                  ? 'negative'
                  : 'neutral'
                : String(highlight.sentiment || 'neutral'),
            relevance:
              typeof highlight.relevance === 'number'
                ? Math.round(
                    highlight.relevance <= 1
                      ? highlight.relevance * 100
                      : highlight.relevance,
                  )
                : 80,
            isPublished: Boolean(highlight.is_published),
            publishedPlatforms: highlight.published_platforms || [],
          }
        }
      } catch (err) {
        console.error('Error al consultar live-summary por ID:', err)
      }
    }

    if (resolved) {
      setPinnedSearchMessage(resolved)
      setSelectedMessageId(resolved.interactionId)
      setActiveWorkbenchMessage(resolved)
      setDrafts(buildDefaultDrafts(resolved))
      setSearchParams({ interaction: String(idNum) })
      scrollTrayCardIntoView(resolved.interactionId)
      setTimeout(() => {
        originalMessageRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }, 100)
    } else {
      setManualIdError(`Mensaje #${idNum} no encontrado`)
    }
  }

  const handleSearchById = handleLoadById

  const submittingRef = useRef<Set<ContentFormat>>(new Set())

  const handleSubmit = async (format: ContentFormat) => {
    const draft = drafts[format]
    const content = draft.content.trim()

    if (draft.submitted || submittingRef.current.has(format)) return

    if (!draft.savedId && !content) {
      setDrafts((current) => ({
        ...current,
        [format]: {
          ...current[format],
          error: 'Escribe un contenido antes de enviarlo.',
        },
      }))
      return
    }

    if (!draft.savedId && format === 'x' && [...content].length > 280) {
      setDrafts((current) => ({
        ...current,
        [format]: {
          ...current[format],
          error: 'El contenido supera los 280 caracteres.',
        },
      }))
      return
    }

    submittingRef.current.add(format)

    setDrafts((current) => ({
      ...current,
      [format]: {
        ...current[format],
        submitting: true,
        error: '',
      },
    }))

    let savedId = draft.savedId

    try {
      if (!savedId) {
        const result = await createContentDraft({
          interaccion_id: draft.interactionId,
          plataforma: format,
          titulo: `Contenido ${format.toUpperCase()} - ${new Date().toLocaleDateString('es-CO')}`,
          contenido: content,
          tono: 'profesional',
          tipo_contenido: 'publicacion',
        })

        savedId = result.id

        setDrafts((current) => ({
          ...current,
          [format]: {
            ...current[format],
            savedId: result.id,
          },
        }))
      }

      if (draft.interactionId) {
        await updateMessageWorkflow(draft.interactionId, 'en_aprobacion')
      }

      setDrafts((current) => ({
        ...current,
        [format]: {
          ...current[format],
          submitted: true,
          submitting: false,
          savedId,
          error: '',
        },
      }))
    } catch (error) {
      setDrafts((current) => ({
        ...current,
        [format]: {
          ...current[format],
          submitting: false,
          savedId,
          error:
            error instanceof Error
              ? error.message
              : 'No fue posible guardar el contenido en la plataforma.',
        },
      }))
    } finally {
      submittingRef.current.delete(format)
    }
  }

  const regeneratingRef = useRef<Set<ContentFormat>>(new Set())
  const draftsRef = useRef(drafts)
  draftsRef.current = drafts

  const handleRegenerate = async (format: ContentFormat) => {
    const draft = draftsRef.current[format]

    if (
      draft.submitted ||
      draft.submitting ||
      draft.savedId ||
      regeneratingRef.current.has(format)
    ) return

    const message =
      displayedTrayMessages.find(
        (item) => item.interactionId === draft.interactionId,
      ) ??
      (activeWorkbenchMessage?.interactionId === draft.interactionId
        ? activeWorkbenchMessage
        : undefined)

    if (!message || !message.content.trim()) {
      setDrafts((current) => ({
        ...current,
        [format]: {
          ...current[format],
          error: 'Selecciona primero un mensaje real de Discord para regenerar.',
        },
      }))
      return
    }

    const interactionId = message.interactionId
    const originalContent = draft.content

    regeneratingRef.current.add(format)
    setActiveFormat(format)

    setDrafts((current) => ({
      ...current,
      [format]: {
        ...current[format],
        regenerating: true,
        error: '',
      },
    }))

    try {
      const result = await regenerateContent({
        texto: message.content,
        canal: message.channel,
        formato: format,
        tono: 'profesional',
        proveedor: workspaceAiProvider,
      })

      setDrafts((current) => {
        const actual = current[format]

        if (
          actual.interactionId !== interactionId ||
          actual.submitted ||
          actual.submitting ||
          actual.savedId ||
          actual.content !== originalContent
        ) {
          return current
        }

        return {
          ...current,
          [format]: {
            ...actual,
            content: result.contenido,
            regenerating: false,
            error: '',
          },
        }
      })
    } catch (error) {
      setDrafts((current) => {
        if (current[format].interactionId !== interactionId) return current

        return {
          ...current,
          [format]: {
            ...current[format],
            error: error instanceof Error
              ? error.message
              : 'No fue posible regenerar el contenido.',
          },
        }
      })
    } finally {
      regeneratingRef.current.delete(format)

      setDrafts((current) => {
        if (current[format].interactionId !== interactionId) return current

        return {
          ...current,
          [format]: {
            ...current[format],
            regenerating: false,
          },
        }
      })
    }
  }

  // Estados de Pipeline Mototradis (Orquestador LangGraph MVP de Enoc)
  const [pipelineData, setPipelineData] = useState<MototradisCheckpointState | null>(null)
  const [pipelineLoading, setPipelineLoading] = useState(false)
  const [pipelineExecuting, setPipelineExecuting] = useState(false)
  const [pipelineActionMessage, setPipelineActionMessage] = useState('')
  const [pipelineActionError, setPipelineActionError] = useState('')

  // Campos específicos de redacción enriquecida por canal
  const [linkedinTitle, setLinkedinTitle] = useState('')
  const [linkedinCopyTono, setLinkedinCopyTono] = useState('')
  const [linkedinNewsletter, setLinkedinNewsletter] = useState<{ destaque?: string; resumen?: string } | null>(null)
  const [linkedinFaq, setLinkedinFaq] = useState<{ sugerencia?: string; respuesta?: string } | null>(null)
  const [showLinkedinExtras, setShowLinkedinExtras] = useState(false)

  const [xTitle, setXTitle] = useState('')
  const [discordTitle, setDiscordTitle] = useState('')
  const [discordSelectedChannel, setDiscordSelectedChannel] = useState('general')

  // Publicación individual por canal
  const [channelPublishing, setChannelPublishing] = useState<Record<string, boolean>>({})
  const [channelPublishResult, setChannelPublishResult] = useState<Record<string, { ok: boolean; detalle: string; url?: string }>>({})

  // Procesamiento masivo con Gemma 4
  const [massProcessing, setMassProcessing] = useState(false)
  const [massResult, setMassResult] = useState<MototradisMassResult | null>(null)
  const [massLimit, setMassLimit] = useState(10)
  const [massError, setMassError] = useState('')
  const [massQueueCount, setMassQueueCount] = useState<number>(0)
  const [massQueueLoading, setMassQueueLoading] = useState<boolean>(true)

  // Cargar estado de la cola de baja relevancia (< 35)
  useEffect(() => {
    let isMounted = true
    setMassQueueLoading(true)
    getMototradisMassQueueStatus()
      .then((res) => {
        if (isMounted) {
          setMassQueueCount(res.total_en_cola ?? 0)
        }
      })
      .catch((err) => {
        console.warn('Error al consultar cola masiva de baja relevancia:', err)
      })
      .finally(() => {
        if (isMounted) setMassQueueLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [])

  // Modelos de IA utilizados reportados reactivamente
  const modelosUtilizados: MototradisModelosUtilizados = useMemo(() => {
    return {
      orquestador: pipelineData?.modelos_utilizados?.orquestador || 'Google Gemini · gemini-2.5-flash',
      linkedin: pipelineData?.modelos_utilizados?.linkedin || 'Google Gemini · gemini-2.5-flash-lite',
      x: pipelineData?.modelos_utilizados?.x || 'Groq · qwen/qwen-2.5-32b',
      discord: pipelineData?.modelos_utilizados?.discord || 'Groq · llama-3.3-70b-versatile',
      pqrs: pipelineData?.modelos_utilizados?.pqrs || 'Google Gemini · gemini-2.5-flash-lite',
      masivo: pipelineData?.modelos_utilizados?.masivo || 'Google Gemma 4 · gemma-4-31b-it',
    }
  }, [pipelineData])

  const publishedPlatformNames = useMemo<string[]>(() => {
    const set = new Set<string>()
    if (activeWorkbenchMessage?.publishedPlatforms) {
      activeWorkbenchMessage.publishedPlatforms.forEach((p) => {
        const pNorm = p.toLowerCase()
        if (pNorm === 'discord') set.add('Discord')
        if (pNorm === 'linkedin') set.add('LinkedIn')
        if (pNorm === 'x' || pNorm === 'twitter') set.add('X')
      })
    }
    if (pipelineData?.plataformas_publicadas) {
      pipelineData.plataformas_publicadas.forEach((p) => {
        const pNorm = p.toLowerCase()
        if (pNorm === 'discord') set.add('Discord')
        if (pNorm === 'linkedin') set.add('LinkedIn')
        if (pNorm === 'x' || pNorm === 'twitter') set.add('X')
      })
    }
    if (drafts.discord.submitted) set.add('Discord')
    if (drafts.linkedin.submitted) set.add('LinkedIn')
    if (drafts.x.submitted) set.add('X')

    return ['Discord', 'LinkedIn', 'X'].filter((p) => set.has(p))
  }, [activeWorkbenchMessage, pipelineData, drafts])

  const isCurrentlyPublished = publishedPlatformNames.length > 0

  // Carga reactiva del Checkpoint de Mototradis al seleccionar un mensaje
  useEffect(() => {
    if (!selectedMessageId) {
      setPipelineData(null)
      return
    }

    let isMounted = true
    setPipelineLoading(true)
    setPipelineActionMessage('')
    setPipelineActionError('')

    getMototradisCheckpoint(selectedMessageId)
      .then((checkpoint) => {
        if (!isMounted) return
        setPipelineData(checkpoint)

        if (checkpoint.has_checkpoint && checkpoint.borradores_ui) {
          const bui = checkpoint.borradores_ui

          let liText = ''
          if (typeof bui.linkedin === 'string') {
            liText = bui.linkedin
          } else if (bui.linkedin && typeof bui.linkedin === 'object') {
            liText = bui.linkedin.texto_copy || ''
            if (bui.linkedin.titulo) setLinkedinTitle(bui.linkedin.titulo)
            if (bui.linkedin.copy_tono) setLinkedinCopyTono(bui.linkedin.copy_tono)
            if (bui.linkedin.newsletter) setLinkedinNewsletter(bui.linkedin.newsletter)
            if (bui.linkedin.faq) setLinkedinFaq(bui.linkedin.faq)
          }

          let xText = ''
          if (typeof bui.x === 'string') {
            xText = bui.x
          } else if (bui.x && typeof bui.x === 'object') {
            xText = bui.x.texto_copy || ''
            if (bui.x.titulo) setXTitle(bui.x.titulo)
          }

          let discordText = ''
          if (typeof bui.discord === 'string') {
            discordText = bui.discord
          } else if (bui.discord && typeof bui.discord === 'object') {
            discordText = bui.discord.texto_copy || ''
            if (bui.discord.titulo) setDiscordTitle(bui.discord.titulo)
            if (bui.discord.canal_seleccionado) setDiscordSelectedChannel(bui.discord.canal_seleccionado)
          }

          const plataformasPub = (checkpoint.plataformas_publicadas || []).map((p) => p.toLowerCase())
          setDrafts({
            linkedin: {
              interactionId: selectedMessageId,
              content: liText,
              submitted: plataformasPub.includes('linkedin'),
            },
            x: {
              interactionId: selectedMessageId,
              content: xText,
              submitted: plataformasPub.includes('x') || plataformasPub.includes('twitter'),
            },
            discord: {
              interactionId: selectedMessageId,
              content: discordText,
              submitted: plataformasPub.includes('discord'),
            },
          })
        } else {
          // Si no tiene checkpoint previo, limpiar las tarjetas para que no muestren textos residuales
          setLinkedinTitle('')
          setLinkedinCopyTono('')
          setLinkedinNewsletter({ destaque: '', resumen: '' })
          setLinkedinFaq({ sugerencia: '', respuesta: '' })
          setXTitle('')
          setDiscordTitle('')
          setDrafts({
            linkedin: { interactionId: selectedMessageId, content: '', submitted: false },
            x: { interactionId: selectedMessageId, content: '', submitted: false },
            discord: { interactionId: selectedMessageId, content: '', submitted: false },
          })
        }
      })
      .catch((err) => {
        console.warn('No se pudo cargar checkpoint de Mototradis:', err)
      })
      .finally(() => {
        if (isMounted) setPipelineLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [selectedMessageId])

  // Ejecución del pipeline LangGraph de Mototradis
  const handleExecuteMototradisPipeline = async () => {
    if (!selectedMessageId) return
    setPipelineExecuting(true)
    setWorkspaceModalChannel('all')
    setPipelineActionMessage('')
    setPipelineActionError('')

    try {
      const res = await executeMototradisPipeline(selectedMessageId, 'auto')
      setPipelineData(res)

      if (res.borradores_ui) {
        const bui = res.borradores_ui
        let liText = typeof bui.linkedin === 'string' ? bui.linkedin : bui.linkedin?.texto_copy || ''
        let xText = typeof bui.x === 'string' ? bui.x : bui.x?.texto_copy || ''
        let discordText = typeof bui.discord === 'string' ? bui.discord : bui.discord?.texto_copy || ''

        if (bui.linkedin && typeof bui.linkedin === 'object') {
          if (bui.linkedin.titulo) setLinkedinTitle(bui.linkedin.titulo)
          if (bui.linkedin.copy_tono) setLinkedinCopyTono(bui.linkedin.copy_tono)
          if (bui.linkedin.newsletter) setLinkedinNewsletter(bui.linkedin.newsletter)
          if (bui.linkedin.faq) setLinkedinFaq(bui.linkedin.faq)
        }
        if (bui.x && typeof bui.x === 'object') {
          if (bui.x.titulo) setXTitle(bui.x.titulo)
        }
        if (bui.discord && typeof bui.discord === 'object') {
          if (bui.discord.titulo) setDiscordTitle(bui.discord.titulo)
          if (bui.discord.canal_seleccionado) {
            setDiscordSelectedChannel(bui.discord.canal_seleccionado)
          }
        }

        setDrafts((prev) => ({
          linkedin: {
            ...prev.linkedin,
            interactionId: selectedMessageId,
            content: liText || prev.linkedin.content,
          },
          x: {
            ...prev.x,
            interactionId: selectedMessageId,
            content: xText || prev.x.content,
          },
          discord: {
            ...prev.discord,
            interactionId: selectedMessageId,
            content: discordText || prev.discord.content,
          },
        }))
      }

      if (res.aviso_fallback) {
        setPipelineActionMessage(res.aviso_fallback)
      } else {
        setPipelineActionMessage(
          `✓ Pipeline ejecutado exitosamente con orquestador LangGraph (${res.modelos_utilizados?.orquestador || 'Gemini'}). Borradores generados para canales activos.`
        )
      }
    } catch (error) {
      setPipelineActionError(
        error instanceof Error ? error.message : 'Error al ejecutar pipeline de redacción.'
      )
    } finally {
      setPipelineExecuting(false)
    }
  }

  // Regeneración individual de canal con IA
  const handleRegenerateChannelCopy = async (canal: 'linkedin' | 'x' | 'discord') => {
    if (!selectedMessageId) return
    setDrafts((prev) => ({
      ...prev,
      [canal]: { ...prev[canal], regenerating: true, error: '' },
    }))

    try {
      const res = await generateMototradisChannelCopy(
        selectedMessageId,
        canal,
        workspaceAiProvider as AIProviderOption,
      )
      const bui = res.borradores_ui || {}
      const canalData = bui[canal] || res.borrador || {}
      const nuevoTexto =
        typeof canalData === 'string'
          ? canalData
          : canalData.texto_copy || res.contenido || ''

      if (canal === 'linkedin' && typeof canalData === 'object') {
        if (canalData.titulo) setLinkedinTitle(canalData.titulo)
        if (canalData.copy_tono) setLinkedinCopyTono(canalData.copy_tono)
        if (canalData.newsletter) setLinkedinNewsletter(canalData.newsletter)
        if (canalData.faq) setLinkedinFaq(canalData.faq)
      } else if (canal === 'x' && typeof canalData === 'object') {
        if (canalData.titulo) setXTitle(canalData.titulo)
      } else if (canal === 'discord' && typeof canalData === 'object') {
        if (canalData.titulo) setDiscordTitle(canalData.titulo)
        if (canalData.canal_seleccionado) {
          setDiscordSelectedChannel(canalData.canal_seleccionado)
        }
      }

      setDrafts((prev) => ({
        ...prev,
        [canal]: {
          ...prev[canal],
          content: nuevoTexto || prev[canal].content,
          regenerating: false,
          error: '',
        },
      }))

      if (res.modelo_utilizado) {
        setPipelineData((prev) => {
          if (!prev) return prev
          return {
            ...prev,
            modelos_utilizados: {
              ...prev.modelos_utilizados,
              [canal]: res.modelo_utilizado,
            },
          }
        })
      }

      if (res.aviso_fallback) {
        setPipelineActionMessage(res.aviso_fallback)
      } else {
        setPipelineActionMessage(`✓ Copy de ${canal.toUpperCase()} regenerado con ${res.modelo_utilizado}.`)
      }
    } catch (err) {
      console.warn(`Fallback a regeneración estándar para ${canal}:`, err)
      await handleRegenerate(canal)
    } finally {
      setDrafts((prev) => ({
        ...prev,
        [canal]: { ...prev[canal], regenerating: false },
      }))
    }
  }

  // Publicación individual por canal
  const handlePublishChannelIndividual = async (canal: 'linkedin' | 'x' | 'discord') => {
    if (!selectedMessageId) return
    const draft = drafts[canal]
    const texto = draft.content.trim()
    if (!texto) return

    setChannelPublishing((prev) => ({ ...prev, [canal]: true }))
    setPipelineActionMessage('')
    setPipelineActionError('')

    try {
      const titulo =
        canal === 'linkedin' ? linkedinTitle : canal === 'x' ? xTitle : discordTitle
      const canalDestino = canal === 'discord' ? discordSelectedChannel : undefined

      const res = await publishMototradisChannel(
        selectedMessageId,
        canal,
        texto,
        canalDestino,
        titulo
      )
      setChannelPublishResult((prev) => ({
        ...prev,
        [canal]: { ok: res.ok, detalle: res.detalle, url: res.url },
      }))

      if (res.ok && res.estado_canal === 'enviado') {
        setDrafts((prev) => ({
          ...prev,
          [canal]: { ...prev[canal], submitted: true },
        }))
        const urlSuffix = res.url ? ` (${res.url})` : ''
        setPipelineActionMessage(`✓ Publicación en ${canal.toUpperCase()} exitosa: ${res.detalle}${urlSuffix}`)

        // Excluir de la bandeja de mensajes pero conservar en la mesa de trabajo
        setWorkflowMessages((prev) => prev.filter((m) => m.interactionId !== selectedMessageId))
        const canonName = canal === 'linkedin' ? 'LinkedIn' : canal === 'x' ? 'X' : 'Discord'
        setActiveWorkbenchMessage((prev) => {
          if (!prev) return prev
          const existing = prev.publishedPlatforms || []
          const updated = existing.includes(canonName) ? existing : [...existing, canonName]
          return {
            ...prev,
            isPublished: true,
            publishedPlatforms: updated,
          }
        })
        setPipelineData((prev) => {
          if (!prev) return prev
          const existing = prev.plataformas_publicadas || []
          const canalLower = canal.toLowerCase()
          const updated = existing.includes(canalLower) ? existing : [...existing, canalLower]
          return {
            ...prev,
            is_published: true,
            plataformas_publicadas: updated,
          }
        })
      } else {
        setDrafts((prev) => ({
          ...prev,
          [canal]: { ...prev[canal], submitted: false },
        }))
        setPipelineActionError(`Error al publicar en ${canal.toUpperCase()}: ${res.detalle}`)
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Error al publicar canal'
      setPipelineActionError(`Error al publicar en ${canal.toUpperCase()}: ${msg}`)
    } finally {
      setChannelPublishing((prev) => ({ ...prev, [canal]: false }))
    }
  }

  // Decisión global HITL (Human-in-the-Loop)
  const handleSubmitHitlDecision = async (aprobado: boolean) => {
    if (!selectedMessageId) return
    setPipelineExecuting(true)
    setPipelineActionMessage('')
    setPipelineActionError('')

    try {
      const copysEditados: Record<'linkedin' | 'x' | 'discord', any> = {
        linkedin: {
          titulo: linkedinTitle,
          texto_copy: isOmittedByOrchestrator(drafts.linkedin.content) ? '' : drafts.linkedin.content,
          copy_tono: linkedinCopyTono,
          newsletter: linkedinNewsletter,
          faq: linkedinFaq,
        },
        x: {
          titulo: xTitle,
          texto_copy: isOmittedByOrchestrator(drafts.x.content) ? '' : drafts.x.content,
        },
        discord: {
          titulo: discordTitle,
          texto_copy: isOmittedByOrchestrator(drafts.discord.content) ? '' : drafts.discord.content,
          canal_seleccionado: discordSelectedChannel,
        },
      }

      const res = await submitMototradisHitlDecision(
        selectedMessageId,
        aprobado,
        aprobado ? copysEditados : undefined,
        aprobado ? undefined : 'Desaprobado por operador humano'
      )

      if (aprobado && res.exito) {
        const resCanales = res.resultados_canales || {}
        const enviados: string[] = []
        const omitidos: string[] = []

        const fallidos: string[] = []
        Object.entries(resCanales).forEach(([ch, val]: [string, any]) => {
          if (val?.estado_canal === 'enviado') {
            enviados.push(ch.toUpperCase())
          } else if (val?.estado_canal === 'omitido' || val?.estado_canal === 'omitido_sin_credenciales') {
            omitidos.push(ch.toUpperCase())
          } else {
            fallidos.push(`${ch.toUpperCase()}: ${val?.detalle || 'Error'}`)
          }
        })

        let feedback = enviados.length > 0
          ? `✓ Publicado en: ${enviados.join(', ')}.`
          : `Lote procesado.`
        if (omitidos.length > 0) {
          feedback += ` Omitido en: ${omitidos.join(', ')}.`
        }
        if (fallidos.length > 0) {
          feedback += ` Falló en: ${fallidos.join('; ')}.`
        }

        if (fallidos.length > 0 && enviados.length === 0) {
          setPipelineActionError(feedback)
        } else {
          setPipelineActionMessage(feedback)
          if (fallidos.length > 0) {
            setPipelineActionError(`Atención: Falló la publicación en: ${fallidos.join('; ')}`)
          }
        }
        setDrafts((prev) => ({
          linkedin: { ...prev.linkedin, submitted: resCanales.linkedin?.estado_canal === 'enviado' },
          x: { ...prev.x, submitted: resCanales.x?.estado_canal === 'enviado' },
          discord: { ...prev.discord, submitted: resCanales.discord?.estado_canal === 'enviado' },
        }))

        if (enviados.length > 0) {
          // Excluir de la bandeja de mensajes pero conservar en la mesa de trabajo
          setWorkflowMessages((prev) => prev.filter((m) => m.interactionId !== selectedMessageId))
          const canonEnviados = enviados.map((e) =>
            e === 'LINKEDIN' ? 'LinkedIn' : e === 'X' ? 'X' : 'Discord'
          )
          setActiveWorkbenchMessage((prev) => {
            if (!prev) return prev
            const existing = prev.publishedPlatforms || []
            const combined = Array.from(new Set([...existing, ...canonEnviados]))
            return {
              ...prev,
              isPublished: true,
              publishedPlatforms: combined,
            }
          })
          setPipelineData((prev) => {
            if (!prev) return prev
            const existing = prev.plataformas_publicadas || []
            const lowerEnviados = canonEnviados.map((c) => c.toLowerCase())
            const combined = Array.from(new Set([...existing, ...lowerEnviados]))
            return {
              ...prev,
              is_published: true,
              plataformas_publicadas: combined,
            }
          })
        }
      } else {
        setPipelineActionMessage(
          `✓ Lote ${res.decision || 'desaprobado'} y checkpoint limpiado correctamente. El hilo queda listo para reintento.`
        )
      }

      const updatedCheckpoint = await getMototradisCheckpoint(selectedMessageId)
      setPipelineData(updatedCheckpoint)
      if (updatedCheckpoint.is_published && updatedCheckpoint.plataformas_publicadas) {
        const canonList = updatedCheckpoint.plataformas_publicadas.map((p) => {
          const pl = p.toLowerCase()
          return pl === 'linkedin' ? 'LinkedIn' : pl === 'x' || pl === 'twitter' ? 'X' : 'Discord'
        })
        setActiveWorkbenchMessage((prev) => prev ? { ...prev, isPublished: true, publishedPlatforms: canonList } : prev)
      }
    } catch (error) {
      setPipelineActionError(
        error instanceof Error ? error.message : 'Error al registrar decisión HITL.'
      )
    } finally {
      setPipelineExecuting(false)
    }
  }

  // Procesamiento Masivo de baja relevancia con Gemma 4
  const handleRunMassGemma = async () => {
    setMassProcessing(true)
    setMassError('')
    setMassResult(null)

    try {
      const res = await runMototradisMassProcess(massLimit)
      setMassResult(res)
      // Refrescar conteo de cola tras procesar
      const queueRes = await getMototradisMassQueueStatus()
      setMassQueueCount(queueRes.total_en_cola ?? 0)
    } catch (error) {
      setMassError(
        error instanceof Error ? error.message : 'Error en el procesamiento masivo con Gemma 4.'
      )
    } finally {
      setMassProcessing(false)
    }
  }

  const announcementDraft = finalAnnouncement.trim() || draftText.trim()

  const renderLinkedinCard = () => (
    <section
      className={`flex flex-col rounded-2xl border bg-white shadow-sm transition ${
        activeFormat === 'linkedin' ? 'border-orange-300 ring-2 ring-orange-50' : 'border-slate-200'
      }`}
    >
      <div className="border-b border-slate-100 p-3 sm:p-3.5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <BriefcaseBusiness size={16} />
            </div>
            <div className="min-w-0">
              <h3 className="text-xs font-bold text-slate-900 truncate">LinkedIn</h3>
              <p className="text-[11px] text-slate-400 truncate">Publicación profesional y networking</p>
            </div>
          </div>

          <span
            className={`shrink-0 c-chip ${
              drafts.linkedin.submitted
                ? 'c-chip--success'
                : isOmittedByOrchestrator(drafts.linkedin.content)
                ? 'c-chip--warning'
                : 'c-chip--brand'
            }`}
          >
            {drafts.linkedin.submitted
              ? '✓ Publicado'
              : isOmittedByOrchestrator(drafts.linkedin.content)
              ? 'Omitido'
              : 'Borrador'}
          </span>
        </div>

        <div className="mt-2 flex items-center min-w-0">
          <span className="c-chip c-chip--info max-w-full truncate inline-flex items-center gap-1" title={modelosUtilizados.linkedin}>
            <Cpu size={10} className="shrink-0" />
            <span className="truncate">{modelosUtilizados.linkedin}</span>
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col p-3.5 space-y-2">
        <div>
          <label htmlFor="linkedin-title" className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Título del Post
          </label>
          <input
            id="linkedin-title"
            type="text"
            value={linkedinTitle}
            disabled={drafts.linkedin.submitted}
            onChange={(e) => setLinkedinTitle(e.target.value)}
            placeholder="Ej: Reflexiones sobre nuestra comunidad de aprendizaje..."
            className="mt-1 w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-800 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-100 disabled:bg-slate-50"
          />
        </div>

        <div>
          <label htmlFor="content-linkedin" className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
            <Pencil size={11} />
            <span>Copy persuasivo editable</span>
          </label>
          <textarea
            id="content-linkedin"
            value={drafts.linkedin.content}
            disabled={drafts.linkedin.submitted}
            onFocus={() => setActiveFormat('linkedin')}
            onChange={(event) => updateContent('linkedin', event.target.value)}
            placeholder="Copy persuasivo para LinkedIn..."
            className={`mt-1 w-full min-h-[140px] flex-1 resize-y rounded-lg border p-2.5 text-xs leading-relaxed outline-none transition disabled:bg-slate-50 disabled:text-slate-500 ${
              isOmittedByOrchestrator(drafts.linkedin.content)
                ? 'border-amber-200 bg-amber-50/40 text-slate-700 italic'
                : 'border-slate-200 text-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-50'
            }`}
          />
        </div>

        {isOmittedByOrchestrator(drafts.linkedin.content) && (
          <div className="mt-2.5 flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-xs text-amber-900">
            <div className="flex items-center gap-1.5">
              <Sparkles size={14} className="shrink-0 text-amber-600" />
              <span>¿Deseas redactar copy para LinkedIn de todos modos?</span>
            </div>
            <button
              type="button"
              disabled={drafts.linkedin.regenerating}
              onClick={() => handleRegenerateChannelCopy('linkedin')}
              className="flex items-center gap-1.5 rounded-md bg-amber-600 px-2.5 py-1 text-xs font-bold text-white shadow-xs transition hover:bg-amber-700 disabled:bg-amber-400"
            >
              <RotateCcw size={12} className={drafts.linkedin.regenerating ? 'animate-spin' : ''} />
              {drafts.linkedin.regenerating ? 'Generando...' : 'Regenerar con IA'}
            </button>
          </div>
        )}

        {/* Extras Plegables (Copy tono, Newsletter, FAQ) */}
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3">
          <button
            type="button"
            onClick={() => setShowLinkedinExtras((prev) => !prev)}
            className="flex w-full items-center justify-between text-xs font-semibold text-slate-700 hover:text-blue-600"
          >
            <span>Formatos adicionales (Newsletter & FAQ)</span>
            {showLinkedinExtras ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          {showLinkedinExtras && (
            <div className="mt-3 space-y-3 border-t border-slate-200 pt-3 text-xs">
              <div>
                <label className="font-semibold text-slate-600">Copy de Tono / Alternativo:</label>
                <textarea
                  value={linkedinCopyTono}
                  onChange={(e) => setLinkedinCopyTono(e.target.value)}
                  placeholder="Variación en tono formal o reflexivo..."
                  rows={2}
                  className="mt-1 w-full rounded-md border border-slate-200 bg-white p-2 text-xs text-slate-700"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-600">Newsletter (Destaque & Resumen):</label>
                <input
                  type="text"
                  value={linkedinNewsletter?.destaque || ''}
                  onChange={(e) =>
                    setLinkedinNewsletter((prev) => ({ ...prev, destaque: e.target.value }))
                  }
                  placeholder="Destaque de Newsletter..."
                  className="mt-1 w-full rounded-md border border-slate-200 bg-white p-2 text-xs text-slate-700"
                />
                <textarea
                  value={linkedinNewsletter?.resumen || ''}
                  onChange={(e) =>
                    setLinkedinNewsletter((prev) => ({ ...prev, resumen: e.target.value }))
                  }
                  placeholder="Resumen para la entrega semanal..."
                  rows={2}
                  className="mt-1.5 w-full rounded-md border border-slate-200 bg-white p-2 text-xs text-slate-700"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-600">Sugerencia FAQ de la Comunidad:</label>
                <input
                  type="text"
                  value={linkedinFaq?.sugerencia || ''}
                  onChange={(e) =>
                    setLinkedinFaq((prev) => ({ ...prev, sugerencia: e.target.value }))
                  }
                  placeholder="Pregunta frecuente sugerida..."
                  className="mt-1 w-full rounded-md border border-slate-200 bg-white p-2 text-xs text-slate-700"
                />
                <textarea
                  value={linkedinFaq?.respuesta || ''}
                  onChange={(e) =>
                    setLinkedinFaq((prev) => ({ ...prev, respuesta: e.target.value }))
                  }
                  placeholder="Respuesta oficial sugerida..."
                  rows={2}
                  className="mt-1.5 w-full rounded-md border border-slate-200 bg-white p-2 text-xs text-slate-700"
                />
              </div>
            </div>
          )}
        </div>

        {/* Acciones auxiliares */}
        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleCopy('linkedin')}
            className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
          >
            {copiedFormat === 'linkedin' ? <CheckCircle size={14} /> : <Copy size={14} />}
            {copiedFormat === 'linkedin' ? 'Copiado' : 'Copiar'}
          </button>

          <button
            type="button"
            disabled={drafts.linkedin.submitted || drafts.linkedin.regenerating}
            onClick={() => handleRegenerateChannelCopy('linkedin')}
            className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-50"
          >
            <RotateCcw size={14} className={drafts.linkedin.regenerating ? 'animate-spin' : ''} />
            {drafts.linkedin.regenerating ? 'Regenerando...' : 'Regenerar'}
          </button>
        </div>

        {/* Publicar individual directo */}
        <button
          type="button"
          disabled={
            drafts.linkedin.submitted ||
            channelPublishing['linkedin'] ||
            !drafts.linkedin.content.trim() ||
            isOmittedByOrchestrator(drafts.linkedin.content)
          }
          title={
            drafts.linkedin.submitted
              ? 'Este contenido ya fue publicado exitosamente en LinkedIn'
              : isOmittedByOrchestrator(drafts.linkedin.content)
              ? "Pulsa 'Generar con IA' o escribe tu propio texto antes de publicar"
              : undefined
          }
          onClick={() => handlePublishChannelIndividual('linkedin')}
          className={`mt-2.5 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold shadow-xs transition ${
            drafts.linkedin.submitted
              ? 'cursor-not-allowed border border-emerald-200 bg-emerald-50 text-emerald-700'
              : 'bg-blue-600 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-blue-200'
          }`}
        >
          {drafts.linkedin.submitted ? (
            <>
              <CheckCircle size={14} className="text-emerald-600" />
              ✓ Publicado en LinkedIn
            </>
          ) : (
            <>
              <Send size={14} />
              {channelPublishing['linkedin'] ? 'Publicando...' : 'Publicar en LinkedIn'}
            </>
          )}
        </button>

        {/* Guardar en base de datos */}
        <button
          type="button"
          onClick={() => handleSubmit('linkedin')}
          disabled={
            drafts.linkedin.submitted ||
            drafts.linkedin.submitting ||
            drafts.linkedin.regenerating ||
            isOmittedByOrchestrator(drafts.linkedin.content)
          }
          className={`mt-2 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${
            drafts.linkedin.submitted
              ? 'cursor-not-allowed bg-green-50 text-green-700'
              : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
          }`}
        >
          {drafts.linkedin.submitted ? <CheckCircle size={14} /> : <FileText size={14} />}
          {drafts.linkedin.submitted ? 'Guardado en plataforma' : 'Guardar borrador'}
        </button>

        {drafts.linkedin.savedId && (
          <p className="mt-2 text-center text-xs font-medium text-green-700">
            Borrador #{drafts.linkedin.savedId} registrado exitosamente.
          </p>
        )}

        {channelPublishResult['linkedin'] && (
          <div
            className={`mt-2 text-center text-xs font-medium ${
              channelPublishResult['linkedin'].ok ? 'text-green-700' : 'text-rose-600'
            }`}
          >
            <p>{channelPublishResult['linkedin'].detalle}</p>
            {channelPublishResult['linkedin'].ok && (
              <a
                href={channelPublishResult['linkedin'].url || "https://www.linkedin.com/feed/"}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex items-center gap-1 font-semibold text-blue-600 underline hover:text-blue-800"
              >
                ↗ Ver publicación en LinkedIn
              </a>
            )}
          </div>
        )}
      </div>
    </section>
  )

  const renderXCard = () => (
    <section
      className={`flex flex-col rounded-2xl border bg-white shadow-sm transition ${
        activeFormat === 'x' ? 'border-orange-300 ring-2 ring-orange-50' : 'border-slate-200'
      }`}
    >
      <div className="border-b border-slate-100 p-3 sm:p-3.5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white">
              <MessageCircle size={16} />
            </div>
            <div className="min-w-0">
              <h3 className="text-xs font-bold text-slate-900 truncate">X (Twitter)</h3>
              <p className="text-[11px] text-slate-400 truncate">Microblogging conciso de alto impacto</p>
            </div>
          </div>

          <span
            className={`shrink-0 c-chip ${
              drafts.x.submitted
                ? 'c-chip--success'
                : isOmittedByOrchestrator(drafts.x.content)
                ? 'c-chip--warning'
                : 'c-chip--brand'
            }`}
          >
            {drafts.x.submitted
              ? '✓ Publicado'
              : isOmittedByOrchestrator(drafts.x.content)
              ? 'Omitido'
              : 'Borrador'}
          </span>
        </div>

        <div className="mt-2 flex items-center min-w-0">
          <span className="c-chip max-w-full truncate inline-flex items-center gap-1" title={modelosUtilizados.x}>
            <Cpu size={10} className="shrink-0" />
            <span className="truncate">{modelosUtilizados.x}</span>
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col p-3.5 space-y-2">
        <div>
          <label htmlFor="x-title" className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Título / Hook del Tweet
          </label>
          <input
            id="x-title"
            type="text"
            value={xTitle}
            disabled={drafts.x.submitted}
            onChange={(e) => setXTitle(e.target.value)}
            placeholder="Ej: ¿Sabías esto sobre nuestra comunidad? 👇"
            className="mt-1 w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-800 outline-none focus:border-slate-600 focus:ring-1 focus:ring-slate-100 disabled:bg-slate-50"
          />
        </div>

        <div>
          <label htmlFor="content-x" className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
            <Pencil size={11} />
            <span>Tweet editable</span>
          </label>
          <textarea
            id="content-x"
            value={drafts.x.content}
            disabled={drafts.x.submitted}
            onFocus={() => setActiveFormat('x')}
            onChange={(event) => updateContent('x', event.target.value)}
            placeholder="Tweet conciso..."
            className={`mt-1 w-full min-h-[140px] flex-1 resize-y rounded-lg border p-2.5 text-xs leading-relaxed outline-none transition disabled:bg-slate-50 disabled:text-slate-500 ${
              isOmittedByOrchestrator(drafts.x.content)
                ? 'border-amber-200 bg-amber-50/40 text-slate-700 italic'
                : 'border-slate-200 text-slate-700 focus:border-slate-600 focus:ring-1 focus:ring-slate-100'
            }`}
          />
        </div>

        {isOmittedByOrchestrator(drafts.x.content) && (
          <div className="mt-2.5 flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-xs text-amber-900">
            <div className="flex items-center gap-1.5">
              <Sparkles size={14} className="shrink-0 text-amber-600" />
              <span>¿Deseas redactar tweet para X de todos modos?</span>
            </div>
            <button
              type="button"
              disabled={drafts.x.regenerating}
              onClick={() => handleRegenerateChannelCopy('x')}
              className="flex items-center gap-1.5 rounded-md bg-amber-600 px-2.5 py-1 text-xs font-bold text-white shadow-xs transition hover:bg-amber-700 disabled:bg-amber-400"
            >
              <RotateCcw size={12} className={drafts.x.regenerating ? 'animate-spin' : ''} />
              {drafts.x.regenerating ? 'Generando...' : 'Regenerar con IA'}
            </button>
          </div>
        )}

        {/* Contador Dinámico de Caracteres Cromático */}
        {(() => {
          const fullXContent = (xTitle ? `${xTitle}\n\n` : '') + drafts.x.content
          const totalChars = [...fullXContent].length
          const isOverLimit = totalChars > 280
          const isWarning = totalChars > 210 && totalChars <= 280

          return (
            <div className="mt-3 flex items-center justify-between rounded-lg border p-2 text-xs transition"
              style={{
                backgroundColor: isOverLimit ? '#fef2f2' : isWarning ? '#fffbeb' : '#f0fdf4',
                borderColor: isOverLimit ? '#fecaca' : isWarning ? '#fde68a' : '#bbf7d0',
                color: isOverLimit ? '#b91c1c' : isWarning ? '#b45309' : '#15803d',
              }}
            >
              <span className="font-semibold text-[11px]">
                {isOverLimit
                  ? '⚠️ Excede el límite máximo de 280 caracteres'
                  : isWarning
                  ? '⚠️ Cerca del límite técnico de X'
                  : '✓ Longitud óptima para publicación'}
              </span>
              <span className={`font-mono font-bold ${isOverLimit ? 'text-rose-600' : ''}`}>
                {totalChars} / 280
              </span>
            </div>
          )
        })()}

        {/* Acciones auxiliares */}
        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleCopy('x')}
            className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
          >
            {copiedFormat === 'x' ? <CheckCircle size={14} /> : <Copy size={14} />}
            {copiedFormat === 'x' ? 'Copiado' : 'Copiar'}
          </button>

          <button
            type="button"
            disabled={drafts.x.submitted || drafts.x.regenerating}
            onClick={() => handleRegenerateChannelCopy('x')}
            className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-50"
          >
            <RotateCcw size={14} className={drafts.x.regenerating ? 'animate-spin' : ''} />
            {drafts.x.regenerating ? 'Regenerando...' : 'Regenerar'}
          </button>
        </div>

        {/* Publicar individual directo */}
        {(() => {
          const fullXContent = (xTitle ? `${xTitle}\n\n` : '') + drafts.x.content
          const isOverLimit = [...fullXContent].length > 280
          return (
            <button
              type="button"
              disabled={
                drafts.x.submitted ||
                channelPublishing['x'] ||
                !drafts.x.content.trim() ||
                isOverLimit ||
                isOmittedByOrchestrator(drafts.x.content)
              }
              title={
                drafts.x.submitted
                  ? 'Este tweet ya fue publicado exitosamente en X'
                  : isOmittedByOrchestrator(drafts.x.content)
                  ? "Pulsa 'Generar con IA' o escribe tu propio texto antes de publicar"
                  : undefined
              }
              onClick={() => handlePublishChannelIndividual('x')}
              className={`mt-2.5 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold shadow-xs transition ${
                drafts.x.submitted
                  ? 'cursor-not-allowed border border-emerald-200 bg-emerald-50 text-emerald-700'
                  : 'bg-slate-900 text-white hover:bg-black disabled:cursor-not-allowed disabled:bg-slate-400'
              }`}
            >
              {drafts.x.submitted ? (
                <>
                  <CheckCircle size={14} className="text-emerald-600" />
                  ✓ Publicado en X
                </>
              ) : (
                <>
                  <Send size={14} />
                  {channelPublishing['x'] ? 'Publicando...' : 'Publicar en X'}
                </>
              )}
            </button>
          )
        })()}

        {/* Guardar en base de datos */}
        <button
          type="button"
          onClick={() => handleSubmit('x')}
          disabled={
            drafts.x.submitted ||
            drafts.x.submitting ||
            drafts.x.regenerating ||
            [...(xTitle ? `${xTitle}\n\n` : '') + drafts.x.content].length > 280 ||
            isOmittedByOrchestrator(drafts.x.content)
          }
          className={`mt-2 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${
            drafts.x.submitted
              ? 'cursor-not-allowed bg-green-50 text-green-700'
              : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
          }`}
        >
          {drafts.x.submitted ? <CheckCircle size={14} /> : <FileText size={14} />}
          {drafts.x.submitted ? 'Guardado en plataforma' : 'Guardar borrador'}
        </button>

        {drafts.x.savedId && (
          <p className="mt-2 text-center text-xs font-medium text-green-700">
            Borrador #{drafts.x.savedId} registrado exitosamente.
          </p>
        )}

        {channelPublishResult['x'] && (
          <div
            className={`mt-2 text-center text-xs font-medium ${
              channelPublishResult['x'].ok ? 'text-green-700' : 'text-rose-600'
            }`}
          >
            <p>{channelPublishResult['x'].detalle}</p>
            {channelPublishResult['x'].ok && (
              <a
                href={channelPublishResult['x'].url || "https://x.com/CloudEdTech_1"}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-flex items-center gap-1 font-semibold text-blue-600 underline hover:text-blue-800"
              >
                ↗ Ver publicación en X
              </a>
            )}
          </div>
        )}
      </div>
    </section>
  )

  const renderDiscordCard = () => (
    <section
      className={`flex flex-col rounded-2xl border bg-white shadow-sm transition ${
        activeFormat === 'discord' ? 'border-orange-300 ring-2 ring-orange-50' : 'border-slate-200'
      }`}
    >
      <div className="border-b border-slate-100 p-3 sm:p-3.5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
              <MessageCircle size={16} />
            </div>
            <div className="min-w-0">
              <h3 className="text-xs font-bold text-slate-900 truncate">Discord</h3>
              <p className="text-[11px] text-slate-400 truncate">Publicación en hilos y canales de la comunidad</p>
            </div>
          </div>

          <span
            className={`shrink-0 c-chip ${
              drafts.discord.submitted
                ? 'c-chip--success'
                : isOmittedByOrchestrator(drafts.discord.content)
                ? 'c-chip--warning'
                : 'c-chip--brand'
            }`}
          >
            {drafts.discord.submitted
              ? '✓ Publicado'
              : isOmittedByOrchestrator(drafts.discord.content)
              ? 'Omitido'
              : 'Borrador'}
          </span>
        </div>

        <div className="mt-2 flex items-center min-w-0">
          <span className="c-chip c-chip--purple max-w-full truncate inline-flex items-center gap-1" title={modelosUtilizados.discord}>
            <Cpu size={10} className="shrink-0" />
            <span className="truncate">{modelosUtilizados.discord}</span>
          </span>
        </div>
      </div>

      <div className="flex flex-1 flex-col p-3.5 space-y-2">
        <div className="flex items-center justify-between gap-2">
          <label htmlFor="discord-channel-select" className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Canal de Destino
          </label>
          <select
            id="discord-channel-select"
            value={discordSelectedChannel}
            disabled={drafts.discord.submitted}
            onChange={(e) => setDiscordSelectedChannel(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-indigo-700 outline-none focus:border-indigo-500"
          >
            <option value="general">#general</option>
            <option value="faq">#faq</option>
            <option value="notificaciones">#notificaciones</option>
            <option value="pqrs">#pqrs</option>
            <option value="chat-egresados">#chat-egresados</option>
            <option value="oportunidades-laborales">#oportunidades-laborales</option>
          </select>
        </div>

        <div>
          <label htmlFor="discord-title" className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Título del Post
          </label>
          <input
            id="discord-title"
            type="text"
            value={discordTitle}
            disabled={drafts.discord.submitted}
            onChange={(e) => setDiscordTitle(e.target.value)}
            placeholder="Ej: [Comunidad] Debate abierto..."
            className="mt-1 w-full rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-800 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-100 disabled:bg-slate-50"
          />
        </div>

        <div>
          <label htmlFor="content-discord" className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-500">
            <Pencil size={11} />
            <span>Cuerpo del Post</span>
          </label>
          <textarea
            id="content-discord"
            value={drafts.discord.content}
            disabled={drafts.discord.submitted}
            onFocus={() => setActiveFormat('discord')}
            onChange={(event) => updateContent('discord', event.target.value)}
            placeholder="Mensaje para la comunidad..."
            className={`mt-1 w-full min-h-[140px] flex-1 resize-y rounded-lg border p-2.5 text-xs leading-relaxed outline-none transition disabled:bg-slate-50 disabled:text-slate-500 ${
              isOmittedByOrchestrator(drafts.discord.content)
                ? 'border-amber-200 bg-amber-50/40 text-slate-700 italic'
                : 'border-slate-200 text-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-50'
            }`}
          />
        </div>

        {isOmittedByOrchestrator(drafts.discord.content) && (
          <div className="mt-2.5 flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50/70 p-2.5 text-xs text-amber-900">
            <div className="flex items-center gap-1.5">
              <Sparkles size={14} className="shrink-0 text-amber-600" />
              <span>¿Deseas redactar mensaje para Discord de todos modos?</span>
            </div>
            <button
              type="button"
              disabled={drafts.discord.regenerating}
              onClick={() => handleRegenerateChannelCopy('discord')}
              className="flex items-center gap-1.5 rounded-md bg-amber-600 px-2.5 py-1 text-xs font-bold text-white shadow-xs transition hover:bg-amber-700 disabled:bg-amber-400"
            >
              <RotateCcw size={12} className={drafts.discord.regenerating ? 'animate-spin' : ''} />
              {drafts.discord.regenerating ? 'Generando...' : 'Regenerar con IA'}
            </button>
          </div>
        )}

        {/* Vista previa visual en vivo de la Cita en Bloque */}
        <div className="mt-3 rounded-xl border border-indigo-100 bg-indigo-50/60 p-3">
          <span className="text-[11px] font-bold text-indigo-800 uppercase tracking-wide">
            Vista previa de cita contextual (Discord Blockquote):
          </span>
          <div className="mt-1.5 rounded-lg border-l-4 border-indigo-500 bg-white p-2.5 text-xs text-slate-700 shadow-2xs">
            <p className="font-semibold text-indigo-600">
              💬 Contexto de @{selectedWorkflowMessage?.author || 'autor'}:
            </p>
            <blockquote className="mt-1 line-clamp-2 italic text-slate-600">
              "{selectedWorkflowMessage?.content || 'Selecciona un mensaje de la bandeja...'}"
            </blockquote>
          </div>
        </div>

        {/* Archivos adjuntos de Discord */}
        {discordFiles.length > 0 && (
          <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold text-slate-700">
                {discordFiles.length} archivo(s) adjunto(s)
              </p>
              <button
                type="button"
                onClick={() => setShowDiscordFiles((curr) => !curr)}
                className="text-xs font-semibold text-indigo-600 hover:underline"
              >
                {showDiscordFiles ? 'Ocultar' : 'Ver'}
              </button>
            </div>

            {showDiscordFiles && (
              <div className="mt-2 space-y-1.5">
                {discordFiles.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium text-slate-700">{file.filename}</p>
                      <p className="text-[10px] text-slate-400">
                        {file.content_type || 'Archivo'} · {formatDiscordFileSize(file.size)}
                      </p>
                    </div>
                    <a
                      href={file.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="shrink-0 text-orange-600 hover:underline"
                    >
                      Descargar
                    </a>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Acciones auxiliares */}
        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleCopy('discord')}
            className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
          >
            {copiedFormat === 'discord' ? <CheckCircle size={14} /> : <Copy size={14} />}
            {copiedFormat === 'discord' ? 'Copiado' : 'Copiar'}
          </button>

          <button
            type="button"
            disabled={drafts.discord.submitted || drafts.discord.regenerating}
            onClick={() => handleRegenerateChannelCopy('discord')}
            className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-50"
          >
            <RotateCcw size={14} className={drafts.discord.regenerating ? 'animate-spin' : ''} />
            {drafts.discord.regenerating ? 'Regenerando...' : 'Regenerar'}
          </button>
        </div>

        {/* Publicar individual directo */}
        <button
          type="button"
          disabled={
            drafts.discord.submitted ||
            channelPublishing['discord'] ||
            !drafts.discord.content.trim() ||
            isOmittedByOrchestrator(drafts.discord.content)
          }
          title={
            drafts.discord.submitted
              ? 'Este contenido ya fue publicado exitosamente en Discord'
              : isOmittedByOrchestrator(drafts.discord.content)
              ? "Pulsa 'Generar con IA' o escribe tu propio texto antes de publicar"
              : undefined
          }
          onClick={() => handlePublishChannelIndividual('discord')}
          className={`mt-2.5 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold shadow-xs transition ${
            drafts.discord.submitted
              ? 'cursor-not-allowed border border-emerald-200 bg-emerald-50 text-emerald-700'
              : 'bg-indigo-600 text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-200'
          }`}
        >
          {drafts.discord.submitted ? (
            <>
              <CheckCircle size={14} className="text-emerald-600" />
              ✓ Publicado en Discord
            </>
          ) : (
            <>
              <Send size={14} />
              {channelPublishing['discord'] ? 'Publicando...' : 'Publicar en Discord'}
            </>
          )}
        </button>

        {/* Guardar en base de datos */}
        <button
          type="button"
          onClick={() => handleSubmit('discord')}
          disabled={
            drafts.discord.submitted ||
            drafts.discord.submitting ||
            drafts.discord.regenerating ||
            isOmittedByOrchestrator(drafts.discord.content)
          }
          className={`mt-2 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${
            drafts.discord.submitted
              ? 'cursor-not-allowed bg-green-50 text-green-700'
              : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
          }`}
        >
          {drafts.discord.submitted ? <CheckCircle size={14} /> : <FileText size={14} />}
          {drafts.discord.submitted ? 'Guardado en plataforma' : 'Guardar borrador'}
        </button>

        {drafts.discord.savedId && (
          <p className="mt-2 text-center text-xs font-medium text-green-700">
            Borrador #{drafts.discord.savedId} registrado exitosamente.
          </p>
        )}

        {channelPublishResult['discord'] && (
          <p
            className={`mt-2 text-center text-xs font-medium ${
              channelPublishResult['discord'].ok ? 'text-green-700' : 'text-rose-600'
            }`}
          >
            {channelPublishResult['discord'].detalle}
          </p>
        )}
      </div>
    </section>
  )

  const renderHitlBar = () => (
    <section className="rounded-2xl border border-indigo-200 bg-gradient-to-r from-indigo-50/60 via-white to-purple-50/60 p-4 shadow-sm">
      <div className="c-panel-head c-panel-head--flat">
        <div className="c-panel-head__main">
          <div className="c-panel-head__icon bg-indigo-100 text-indigo-700">
            <CheckCircle size={16} />
          </div>

          <div className="c-panel-head__body">
            <div className="c-panel-head__row">
              <h4 className="c-panel-head__title">
                Decisión Humana Global HITL (Human-in-the-Loop)
              </h4>
              <span className="c-chip c-chip--info">
                Revisión: {pipelineData?.estado_revision || 'pendiente_hitl'}
              </span>
            </div>
            <p className="c-panel-head__desc">
              Soberanía humana completa: Tus modificaciones manuales en los títulos y copys tienen prevalencia estricta sobre las sugerencias de la IA.
            </p>
          </div>
        </div>

        <div className="c-panel-head__actions">
          <button
            type="button"
            disabled={pipelineExecuting || !selectedWorkflowMessage}
            onClick={() => handleSubmitHitlDecision(false)}
            className="flex items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-3 py-1.5 text-xs font-bold text-rose-600 shadow-xs transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <XCircle size={13} />
            <span>Desaprobar y limpiar hilo</span>
          </button>

          <button
            type="button"
            disabled={pipelineExecuting || !selectedWorkflowMessage}
            onClick={() => handleSubmitHitlDecision(true)}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-xs transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <CheckCircle size={13} />
            <span>Aprobar y publicar en canales (HITL)</span>
          </button>
        </div>
      </div>

      {pipelineActionMessage && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800">
          <CheckCircle size={16} className="shrink-0 text-emerald-600" />
          <span>{pipelineActionMessage}</span>
        </div>
      )}

      {pipelineActionError && (
        <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs font-semibold text-rose-800">
          <AlertTriangle size={16} className="shrink-0 text-rose-600" />
          <span>{pipelineActionError}</span>
        </div>
      )}
    </section>
  )

  return (
    <div>
      {/* Encabezado */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="t-page t-page--xl text-3xl font-bold tracking-tight text-slate-900">
            Redacción de Contenidos
          </h1>

          <p className="mt-1 text-sm text-slate-500">
            Convierte conversaciones de Discord en contenido adaptado para diferentes canales
          </p>
        </div>

        <div
          className="c-live rounded-full border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs font-semibold text-emerald-700"
          role="status"
        >
          <span className="c-live__dot" aria-hidden="true" />
          <span>Webhook Discord conectado</span>
        </div>
      </div>

      {/* Selector de pestañas (Design System de Cristian) */}
      <div className="c-tabs mt-6" role="tablist" aria-label="Secciones de Redacción" style={{ marginBottom: '1.5rem' }}>
        <button
          type="button"
          role="tab"
          id="tab-btn-inbox"
          aria-selected={activeContentTab === 'inbox'}
          aria-controls="panel-inbox"
          onClick={() => setActiveContentTab('inbox')}
          className={`c-tab ${activeContentTab === 'inbox' ? 'is-active' : ''}`}
        >
          Bandeja
          <span className="c-tab__count">{workflowMessages.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          id="tab-btn-announcements"
          aria-selected={activeContentTab === 'announcements'}
          aria-controls="panel-announcements"
          onClick={() => setActiveContentTab('announcements')}
          className={`c-tab ${activeContentTab === 'announcements' ? 'is-active' : ''}`}
        >
          Anuncios oficiales
        </button>
        <button
          type="button"
          role="tab"
          id="tab-btn-complaints"
          aria-selected={activeContentTab === 'complaints'}
          aria-controls="panel-quejas"
          onClick={() => setActiveContentTab('complaints')}
          className={`c-tab ${activeContentTab === 'complaints' ? 'is-active' : ''}`}
        >
          Quejas y soporte
          <span className="c-tab__count">{complaints.length}</span>
        </button>
      </div>

      {/* PESTAÑA: ANUNCIOS OFICIALES */}
      <div
        id="panel-announcements"
        role="tabpanel"
        aria-labelledby="tab-btn-announcements"
        className={activeContentTab === 'announcements' ? 'space-y-6' : 'hidden'}
      >
        {/* Panel de Anuncios Oficiales de la Comunidad (Discord Webhook) */}
        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          {/* Cabecera compacta del Panel (CommunityLab Design System) */}
          <div className="c-panel-head">
            <div className="c-panel-head__main">
              <div className="c-panel-head__icon bg-orange-100 text-orange-600">
                <Megaphone size={16} />
              </div>

              <div className="c-panel-head__body">
                <div className="c-panel-head__row">
                  <h3 className="c-panel-head__title">
                    Panel de Anuncios Oficiales de la Comunidad (Discord Webhook)
                  </h3>

                  <span className="c-chip c-chip--info">
                    #{announcementStatus?.channel_hint || 'anuncios'}
                  </span>

                  <span className="c-chip c-chip--purple">
                    <Cpu size={11} />
                    <span>
                      🤖 Modelo IA: {selectedAnnouncementModel === 'groq' ? 'Groq · llama-3.3-70b-versatile' : selectedAnnouncementModel === 'gemma' ? 'Google Gemma 4 · gemma-4-31b-it' : 'Google Gemini · gemini-2.5-flash-lite'}
                    </span>
                  </span>
                </div>

                <p className="c-panel-head__desc">
                  Redacta comunicados oficiales, optimízalos con IA o carga archivos .txt/.md y publícalos directamente vía Webhook.
                </p>
              </div>
            </div>

            <div className="c-panel-head__actions">
              {announcementStatusLoading ? (
                <span className="text-xs text-slate-400">Consultando webhook...</span>
              ) : announcementStatus?.configured ? (
                <span className="c-chip c-chip--success">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  <span>Webhook configurado</span>
                </span>
              ) : (
                <span className="c-chip c-chip--warning">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  <span>Webhook no configurado</span>
                </span>
              )}
            </div>
          </div>

        {/* Alerta ámbar si configured === false */}
        {!announcementStatusLoading && announcementStatus && !announcementStatus.configured && (
          <div
            role="alert"
            className="mt-4 flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900"
          >
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div>
              <p className="font-semibold">
                ⚠️ Webhook de Discord no configurado en el servidor (DISCORD_WEBHOOK_ANUNCIOS)
              </p>
              <p className="mt-0.5 text-xs text-amber-800">
                {announcementStatus.warning || 'La publicación directa a Discord está bloqueada preventivamente hasta que se configure la variable de entorno.'}
              </p>
            </div>
          </div>
        )}

        {/* Notificación de éxito o error en publicación */}
        {announcementPublishSuccess && (
          <div
            role="status"
            className="mt-4 flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"
          >
            <div className="flex items-center gap-2">
              <CheckCircle size={18} className="shrink-0 text-emerald-600" />
              <span>{announcementPublishSuccess}</span>
            </div>
            <button
              type="button"
              onClick={() => setAnnouncementPublishSuccess('')}
              className="text-xs font-semibold text-emerald-700 hover:underline"
            >
              Cerrar
            </button>
          </div>
        )}

        {announcementPublishError && (
          <div
            role="alert"
            className="mt-4 flex items-center justify-between rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          >
            <span>{announcementPublishError}</span>
            <button
              type="button"
              onClick={() => setAnnouncementPublishError('')}
              className="text-xs font-semibold text-rose-700 hover:underline"
            >
              Cerrar
            </button>
          </div>
        )}

        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Descripción del anuncio para generar con IA */}
          <div className="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-slate-50/50 p-3.5 sm:p-4">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label
                  htmlFor="announcement-draft"
                  className="text-[11px] font-bold uppercase tracking-wider text-slate-700"
                >
                  Descripción del anuncio para generar con IA
                </label>

                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-slate-500">IA:</span>
                  <select
                    value={selectedAnnouncementModel}
                    onChange={(e) => setSelectedAnnouncementModel(e.target.value)}
                    className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700 outline-none transition focus:border-orange-500"
                  >
                    <option value="gemini">Google Gemini Flash Lite</option>
                    <option value="groq">Groq (Cerebro IA)</option>
                    <option value="gemma">Google Gemma 4</option>
                  </select>

                  <span
                    className={`text-[11px] font-semibold tabular-nums ${
                      draftText.length > 10000 ? 'font-bold text-rose-600' : 'text-slate-500'
                    }`}
                  >
                    {draftText.length.toLocaleString()} / 10,000
                  </span>
                </div>
              </div>

            {selectedAnnouncementModel === 'gemma' && (
              <div className="mt-2.5 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50/90 px-3 py-2 text-[11px] text-amber-800">
                <span className="text-base shrink-0">⏳</span>
                <span>
                  <strong>Google Gemma 4 (31B)</strong> es un modelo denso de alta precisión; puede tardar entre <strong>30 y 60 segundos</strong>. Si deseas respuesta inmediata en 1-2 segundos, selecciona <strong>Google Gemini Flash Lite</strong> o <strong>Groq</strong>.
                </span>
              </div>
            )}

            <textarea
              id="announcement-draft"
              value={draftText}
              onChange={(e) => {
                setDraftText(e.target.value)
                setAnnouncementGenerateError('')
              }}
              placeholder="Escribe aquí los puntos clave, fecha, temática o instrucciones para el anuncio. La IA generará automáticamente el texto del anuncio en el editor final siguiendo el manual de marca CloudEdTech..."
              rows={6}
              className="mt-2.5 w-full min-h-[140px] flex-1 resize-y rounded-lg border border-slate-200 bg-white p-2.5 text-xs leading-relaxed text-slate-700 outline-none transition focus:border-orange-500 focus:ring-1 focus:ring-orange-200"
            />
            </div>

            {draftText.length > 10000 && (
              <p className="mt-1.5 text-xs font-medium text-rose-600">
                La descripción excede el límite máximo de 10,000 caracteres permitidos.
              </p>
            )}

            {announcementGenerateError && (
              <div
                role="alert"
                className="mt-2.5 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700"
              >
                {announcementGenerateError}
              </div>
            )}

            {isGeneratingAnnouncement && (
              <div className="mt-3 flex items-start gap-2.5 rounded-lg border border-indigo-200 bg-indigo-50/90 p-3 text-xs text-indigo-950 shadow-xs">
                <RotateCcw size={15} className="mt-0.5 shrink-0 animate-spin text-indigo-600" />
                <div>
                  <p className="font-bold text-indigo-900">
                    {selectedAnnouncementModel === 'gemma'
                      ? 'Generando anuncio con Google Gemma 4...'
                      : selectedAnnouncementModel === 'groq'
                      ? 'Generando anuncio con Groq...'
                      : 'Generando anuncio con Google Gemini...'}
                  </p>
                  <p className="mt-0.5 text-[11px] leading-relaxed text-indigo-700">
                    {selectedAnnouncementModel === 'gemma'
                      ? 'Gemma 4 puede demorar entre 30 y 60 segundos por su arquitectura de 31B parámetros. Para redacción instantánea en 1-2s, puedes elegir Gemini Flash o Groq.'
                      : 'Redactando el anuncio con las directivas del manual de marca CloudEdTech y formato optimizado para Discord.'}
                  </p>
                </div>
              </div>
            )}

            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/60 pt-2.5">
              <div>
                {draftText && (
                  <button
                    type="button"
                    onClick={() => {
                      setDraftText('')
                      setAnnouncementGenerateError('')
                    }}
                    className="text-[11px] font-medium text-slate-400 transition hover:text-slate-600"
                  >
                    Limpiar
                  </button>
                )}
              </div>

              <button
                type="button"
                disabled={
                  isGeneratingAnnouncement ||
                  !draftText.trim() ||
                  draftText.length > 10000
                }
                onClick={handleGenerateAnnouncement}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-brand,#ff7400)] px-3.5 py-1.5 text-xs font-bold text-white shadow-xs transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-200"
              >
                {isGeneratingAnnouncement ? (
                  <RotateCcw size={13} className="animate-spin" />
                ) : (
                  <Sparkles size={13} />
                )}
                <span>{isGeneratingAnnouncement ? 'Generando...' : 'Generar anuncio con IA'}</span>
              </button>
            </div>
          </div>

          {/* Editor de Anuncio Final y Semáforo de Caracteres */}
          <div className="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-slate-50/50 p-3.5 sm:p-4">
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label
                  htmlFor="announcement-final"
                  className="text-[11px] font-bold uppercase tracking-wider text-slate-700"
                >
                  Editor de Anuncio Final
                </label>

                {/* Contador de caracteres */}
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-bold tabular-nums text-slate-700">
                    {finalAnnouncement.length} / 2000
                  </span>
                </div>
              </div>

            <textarea
              id="announcement-final"
              value={finalAnnouncement}
              onChange={(e) => {
                setFinalAnnouncement(e.target.value)
                setAnnouncementPublishError('')
                setAnnouncementPublishSuccess('')
              }}
              placeholder="El anuncio generado aparecerá aquí para revisión final, o puedes redactarlo / cargar un archivo .txt/.md directamente..."
              rows={6}
              className="mt-2.5 w-full min-h-[140px] flex-1 resize-y rounded-lg border border-slate-200 bg-white p-2.5 text-xs leading-relaxed text-slate-700 outline-none transition focus:border-orange-500 focus:ring-1 focus:ring-orange-200"
            />

            {/* Barra de progreso cromática */}
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className={`h-full transition-all duration-300 ${
                  finalAnnouncement.length <= 1500
                    ? 'bg-emerald-500'
                    : finalAnnouncement.length <= 2000
                    ? 'bg-amber-500'
                    : 'bg-rose-500'
                }`}
                style={{
                  width: `${Math.min(100, (finalAnnouncement.length / 2000) * 100)}%`,
                }}
              />
            </div>

            </div>
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-200/60 pt-2.5">
              {/* Botón de carga de archivo */}
              <div className="flex items-center gap-1.5">
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".txt,.md"
                  className="hidden"
                  onChange={handleFileUpload}
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 shadow-xs transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <Upload size={13} />
                  <span>.txt / .md</span>
                </button>

                {finalAnnouncement && (
                  <button
                    type="button"
                    onClick={() => {
                      setFinalAnnouncement('')
                      setAnnouncementPublishError('')
                      setAnnouncementPublishSuccess('')
                    }}
                    className="text-[11px] font-medium text-slate-400 transition hover:text-slate-600"
                  >
                    Limpiar
                  </button>
                )}
              </div>

              {/* Selector de Canal y Botón Publicar */}
              <div className="flex flex-wrap items-center gap-1.5">
                <div className="flex items-center gap-1">
                  <label htmlFor="announcement-channel" className="text-[11px] font-semibold text-slate-500">
                    Canal:
                  </label>
                  <select
                    id="announcement-channel"
                    value={selectedDiscordChannel}
                    onChange={(e) => setSelectedDiscordChannel(e.target.value)}
                    className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700 outline-none transition focus:border-orange-500"
                  >
                    {availableDiscordChannels.map((ch) => (
                      <option key={ch.id} value={ch.id}>
                        {ch.name}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  disabled={
                    !finalAnnouncement.trim() ||
                    finalAnnouncement.length > 2000 ||
                    !announcementStatus?.configured ||
                    isPublishingAnnouncement
                  }
                  onClick={() => setShowConfirmModal(true)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-brand,#ff7400)] px-3.5 py-1.5 text-xs font-bold text-white shadow-xs transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-200"
                >
                  <Send size={13} />
                  <span>Publicar en Discord</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Vista Previa en vivo estilo Discord Embed (Spec 019 RF-09) */}
        <div className="mt-3.5 rounded-xl border border-slate-200/90 bg-slate-50/40 p-3 sm:p-3.5">
          <div className="mb-2.5 flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-bold uppercase tracking-wide text-slate-700">
              Vista previa en vivo · Discord Embed
            </span>
            <span className="rounded-md bg-indigo-50 px-2.5 py-0.5 font-mono text-[11px] font-semibold tabular-nums text-indigo-700">
              Canal destino: {selectedTargetChannelName}
            </span>
          </div>

          <div className="discord-embed">
            <div className="discord-embed__header discord-embed__bot">
              <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#080a27] text-[10px] font-black text-white">
                CE
              </span>
              <span className="text-xs font-bold text-slate-900">
                CloudEdTech_Oficial
              </span>
              <span className="discord-embed__pill">BOT</span>
              <span className="text-[11px] font-normal tabular-nums text-slate-400">
                Hoy · {selectedTargetChannelName}
              </span>
            </div>

            <div className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
              {announcementDraft ? (
                announcementDraft
              ) : (
                <span className="italic text-slate-400">
                  Escribe o genera con IA el anuncio oficial para visualizar cómo se verá en el canal #anuncios de Discord...
                </span>
              )}
            </div>
          </div>
        </div>
      </section>
      </div>

      {/* PESTAÑA: BANDEJA Y MESA DE TRABAJO */}
      <div
        id="panel-inbox"
        role="tabpanel"
        aria-labelledby="tab-btn-inbox"
        className={activeContentTab === 'inbox' ? 'space-y-5' : 'hidden'}
      >
        {/* Layout 2 Columnas estilo Cristian (l-grid--side-main): Bandeja a la izquierda, Mesa de trabajo a la derecha */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12 items-start">
          {/* Columna Izquierda: Bandeja de mensajes y Control de flujo editorial */}
          <div className="lg:col-span-4 xl:col-span-4 space-y-4">
            {/* Bandeja de mensajes listos para redacción (Selector de cola) */}
            <section className="flex flex-col rounded-2xl border border-slate-200 bg-white p-4 sm:p-4.5 shadow-sm">
              <div className="c-panel-head mb-3">
                <div className="c-panel-head__main">
                  <div className="c-panel-head__body">
                    <div className="c-panel-head__row">
                      <h3 className="c-panel-head__title">
                        Bandeja de mensajes en Redacción
                      </h3>
                    </div>
                    <p className="c-panel-head__desc">
                      Selecciona un mensaje para revisarlo
                    </p>
                  </div>
                </div>

                {/* Buscador y Carga directa por ID específico (Estilo Enoc / HITL) */}
                <div className="c-panel-head__actions">
                  <form
                    onSubmit={handleSearchById}
                    className="mt-2.5 flex flex-col gap-1 border-b border-slate-100 pb-2.5"
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="1"
                        placeholder="ID ej: 42"
                        value={manualIdInput}
                        onChange={(e) => {
                          const nextVal = e.target.value
                          setManualIdInput(nextVal)
                          setManualIdError(null)
                          if (pinnedSearchMessage !== null) {
                            const pinnedId = pinnedSearchMessage.interactionId
                            setPinnedSearchMessage(null)
                            if (
                              selectedMessageId === pinnedId ||
                              activeWorkbenchMessage?.interactionId === pinnedId
                            ) {
                              const firstNatural = workflowMessages[0] ?? null
                              setSelectedMessageId(firstNatural?.interactionId ?? null)
                              setActiveWorkbenchMessage(firstNatural)
                              setDrafts(buildDefaultDrafts(firstNatural))
                            }
                          }
                        }}
                        className="w-full flex-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold tabular-nums text-slate-800 placeholder-slate-400 transition focus:border-orange-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-orange-500"
                      />
                      <button
                        type="submit"
                        disabled={!manualIdInput.trim() || workflowLoading}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-orange-600 px-3 py-1 text-xs font-semibold text-white shadow-xs transition hover:bg-orange-700 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <Search size={12} />
                        <span>Cargar ID</span>
                      </button>
                    </div>
                    {manualIdError && (
                      <span className="text-[10px] font-medium text-rose-600">
                        {manualIdError}
                      </span>
                    )}
                  </form>
                </div>
              </div>

              {workflowLoading && (
                <p className="py-4 text-xs text-slate-500">Cargando mensajes disponibles...</p>
              )}

              {workflowError && (
                <p role="alert" className="py-4 text-xs text-rose-600">
                  {workflowError}
                </p>
              )}

              {!workflowLoading && !workflowError && displayedTrayMessages.length === 0 && (
                <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center">
                  <p className="text-xs text-slate-500">
                    No hay mensajes pendientes de redacción en este momento.
                  </p>
                </div>
              )}

              {!workflowLoading && !workflowError && displayedTrayMessages.length > 0 && (
                <div className="mt-3 space-y-2.5 max-h-[460px] overflow-y-auto pr-1 scrollbar-thin">
                  {displayedTrayMessages.map((item) => {
                    const isActive = selectedWorkflowId === item.interactionId
                    const isPinnedById =
                      pinnedSearchMessage !== null &&
                      pinnedSearchMessage.interactionId === item.interactionId &&
                      !workflowMessages.some(
                        (m) => m.interactionId === item.interactionId,
                      )

                    return (
                      <button
                        key={item.interactionId}
                        id={`tray-card-${item.interactionId}`}
                        ref={(el) => {
                          trayCardRefs.current[item.interactionId] = el
                        }}
                        type="button"
                        onClick={() => {
                          setSelectedWorkflowId(item.interactionId)
                          prepareWorkflowContent(item)
                        }}
                        className={`w-full rounded-xl border p-3 text-left transition ${
                          isActive
                            ? 'c-tray-card--active border-orange-500 bg-orange-50/70 shadow-xs ring-1 ring-orange-400'
                            : 'border-slate-200 bg-white hover:border-orange-300 hover:bg-slate-50/60'
                        }`}
                      >
                        {isPinnedById && (
                          <div className="mb-2 flex items-center justify-between rounded-lg border border-orange-200 bg-orange-100/80 px-2.5 py-1 text-[10px] font-bold text-orange-800">
                            <span className="tabular-nums">
                              📌 Cargado por ID #{item.interactionId}
                            </span>
                            <span className="text-[9px] font-semibold uppercase tracking-wide text-orange-600">
                              Temporal
                            </span>
                          </div>
                        )}

                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-xs font-bold text-slate-900">
                            @{item.author}
                          </span>
                          <span className="tabular-nums shrink-0 rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-bold text-orange-700">
                            {item.relevance}% rel.
                          </span>
                        </div>

                        <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-500">
                          <span className="font-medium text-indigo-600">#{item.channel}</span>
                          <span>•</span>
                          <span className="truncate text-slate-600">{item.topic}</span>
                        </div>

                        <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-slate-600">
                          "{item.content}"
                        </p>

                        <div className="mt-2 flex items-center justify-between border-t border-slate-100 pt-1.5 text-[11px]">
                          <span
                            className={`font-semibold ${
                              isActive ? 'text-orange-600' : 'text-slate-400'
                            }`}
                          >
                            {isActive ? '● En mesa de trabajo' : 'Click para cargar'}
                          </span>
                          <span className="tabular-nums text-[10px] text-slate-400">
                            ID #{item.interactionId}
                          </span>
                        </div>
                      </button>
                    )
                  })}
                </div>
              )}
            </section>

          </div>

          {/* Columna Derecha: Mesa de Trabajo Multicanal (Orquestador LangGraph) unificada con Mensaje Original de Discord */}
          <div className="lg:col-span-8 xl:col-span-8 space-y-4">
            {/* Tarjeta Fusionada: Mesa de Trabajo Multicanal (Orquestador LangGraph) */}
            <section
              ref={originalMessageRef}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="c-panel-head">
                <div className="c-panel-head__main">
                  <div className="c-panel-head__body">
                    <div className="c-panel-head__row">
                      <h3 className="c-panel-head__title">
                        Mesa de Trabajo Multicanal (Orquestador LangGraph)
                      </h3>

                      {isCurrentlyPublished && (
                        <span className="c-chip c-chip--success">
                          <CheckCircle size={11} className="text-emerald-600" />
                          <span>✓ Publicado en: {publishedPlatformNames.join(', ')}</span>
                        </span>
                      )}

                      <span className="c-chip c-chip--info">
                        <Cpu size={11} />
                        <span>🤖 Orquestador IA: {modelosUtilizados.orquestador}</span>
                      </span>

                      {pipelineData?.rutas_activas && (
                        <span className="c-chip c-chip--success">
                          Rutas: {pipelineData.rutas_activas.join(', ')}
                        </span>
                      )}
                    </div>

                    <p className="c-panel-head__desc">
                      Mensaje seleccionado para generación de contenido y orquestación adaptativa multicanal.
                    </p>
                  </div>
                </div>

                <div className="c-panel-head__actions flex-wrap gap-2">
                  <div className="flex items-center gap-1.5">
                    <label
                      htmlFor="workspace-ai-provider"
                      className="text-xs font-semibold text-slate-600"
                    >
                      Fallback IA:
                    </label>
                    <select
                      id="workspace-ai-provider"
                      value={workspaceAiProvider}
                      disabled={Object.values(drafts).some((d) => d.regenerating)}
                      onChange={(event) => setWorkspaceAiProvider(event.target.value)}
                      className="rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 outline-none focus:border-orange-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                    >
                      {AI_PROVIDERS.map((provider) => (
                        <option key={provider} value={provider}>
                          {provider}
                        </option>
                      ))}
                    </select>
                  </div>

                  <button
                    type="button"
                    disabled={!selectedWorkflowMessage}
                    onClick={() => setWorkspaceModalChannel('all')}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 shadow-2xs transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                    title="Abrir editor manual con los 3 canales en paralelo"
                  >
                    <Pencil size={13} className="text-slate-600" />
                    <span>✏️ Editar manualmente</span>
                  </button>

                  <button
                    type="button"
                    disabled={pipelineExecuting || !selectedWorkflowMessage}
                    onClick={handleExecuteMototradisPipeline}
                    className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-xs transition hover:from-indigo-700 hover:to-purple-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <RotateCcw size={13} className={pipelineExecuting ? 'animate-spin' : ''} />
                    <span>{pipelineExecuting ? 'Ejecutando LangGraph...' : '⚡ Ejecutar Pipeline (LangGraph)'}</span>
                  </button>
                </div>
              </div>

              {pipelineLoading && (
                <p className="mt-3 text-xs text-indigo-600">Sincronizando checkpoint del orquestador...</p>
              )}

              {/* Mensaje original de Discord seleccionado */}
              {selectedWorkflowMessage ? (
                <div className="mt-4 rounded-2xl border border-slate-200/90 bg-white p-4 sm:p-4.5 shadow-xs">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-2.5">
                      <span className="c-avatar c-avatar--indigo h-8 w-8 text-xs font-bold shrink-0">
                        {(selectedWorkflowMessage.author || 'U').slice(0, 2).toUpperCase()}
                      </span>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold text-slate-900">
                            @{selectedWorkflowMessage.author}
                          </span>
                          <span className="c-tag c-tag--channel text-[10px]">
                            #{selectedWorkflowMessage.channel.replace(/^#/, '')}
                          </span>
                          <span className="text-[11px] font-medium text-slate-400 tabular-nums">
                            ID #{selectedWorkflowMessage.interactionId}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Tema: <span className="font-semibold text-slate-700">{selectedWorkflowMessage.topic || 'General'}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-center tabular-nums">
                      <span
                        className={`c-pill c-pill--dot ${
                          selectedWorkflowMessage.sentiment === 'positive'
                            ? 'c-pill--success'
                            : selectedWorkflowMessage.sentiment === 'negative'
                            ? 'c-pill--danger'
                            : ''
                        }`}
                      >
                        {selectedWorkflowMessage.sentiment === 'positive'
                          ? 'Positivo'
                          : selectedWorkflowMessage.sentiment === 'negative'
                          ? 'Negativo'
                          : 'Neutral'}
                      </span>

                      <div
                        className="score-ring score-ring--sm"
                        style={{ '--p': selectedWorkflowMessage.relevance } as React.CSSProperties}
                        title={`Relevancia IA: ${selectedWorkflowMessage.relevance}%`}
                      >
                        <span>{selectedWorkflowMessage.relevance}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3">
                    <p className="text-xs sm:text-sm leading-relaxed text-slate-800 font-normal">
                      {selectedWorkflowMessage.content}
                    </p>
                  </div>

                  {selectedWorkflowMessage.attachments && selectedWorkflowMessage.attachments.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-2.5">
                      {selectedWorkflowMessage.attachments.map((att) => (
                        <a
                          key={att.id || att.url}
                          href={att.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100"
                        >
                          📎 {att.filename}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50/50 p-6 text-center">
                  <p className="text-xs text-slate-500">
                    Selecciona una conversación de la bandeja para cargar su contenido en la mesa de trabajo.
                  </p>
                </div>
              )}

              {pipelineActionMessage && (
                <div className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-xs font-semibold text-emerald-800">
                  <CheckCircle size={16} className="shrink-0 text-emerald-600" />
                  <span>{pipelineActionMessage}</span>
                </div>
              )}

              {pipelineActionError && (
                <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs font-semibold text-rose-800">
                  <AlertTriangle size={16} className="shrink-0 text-rose-600" />
                  <span>{pipelineActionError}</span>
                </div>
              )}
            </section>

            {/* Lanzadores de Redes Sociales: LinkedIn, X (Twitter) y Discord */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              {/* Botón / Tarjeta Lanzadora: LinkedIn */}
              <div className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-xs transition hover:border-blue-300 hover:shadow-sm">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                        <BriefcaseBusiness size={16} />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-900">LinkedIn</h4>
                        <p className="text-[10px] text-slate-400">Networking profesional</p>
                      </div>
                    </div>
                    <span
                      className={`shrink-0 c-chip ${
                        drafts.linkedin.submitted
                          ? 'c-chip--success'
                          : isOmittedByOrchestrator(drafts.linkedin.content)
                          ? 'c-chip--warning'
                          : drafts.linkedin.content.trim()
                          ? 'c-chip--brand'
                          : ''
                      }`}
                    >
                      {drafts.linkedin.submitted
                        ? '✓ Publicado'
                        : isOmittedByOrchestrator(drafts.linkedin.content)
                        ? 'Omitido'
                        : drafts.linkedin.content.trim()
                        ? 'Borrador'
                        : 'Pendiente'}
                    </span>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                    <span className="truncate">
                      {drafts.linkedin.content.trim() ? `${drafts.linkedin.content.length} caracteres` : 'Sin borrador aún'}
                    </span>
                    <span className="truncate font-medium text-slate-400">
                      {modelosUtilizados.linkedin.split(' ')[0]}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setWorkspaceModalChannel('linkedin')}
                  className="mt-3.5 flex w-full items-center justify-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50/70 px-3 py-2 text-xs font-bold text-blue-700 shadow-2xs transition hover:bg-blue-100"
                >
                  <Pencil size={13} />
                  <span>Abrir editor LinkedIn</span>
                </button>
              </div>

              {/* Botón / Tarjeta Lanzadora: X (Twitter) */}
              <div className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-xs transition hover:border-slate-400 hover:shadow-sm">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-900 text-white">
                        <MessageCircle size={16} />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-900">X (Twitter)</h4>
                        <p className="text-[10px] text-slate-400">Microblogging sintético</p>
                      </div>
                    </div>
                    <span
                      className={`shrink-0 c-chip ${
                        drafts.x.submitted
                          ? 'c-chip--success'
                          : isOmittedByOrchestrator(drafts.x.content)
                          ? 'c-chip--warning'
                          : drafts.x.content.trim()
                          ? 'c-chip--brand'
                          : ''
                      }`}
                    >
                      {drafts.x.submitted
                        ? '✓ Publicado'
                        : isOmittedByOrchestrator(drafts.x.content)
                        ? 'Omitido'
                        : drafts.x.content.trim()
                        ? 'Borrador'
                        : 'Pendiente'}
                    </span>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                    <span className="tabular-nums">
                      {drafts.x.content.trim() ? `${drafts.x.content.length}/280 caracteres` : 'Sin borrador aún'}
                    </span>
                    <span className="truncate font-medium text-slate-400">
                      {modelosUtilizados.x.split(' ')[0]}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setWorkspaceModalChannel('x')}
                  className="mt-3.5 flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-800 shadow-2xs transition hover:bg-slate-100"
                >
                  <Pencil size={13} />
                  <span>Abrir editor X</span>
                </button>
              </div>

              {/* Botón / Tarjeta Lanzadora: Discord */}
              <div className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-4 shadow-xs transition hover:border-indigo-300 hover:shadow-sm">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                        <MessageCircle size={16} />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-900">Discord</h4>
                        <p className="text-[10px] text-slate-400">Comunidad y soporte</p>
                      </div>
                    </div>
                    <span
                      className={`shrink-0 c-chip ${
                        drafts.discord.submitted
                          ? 'c-chip--success'
                          : isOmittedByOrchestrator(drafts.discord.content)
                          ? 'c-chip--warning'
                          : drafts.discord.content.trim()
                          ? 'c-chip--brand'
                          : ''
                      }`}
                    >
                      {drafts.discord.submitted
                        ? '✓ Publicado'
                        : isOmittedByOrchestrator(drafts.discord.content)
                        ? 'Omitido'
                        : drafts.discord.content.trim()
                        ? 'Borrador'
                        : 'Pendiente'}
                    </span>
                  </div>

                  <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                    <span className="tabular-nums">
                      {drafts.discord.content.trim() ? `${drafts.discord.content.length}/2000 caracteres` : 'Sin borrador aún'}
                    </span>
                    <span className="truncate font-medium text-slate-400">
                      {modelosUtilizados.discord.split(' ')[0]}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setWorkspaceModalChannel('discord')}
                  className="mt-3.5 flex w-full items-center justify-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50/70 px-3 py-2 text-xs font-bold text-indigo-700 shadow-2xs transition hover:bg-indigo-100"
                >
                  <Pencil size={13} />
                  <span>Abrir editor Discord</span>
                </button>
              </div>
            </div>

            {/* Procesamiento Masivo con Gemma 4 para Baja Relevancia (< 35) (CommunityLab DS) */}
            <section className="rounded-2xl border border-purple-200/90 bg-gradient-to-b from-white to-purple-50/20 p-4 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 border-b border-purple-100/80 pb-3">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-purple-100 text-purple-700">
                    <Layers size={16} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-xs font-bold text-slate-900">
                        Procesamiento Masivo de Baja Relevancia (&lt; 35)
                      </h4>
                      <span className="c-chip c-chip--purple text-[10px]">
                        <Cpu size={10} className="shrink-0" />
                        <span className="truncate">🤖 Modelo IA: {modelosUtilizados.masivo}</span>
                      </span>
                      <span
                        className={`c-chip text-[10px] ${
                          massQueueCount > 0 ? 'c-chip--purple font-bold' : ''
                        }`}
                        title="Cantidad de mensajes en cola pendientes con relevancia menor a 35"
                      >
                        <span>📥 {massQueueLoading ? 'Consultando...' : `Cola: ${massQueueCount} ${massQueueCount === 1 ? 'mensaje' : 'mensajes'}`}</span>
                      </span>
                    </div>
                    <p className="mt-0.5 text-[11px] text-slate-500 line-clamp-1">
                      Filtra y despacha en bloque interacciones con relevancia menor a 35 mediante Google Gemma 4 con directivas concisas, liberando la mesa de trabajo principal.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                  <div className="flex items-center gap-1.5">
                    <label htmlFor="mass-limit-input" className="text-[11px] font-semibold text-slate-600">
                      Límite:
                    </label>
                    <input
                      id="mass-limit-input"
                      type="number"
                      min={1}
                      max={50}
                      value={massLimit}
                      disabled={massProcessing || massQueueCount === 0}
                      onChange={(e) => setMassLimit(Math.max(1, parseInt(e.target.value, 10) || 1))}
                      className="w-12 rounded-lg border border-slate-200 bg-white px-1.5 py-1 text-center text-xs font-bold text-slate-700 outline-none focus:border-purple-400 disabled:bg-slate-50 disabled:text-slate-400"
                    />
                  </div>
                  <button
                    type="button"
                    disabled={massProcessing || massQueueLoading || massQueueCount === 0}
                    onClick={handleRunMassGemma}
                    className="flex items-center gap-1.5 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-bold text-white shadow-xs transition hover:bg-purple-700 disabled:cursor-not-allowed disabled:bg-purple-300"
                    title={massQueueCount === 0 ? 'Sin mensajes en cola con relevancia menor a 35' : undefined}
                  >
                    <RotateCcw size={12} className={massProcessing ? 'animate-spin' : ''} />
                    <span>
                      {massProcessing
                        ? 'Procesando...'
                        : massQueueCount === 0
                        ? 'Sin pendientes (< 35)'
                        : '⚡ Procesar (< 35)'}
                    </span>
                  </button>
                </div>
              </div>

              {massError && (
                <div className="mt-3 rounded-xl border border-rose-200 bg-rose-50 p-2.5 text-xs font-medium text-rose-700">
                  {massError}
                </div>
              )}

              {massResult && (
                <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <div className="rounded-xl border border-purple-100 bg-purple-50/50 p-2 text-center">
                    <span className="text-[9px] font-bold uppercase text-purple-600">Estado</span>
                    <p className="mt-0.5 text-xs font-bold text-slate-800">{massResult.status}</p>
                  </div>
                  <div className="rounded-xl border border-purple-100 bg-purple-50/50 p-2 text-center">
                    <span className="text-[9px] font-bold uppercase text-purple-600">Procesados</span>
                    <p className="mt-0.5 text-xs font-bold text-purple-900">{massResult.procesados}</p>
                  </div>
                  <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-2 text-center">
                    <span className="text-[9px] font-bold uppercase text-emerald-600">Publicados Directo</span>
                    <p className="mt-0.5 text-xs font-bold text-emerald-700">{massResult.publicados_directo}</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-slate-50 p-2 text-center">
                    <span className="text-[9px] font-bold uppercase text-slate-500">Descartados</span>
                    <p className="mt-0.5 text-xs font-bold text-slate-700">{massResult.descartados}</p>
                  </div>
                </div>
              )}
            </section>
          </div>
        </div>

        {/* Flujo editorial directo (al pie de ambas columnas) */}
        <section className="mt-4 rounded-xl border border-orange-100 bg-orange-50/40 p-3 sm:p-3.5 shadow-2xs">
          <div className="flex items-start gap-2.5">
            <Sparkles
              size={16}
              className="mt-0.5 shrink-0 text-orange-500"
            />

            <div>
              <p className="text-xs font-bold text-slate-800">
                Flujo editorial directo
              </p>

              <p className="mt-0.5 text-xs leading-relaxed text-slate-600">
                El contenido generado y personalizado aquí se guarda directamente en la base de datos de la plataforma. Puedes copiar los textos optimizados para LinkedIn y X para publicarlos en tus redes, mientras que las respuestas a quejas y soporte de Discord se envían en tiempo real con el bot oficial.
              </p>
            </div>
          </div>
        </section>

      {/* Modal de Mesa de Trabajo Multicanal (Redacción Individual o Paralela) */}
      <div
        className={`c-modal ${workspaceModalChannel !== null ? 'is-open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-workspace-title"
        onClick={(e) => {
          if (e.target === e.currentTarget) setWorkspaceModalChannel(null)
        }}
      >
        <div
          className="c-modal__dialog w-full flex flex-col bg-white overflow-hidden shadow-2xl"
          style={{
            maxWidth: workspaceModalChannel === 'all' ? '88rem' : '44rem',
            maxHeight: '92vh',
          }}
        >
          {/* Cabecera del Modal */}
          <div className="c-modal__head flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3.5">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-orange-100 text-orange-600 font-bold">
                {workspaceModalChannel === 'all' ? (
                  <Cpu size={18} />
                ) : workspaceModalChannel === 'linkedin' ? (
                  <BriefcaseBusiness size={18} />
                ) : (
                  <MessageCircle size={18} />
                )}
              </div>
              <div className="min-w-0">
                <h3 id="modal-workspace-title" className="text-sm font-bold text-slate-900 truncate">
                  {workspaceModalChannel === 'all'
                    ? 'Mesa de Trabajo Multicanal — Edición y Publicación Paralela'
                    : workspaceModalChannel === 'linkedin'
                    ? 'Editor Multicanal — LinkedIn'
                    : workspaceModalChannel === 'x'
                    ? 'Editor Multicanal — X (Twitter)'
                    : 'Editor Multicanal — Discord'}
                </h3>
                <p className="text-[11px] text-slate-500 truncate">
                  {selectedWorkflowMessage
                    ? `Insumo: @${selectedWorkflowMessage.author} (#${selectedWorkflowMessage.channel}) • ID #${selectedWorkflowMessage.interactionId}`
                    : 'Soberanía humana (HITL): Edita o publica según tus necesidades'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {workspaceModalChannel !== 'all' && (
                <button
                  type="button"
                  onClick={() => setWorkspaceModalChannel('all')}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
                  title="Ver los 3 canales en paralelo"
                >
                  Ver los 3 canales
                </button>
              )}
              <button
                type="button"
                onClick={() => setWorkspaceModalChannel(null)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
                title="Cerrar ventana (Esc)"
                aria-label="Cerrar ventana"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Cuerpo del Modal */}
          <div className="c-modal__body p-4 sm:p-5 overflow-y-auto max-h-[calc(92vh-130px)] space-y-4">
            {workspaceModalChannel === 'all' && (
              <>
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                  {renderLinkedinCard()}
                  {renderXCard()}
                  {renderDiscordCard()}
                </div>
                {renderHitlBar()}
              </>
            )}

            {workspaceModalChannel === 'linkedin' && (
              <div className="w-full">
                {renderLinkedinCard()}
              </div>
            )}

            {workspaceModalChannel === 'x' && (
              <div className="w-full">
                {renderXCard()}
              </div>
            )}

            {workspaceModalChannel === 'discord' && (
              <div className="w-full">
                {renderDiscordCard()}
              </div>
            )}
          </div>

          {/* Pie del Modal */}
          <div className="c-modal__foot flex items-center justify-between border-t border-slate-200 bg-slate-50/70 px-5 py-3">
            <span className="text-[11px] text-slate-500">
              Presiona <kbd className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">Esc</kbd> o haz clic fuera para cerrar
            </span>
            <button
              type="button"
              onClick={() => setWorkspaceModalChannel(null)}
              className="rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-50 shadow-2xs transition"
            >
              Cerrar ventana
            </button>
          </div>
        </div>
      </div>
      </div>

      {/* PESTAÑA: QUEJAS Y SOPORTE */}
      <div
        id="panel-complaints"
        role="tabpanel"
        aria-labelledby="tab-btn-complaints"
        className={activeContentTab === 'complaints' ? 'space-y-6' : 'hidden'}
      >
      {/* Quejas, reclamos y soporte crítico */}
      <section id="panel-quejas" className="rounded-2xl border border-rose-200 bg-white p-5 shadow-sm">
        <div className="c-panel-head">
          <div className="c-panel-head__main">
            <div className="c-panel-head__icon bg-rose-50 text-rose-600">
              <MessageCircle size={16} />
            </div>

            <div className="c-panel-head__body">
              <div className="c-panel-head__row">
                <h3 className="c-panel-head__title">
                  Panel de Quejas, Reclamos y Soporte Crítico
                </h3>

                <span className="c-chip c-chip--purple">
                  IA + revisión humana
                </span>
              </div>

              <p className="c-panel-head__desc">
                Interacciones negativas de Discord que requieren revisión para determinar si necesitan una respuesta.
              </p>
            </div>
          </div>

          <div className="c-panel-head__actions">
            <span className="c-chip c-chip--danger">
              {complaintsLoading ? 'Cargando...' : `${complaints.length} posibles quejas`}
            </span>
          </div>
        </div>

        {complaintsError && (
          <p role="alert" className="mt-4 text-sm text-red-600">
            No se pudieron cargar las interacciones: {complaintsError}
          </p>
        )}

        <div className="mt-3 max-h-[500px] overflow-y-auto pr-1.5 space-y-2.5">
          {!complaintsLoading && !complaintsError && complaints.length === 0 && (
            <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center">
              <p className="text-xs text-slate-500">
                No hay interacciones negativas para revisar en este momento.
              </p>
            </div>
          )}

          {complaints.map((complaint) => (
            <div
              key={complaint.id}
              className="rounded-xl border border-rose-100 bg-rose-50/20 p-3 sm:p-3.5 transition hover:bg-rose-50/40"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="c-chip c-chip--danger">
                    Posible queja
                  </span>

                  <span className="text-xs font-semibold text-slate-600">
                    #{complaint.canal || 'Discord'} · @{complaint.autor || 'Autor desconocido'}
                  </span>
                </div>

                <span className="c-chip c-chip--brand tabular-nums">
                  Relevancia: {complaint.relevancia ?? 'Sin evaluar'}%
                </span>
              </div>

              <p className="mt-2 whitespace-pre-wrap break-words text-xs leading-relaxed text-slate-700">
                {complaint.texto}
              </p>

              <div className="mt-3 flex justify-end border-t border-rose-100/60 pt-2">
                <button
                  type="button"
                  disabled={complaintPublishing}
                  onClick={() => {
                    if (complaintPublishingRef.current) return
                    complaintRequestRef.current += 1
                    setComplaintPublishError('')
                    setComplaintPublishSuccess('')
                    activeComplaintRef.current = complaint.id
                    setActiveComplaint(complaint.id)
                    setComplaintGenerating(false)
                    setComplaintGenerationError('')
                    setComplaintResponse('')
                  }}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-brand,#ff7400)] px-3 py-1.5 text-xs font-bold text-white shadow-xs transition hover:bg-orange-600"
                >
                  <MessageCircle size={13} />
                  <span>Preparar respuesta</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
      </div>

      {/* Ventana de respuesta a quejas */}
      {activeComplaint !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-slate-950/60 p-3 sm:p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !complaintPublishingRef.current) {
              complaintRequestRef.current += 1
              activeComplaintRef.current = null
              setComplaintGenerating(false)
              setActiveComplaint(null)
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="complaint-dialog-title"
            className="max-h-[90dvh] overflow-y-auto overscroll-contain w-full max-w-2xl rounded-2xl bg-white p-6 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3
                  id="complaint-dialog-title"
                  className="text-xl font-bold text-slate-900"
                >
                  Preparar respuesta
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  Revisa y redacta una respuesta antes de enviarla a Discord.
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  if (complaintPublishingRef.current) return
                  complaintRequestRef.current += 1
                  activeComplaintRef.current = null
                  setComplaintGenerating(false)
                  setActiveComplaint(null)
                }}
                aria-label="Cerrar ventana"
                className="rounded-lg px-3 py-1 text-slate-500 hover:bg-slate-100"
              >
                ✕
              </button>
            </div>

            <div className="mt-5 rounded-xl border border-indigo-100 bg-indigo-50 p-4">
              <p className="text-xs font-semibold uppercase text-indigo-600">
                Mensaje seleccionado
              </p>
              <p className="mt-2 text-sm text-slate-700">
                {complaints.find((item) => item.id === activeComplaint)?.texto
                  || 'No se encontró el mensaje seleccionado.'}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Autor: {complaints.find((item) => item.id === activeComplaint)?.autor || 'Desconocido'}
                {' · '}
                Canal: {complaints.find((item) => item.id === activeComplaint)?.canal || 'Discord'}
              </p>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <label
                  htmlFor="complaint-ai-provider"
                  className="text-xs font-semibold text-slate-600"
                >
                  Modelo IA:
                </label>
                <select
                  id="complaint-ai-provider"
                  value={complaintAiProvider}
                  disabled={complaintGenerating || complaintPublishing}
                  onChange={(event) => setComplaintAiProvider(event.target.value)}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 outline-none focus:border-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                >
                  {AI_PROVIDERS.map((provider) => (
                    <option key={provider} value={provider}>
                      {provider}
                    </option>
                  ))}
                </select>

                <span className="inline-flex items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">
                  <Cpu size={12} />
                  🤖 Modelo IA activo: {complaintAiProvider}
                </span>
              </div>

              <button
                type="button"
                disabled={complaintGenerating || complaintPublishing}
                onClick={async () => {
                  if (activeComplaint === null) return

                  const interactionId = activeComplaint
                  const requestId = ++complaintRequestRef.current
                  activeComplaintRef.current = interactionId

                  setComplaintGenerating(true)
                  setComplaintGenerationError('')

                  try {
                    const data = await generateComplaintResponse(
                      interactionId,
                      complaintAiProvider,
                    )

                    if (
                      typeof data.respuesta !== 'string' ||
                      !data.respuesta.trim()
                    ) {
                      throw new Error('El servidor no devolvió una respuesta válida.')
                    }

                    if (
                      complaintRequestRef.current === requestId &&
                      activeComplaintRef.current === interactionId
                    ) {
                      setComplaintResponse(data.respuesta)
                    }
                  } catch (error) {
                    if (complaintRequestRef.current === requestId) {
                      setComplaintGenerationError(
                        error instanceof Error
                          ? error.message
                          : 'No se pudo generar la respuesta.'
                      )
                    }
                  } finally {
                    if (complaintRequestRef.current === requestId) {
                      setComplaintGenerating(false)
                    }
                  }
                }}
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-200"
              >
                <Sparkles size={16} className={complaintGenerating ? 'animate-pulse' : ''} />
                {complaintGenerating ? 'Generando respuesta...' : 'Generar con IA'}
              </button>
            </div>

            {complaintGenerationError && (
              <p
                role="alert"
                className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
              >
                No se pudo generar la respuesta: {complaintGenerationError}
              </p>
            )}

            <label
              htmlFor="complaint-response"
              className="mt-5 block text-sm font-semibold text-slate-700"
            >
              Respuesta editable
            </label>

            <textarea
              id="complaint-response"
              value={complaintResponse}
              disabled={complaintPublishing || Boolean(complaintPublishSuccess)}
              onChange={(event) => setComplaintResponse(event.target.value)}
              placeholder="Escribe aquí tu respuesta a la queja..."
              rows={7}
              className="mt-2 w-full resize-y rounded-xl border border-slate-200 p-4 text-sm leading-6 text-slate-700 outline-none focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
            />

            <p className="mt-2 text-xs text-slate-500">
              La respuesta no se enviará hasta que confirmes su publicación.
            </p>

            {complaintResponse.trim() && (
              <div className="mt-5 rounded-xl border border-orange-200 bg-orange-50 p-4">
                <p className="text-sm font-semibold text-orange-800">
                  Vista previa de publicación en Discord
                </p>

                {complaintDestinationLoading && (
                  <p className="mt-3 text-sm text-indigo-700">
                    Verificando el destino con el backend...
                  </p>
                )}

                {complaintDestinationError && (
                  <p className="mt-3 text-sm text-red-700" role="alert">
                    {complaintDestinationError}
                  </p>
                )}

                {complaintDestination?.ready &&
                complaintDestination.interaccion_id === activeComplaint ? (
                  <div className="mt-3 space-y-2 rounded-lg border border-green-200 bg-white p-3">
                    <p className="text-sm font-semibold text-green-800">
                      Destino verificado por el backend
                    </p>
                    <p className="text-xs text-slate-700">
                      Canal: <strong>#{complaintDestination.channel_name}</strong>
                    </p>
                    <p className="break-all text-xs text-slate-600">
                      ID del canal: {complaintDestination.channel_id}
                    </p>
                    <p className="text-xs text-slate-700">
                      Autor original: {complaintDestination.author}
                    </p>
                    <p className="text-xs font-semibold text-slate-700">
                      Mensaje original:
                    </p>
                    <p className="whitespace-pre-wrap break-words text-sm text-slate-700">
                      {complaintDestination.original_content || '(Sin contenido de texto)'}
                    </p>
                  </div>
                ) : complaintDestination && !complaintDestination.ready ? (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800" role="alert">
                    <p className="font-semibold">Destino de Discord no disponible</p>
                    <p className="mt-1">
                      {complaintDestination.detail || 'El bot de Discord no está listo o las credenciales no están configuradas.'}
                    </p>
                  </div>
                ) : (
                  <p className="mt-3 text-xs text-amber-800">
                    Canal indicado en la lista: <strong>
                      {complaints.find((item) => item.id === activeComplaint)?.canal || 'No identificado'}
                    </strong>. Destino pendiente de verificación.
                  </p>
                )}

                <p className="mt-1 text-xs text-slate-600">
                  Interacción: <strong>{activeComplaint}</strong>
                </p>

                <p className="mt-3 text-xs font-semibold text-slate-700">
                  Texto que se enviaría:
                </p>

                <p className="mt-2 whitespace-pre-wrap break-words rounded-lg border border-orange-100 bg-white p-3 text-sm text-slate-700">
                  {complaintResponse.trim()}
                </p>

                <p className="mt-3 text-xs text-orange-800">
                  Vista previa únicamente. No se enviará ningún mensaje
                  hasta completar la validación del destino y confirmar
                  expresamente la publicación.
                </p>
              </div>
            )}

            <div className="mt-4 space-y-2" aria-live="polite">
              {complaintPublishing && (
                <p className="text-sm text-indigo-600">
                  Procesando publicación...
                </p>
              )}
              {complaintPublishError && (
                <p className="text-sm text-red-600" role="alert">
                  {complaintPublishError}
                </p>
              )}
              {complaintPublishSuccess && (
                <p className="text-sm text-green-700">
                  {complaintPublishSuccess}
                </p>
              )}
            </div>

            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  if (complaintPublishingRef.current) return
                  complaintRequestRef.current += 1
                  activeComplaintRef.current = null
                  setComplaintGenerating(false)
                  setActiveComplaint(null)
                }}
                className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancelar
              </button>

              <button
                type="button"
                disabled={
                  complaintPublishing ||
                  complaintGenerating ||
                  complaintDestinationLoading ||
                  !complaintDestination?.ready ||
                  complaintDestination.interaccion_id !== activeComplaint ||
                  !complaintResponse.trim() ||
                  complaintResponse.trim().length > 2000 ||
                  Boolean(complaintPublishSuccess) ||
                  (activeComplaint !== null &&
                    complaintPublishLockedIds.current.has(activeComplaint))
                }
                onClick={async () => {
                  const interactionId = activeComplaint
                  const destination = complaintDestination
                  const respuesta = complaintResponse.trim()

                  if (
                    interactionId === null ||
                    !destination?.ready ||
                    destination.interaccion_id !== interactionId ||
                    !respuesta ||
                    respuesta.length > 2000 ||
                    complaintPublishingRef.current ||
                    complaintPublishLockedIds.current.has(interactionId)
                  ) return

                  const confirmado = window.confirm(
                    `¿PUBLICAR RESPUESTA REAL EN DISCORD?\n\n` +
                    `Canal: #${destination.channel_name}\n` +
                    `ID del canal: ${destination.channel_id}\n` +
                    `Interacción: ${interactionId}\n\n` +
                    `TEXTO EXACTO:\n${respuesta}\n\n` +
                    `Aceptar enviará este mensaje a Discord.`
                  )

                  if (!confirmado) return

                  complaintPublishingRef.current = true
                  complaintPublishLockedIds.current.add(interactionId)
                  setComplaintPublishing(true)
                  setComplaintPublishError('')
                  setComplaintPublishSuccess('')

                  try {
                    const resultado = await publishComplaintResponse({
                      interaccion_id: interactionId,
                      respuesta,
                      confirmado: true,
                    })

                    setComplaintPublishSuccess(
                      `Publicado en Discord. Canal: #${destination.channel_name}. ` +
                      `ID del mensaje: ${resultado.discord_message_id}`
                    )

                    setComplaints((current) =>
                      current.filter((item) => item.id !== interactionId)
                    )
                  } catch (error) {
                    complaintPublishLockedIds.current.delete(interactionId)
                    const errMsg = error instanceof Error ? error.message : 'Error de publicación.'
                    const isRateLimit =
                      errMsg.includes('429') ||
                      errMsg.includes('1015') ||
                      errMsg.toLowerCase().includes('rate limit') ||
                      errMsg.toLowerCase().includes('too many requests')
                    setComplaintPublishError(
                      isRateLimit
                        ? '⚠️ Discord ha limitado temporalmente el envío por límite de peticiones de Cloudflare (Error 1015 / 429). Tu respuesta se conserva en el editor. Intenta nuevamente en unos minutos o realiza el despacho desde local.'
                        : `${errMsg} Verifica Discord y Auditoría antes de volver a intentarlo.`
                    )
                  } finally {
                    complaintPublishingRef.current = false
                    setComplaintPublishing(false)
                  }
                }}
                className="flex items-center gap-2 rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-200"
              >
                <Send size={16} />
                {complaintPublishing ? 'Publicando...' : 'Enviar respuesta a Discord'}
              </button>
            </div>
          </section>
        </div>
      )}

      {/* Modal de confirmación para publicación de Anuncio Oficial */}
      {showConfirmModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-announcement-title"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isPublishingAnnouncement) {
              setShowConfirmModal(false)
            }
          }}
        >
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3
                  id="confirm-announcement-title"
                  className="text-lg font-bold text-slate-900"
                >
                  Confirmar publicación de anuncio en Discord
                </h3>
                <p className="mt-1 text-xs text-slate-500">
                  El comunicado se despachará al canal oficial{' '}
                  <strong className="text-indigo-600">
                    {selectedTargetChannelName}
                  </strong>{' '}
                  de Discord.
                </p>
              </div>

              <button
                type="button"
                disabled={isPublishingAnnouncement}
                onClick={() => setShowConfirmModal(false)}
                aria-label="Cerrar modal"
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                ✕
              </button>
            </div>

            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3.5">
              <div className="flex items-center justify-between text-[11px] font-semibold uppercase text-slate-500">
                <span>Vista previa del mensaje</span>
                <span>{finalAnnouncement.length} caracteres</span>
              </div>
              <p className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-200 bg-white p-3 font-mono text-xs leading-relaxed text-slate-800">
                {finalAnnouncement.trim()}
              </p>
            </div>

            <p className="mt-3 text-[11px] font-medium text-amber-700">
              ⚠️ Esta acción es irreversible: el anuncio será visible inmediatamente para los miembros de la comunidad y quedará registrado en la auditoría.
            </p>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                disabled={isPublishingAnnouncement}
                onClick={() => setShowConfirmModal(false)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={isPublishingAnnouncement}
                onClick={handleConfirmPublish}
                className="flex items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-xs font-semibold text-white hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-200"
              >
                {isPublishingAnnouncement ? (
                  <RotateCcw size={14} className="animate-spin" />
                ) : (
                  <Send size={14} />
                )}
                {isPublishingAnnouncement ? 'Publicando...' : 'Confirmar y publicar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ContentStudio
