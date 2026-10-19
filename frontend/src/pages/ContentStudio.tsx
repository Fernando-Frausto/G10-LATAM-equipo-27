import {
  AlertTriangle,
  BriefcaseBusiness,
  CheckCircle,
  Copy,
  FileText,
  Megaphone,
  MessageCircle,
  Pencil,
  RotateCcw,
  Send,
  Sparkles,
  Upload,
} from 'lucide-react'

import { useEffect, useRef, useState } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'

import {
  createContentDraft,
  generateAnnouncement,
  generateComplaintResponse,
  getAnnouncementWebhookStatus,
  getComplaintPublishPreview,
  getPublishedComplaintIds,
  publishAnnouncement,
  publishComplaintResponse,
  regenerateContent,
} from '../api/contentWorkflow'
import type {
  AnnouncementWebhookStatus,
  ComplaintPublishPreview,
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
  if (!message || !message.content.trim()) {
    return {
      linkedin: { content: '', submitted: false },
      x: { content: '', submitted: false },
      discord: { content: '', submitted: false },
    }
  }

  const source = message.content.trim()

  return {
    linkedin: {
      interactionId: message.interactionId,
      content: `Una conversación de nuestra comunidad nos invita a reflexionar:\n\n"${source}"\n\nTema: ${message.topic}\n\nEn CloudEdTech valoramos las experiencias compartidas y el aprendizaje colaborativo.\n\n#CloudEdTech #Comunidad #Aprendizaje`,
      submitted: false,
    },
    x: {
      interactionId: message.interactionId,
      content: `Desde nuestra comunidad: ${source}`.slice(0, 280),
      submitted: false,
    },
    discord: {
      interactionId: message.interactionId,
      attachments: [...message.attachments],
      content: `Gracias por compartir tu mensaje en #${message.channel}.\n\n"${source}"\n\nDesde CloudEdTech queremos continuar esta conversación con la comunidad.`,
      submitted: false,
    },
  }
}

function ContentStudio() {
  const location = useLocation()
  const [searchParams] = useSearchParams()

  const interactionParam =
    searchParams.get('interaction') ||
    (location.state as { interactionId?: number | string } | null)?.interactionId
  const targetInteractionId = interactionParam
    ? parseInt(String(interactionParam), 10)
    : null

  const [activeFormat, setActiveFormat] =
    useState<ContentFormat>('linkedin')
  const [copiedFormat, setCopiedFormat] =
    useState<ContentFormat | null>(null)
  const [showDiscordFiles, setShowDiscordFiles] =
    useState(false)
  const [drafts, setDrafts] = useState<
    Record<ContentFormat, DraftState>
  >(() => buildDefaultDrafts(null))

  const [workflowMessages, setWorkflowMessages] =
    useState<WorkflowMessage[]>([])
  const [selectedMessageId, setSelectedMessageId] =
    useState<number | null>(null)
  const selectedWorkflowId = selectedMessageId
  const setSelectedWorkflowId = setSelectedMessageId

  const [workflowLoading, setWorkflowLoading] = useState(true)
  const [workflowError, setWorkflowError] = useState('')

  const originalMessageRef = useRef<HTMLElement | null>(null)

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
            const defaultChan = status.channels.find((c) => c.id !== 'webhook') || status.channels[0]
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
            channel_hint: 'anuncios',
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

        let messages = data.messages
          .filter(
            (item) =>
              (item.analysis.workflow_stage === 'en_redaccion' ||
                item.analysis.workflow_stage === 'en_analisis') &&
              item.analysis.relevance >= 70 &&
              item.analysis.curation_status !== 'discarded',
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
          }))
          .sort((a, b) => b.interactionId - a.interactionId)

        if (targetInteractionId && !Number.isNaN(targetInteractionId)) {
          const existsInFiltered = messages.some(
            (m) => m.interactionId === targetInteractionId,
          )

          if (!existsInFiltered) {
            const foundInAll = data.messages.find(
              (item) => item.message.interaction_id === targetInteractionId,
            )
            if (foundInAll) {
              const extraMsg: WorkflowMessage = {
                interactionId: foundInAll.message.interaction_id,
                author: foundInAll.message.author_name || 'Usuario',
                channel: foundInAll.message.channel_name,
                content: foundInAll.message.content,
                attachments: Array.isArray(foundInAll.message.attachments)
                  ? foundInAll.message.attachments
                  : [],
                topic: foundInAll.analysis.topic,
                sentiment: foundInAll.analysis.sentiment,
                relevance: foundInAll.analysis.relevance,
              }
              messages = [extraMsg, ...messages]
            } else {
              try {
                const liveSummary = await getCommunityLiveSummary()
                const highlight = liveSummary.highlights?.find(
                  (h) => (h.id_mensaje ?? Number(h.id)) === targetInteractionId,
                )
                if (highlight) {
                  const extraMsg: WorkflowMessage = {
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
                  }
                  messages = [extraMsg, ...messages]
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
          setWorkflowMessages(messages)

          const targetMsg =
            targetInteractionId && !Number.isNaN(targetInteractionId)
              ? messages.find((m) => m.interactionId === targetInteractionId)
              : null

          const initialSelectedId = targetMsg
            ? targetMsg.interactionId
            : messages[0]?.interactionId ?? null

          setSelectedMessageId(initialSelectedId)

          if (targetMsg) {
            setDrafts(buildDefaultDrafts(targetMsg))
            setTimeout(() => {
              originalMessageRef.current?.scrollIntoView({
                behavior: 'smooth',
                block: 'start',
              })
            }, 100)
          } else if (messages.length > 0) {
            setDrafts((current) => {
              if (current.linkedin.interactionId) return current
              return buildDefaultDrafts(messages[0])
            })
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
    const targetMsg = workflowMessages.find(
      (m) => m.interactionId === targetInteractionId,
    )
    if (targetMsg && targetMsg.interactionId !== selectedMessageId) {
      setSelectedMessageId(targetMsg.interactionId)
      setDrafts(buildDefaultDrafts(targetMsg))
      setTimeout(() => {
        originalMessageRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        })
      }, 100)
    }
  }, [targetInteractionId, workflowMessages, selectedMessageId])

  const availableDiscordChannels =
    announcementStatus?.channels && announcementStatus.channels.length > 0
      ? announcementStatus.channels
      : [
          { id: '1559244522842488942', name: '#notificaciones' },
          { id: '1550016804418621452', name: '#general' },
          { id: '1551309281041715230', name: '#chat-egresados' },
          { id: '1551309330198953994', name: '#oportunidades-laborales' },
          { id: '1551309664397033513', name: '#faq' },
          { id: '1559244209884504245', name: '#pqrs' },
          { id: 'webhook', name: 'Canal predeterminado del Webhook (#anuncios / #general)' },
        ]

  const selectedTargetChannelName =
    availableDiscordChannels.find((c) => c.id === selectedDiscordChannel)?.name ||
    '#anuncios'

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
      setAnnouncementPublishError(
        error instanceof Error
          ? error.message
          : 'Error al publicar anuncio en Discord.',
      )
      setShowConfirmModal(false)
    } finally {
      setIsPublishingAnnouncement(false)
    }
  }

  const selectedWorkflowMessage =
    workflowMessages.find(
      (item) => item.interactionId === selectedWorkflowId,
    ) ?? null

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

    const message = workflowMessages.find(
      (item) => item.interactionId === draft.interactionId,
    )

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

  const formats: Array<{
    id: ContentFormat
    name: string
    description: string
    icon: typeof BriefcaseBusiness
  }> = [
      {
        id: 'linkedin',
        name: 'LinkedIn',
        description: 'Publicación profesional',
        icon: BriefcaseBusiness,
      },
      {
        id: 'x',
        name: 'X',
        description: 'Publicación breve para X',
        icon: MessageCircle,
      },
      {
        id: 'discord',
        name: 'Discord',
        description: 'Mensaje para la comunidad',
        icon: MessageCircle,
      },
    ]

  return (
    <div>
      {/* Encabezado */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-100 text-orange-500">
            <Sparkles size={21} />
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900">
              Redacción de Contenidos
            </h2>

            <p className="mt-1 text-sm text-slate-500">
              Convierte conversaciones de Discord en contenido
              adaptado para diferentes canales
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-3 py-2">
          <span className="h-2 w-2 rounded-full bg-green-500" />

          <span className="text-xs font-semibold text-green-700">
            Discord conectado
          </span>
        </div>
      </div>

      {/* Panel de Anuncios Oficiales de la Comunidad (Discord Webhook) */}
      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {/* Cabecera del Panel */}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-orange-100 text-orange-600">
              <Megaphone size={20} />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-slate-900">
                  Panel de Anuncios Oficiales de la Comunidad (Discord Webhook)
                </h3>

                <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
                  #{announcementStatus?.channel_hint || 'anuncios'}
                </span>
              </div>

              <p className="mt-1 text-xs text-slate-500">
                Redacta comunicados oficiales, optimízalos con IA o carga archivos .txt/.md y publícalos directamente vía Webhook.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {announcementStatusLoading ? (
              <span className="text-xs text-slate-400">Consultando webhook...</span>
            ) : announcementStatus?.configured ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Webhook configurado
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
                <span className="h-2 w-2 rounded-full bg-amber-500" />
                Webhook no configurado
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

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Descripción del anuncio para generar con IA */}
          <div className="flex flex-col rounded-xl border border-slate-200 bg-slate-50/50 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label
                htmlFor="announcement-draft"
                className="text-xs font-bold uppercase tracking-wide text-slate-700"
              >
                Descripción del anuncio para generar con IA
              </label>

              <div className="flex items-center gap-2">
                <span className="text-[11px] font-semibold text-slate-500">IA:</span>
                <select
                  value={selectedAnnouncementModel}
                  onChange={(e) => setSelectedAnnouncementModel(e.target.value)}
                  className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-semibold text-slate-700 outline-none transition focus:border-indigo-400"
                >
                  <option value="gemini">Google Gemini Flash Lite</option>
                  <option value="groq">Groq (Cerebro IA)</option>
                  <option value="gemma">Google Gemma 4</option>
                </select>

                <span
                  className={`text-xs font-medium ${
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
              rows={8}
              className="mt-2.5 w-full flex-1 resize-y rounded-xl border border-slate-200 bg-white p-3.5 text-sm leading-relaxed text-slate-700 outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100"
            />

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

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200/60 pt-3">
              <div>
                {draftText && (
                  <button
                    type="button"
                    onClick={() => {
                      setDraftText('')
                      setAnnouncementGenerateError('')
                    }}
                    className="text-xs text-slate-400 transition hover:text-slate-600"
                  >
                    Limpiar descripción
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
                className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-200"
              >
                {isGeneratingAnnouncement ? (
                  <RotateCcw size={14} className="animate-spin" />
                ) : (
                  <Sparkles size={14} />
                )}
                {isGeneratingAnnouncement ? 'Generando anuncio con IA...' : 'Generar anuncio con IA'}
              </button>
            </div>
          </div>

          {/* Editor de Anuncio Final y Semáforo de Caracteres */}
          <div className="flex flex-col rounded-xl border border-slate-200 bg-slate-50/50 p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label
                htmlFor="announcement-final"
                className="text-xs font-bold uppercase tracking-wide text-slate-700"
              >
                Editor de Anuncio Final
              </label>

              {/* Semáforo cromático */}
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${
                    finalAnnouncement.length <= 1500
                      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                      : finalAnnouncement.length <= 2000
                      ? 'border-amber-200 bg-amber-50 text-amber-700'
                      : 'border-rose-200 bg-rose-50 text-rose-700'
                  }`}
                >
                  {finalAnnouncement.length <= 1500
                    ? 'Recomendado por manual de marca'
                    : finalAnnouncement.length <= 2000
                    ? 'Extenso pero permitido por Discord'
                    : 'Excede el límite máximo de 2000 caracteres de Discord'}
                </span>
                <span className="text-xs font-bold text-slate-700">
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
              rows={8}
              className="mt-2.5 w-full flex-1 resize-y rounded-xl border border-slate-200 bg-white p-3.5 text-sm leading-relaxed text-slate-700 outline-none transition focus:border-orange-400 focus:ring-2 focus:ring-orange-100"
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

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200/60 pt-3">
              {/* Botón de carga de archivo movido aquí al editor final */}
              <div className="flex items-center gap-2">
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
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-xs transition hover:border-slate-300 hover:bg-slate-50"
                >
                  <Upload size={14} />
                  Cargar archivo .txt / .md
                </button>

                {finalAnnouncement && (
                  <button
                    type="button"
                    onClick={() => {
                      setFinalAnnouncement('')
                      setAnnouncementPublishError('')
                      setAnnouncementPublishSuccess('')
                    }}
                    className="text-xs text-slate-400 transition hover:text-slate-600"
                  >
                    Limpiar
                  </button>
                )}
              </div>

              {/* Selector de Canal y Botón Publicar */}
              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <label htmlFor="announcement-channel" className="text-[11px] font-semibold text-slate-500">
                    Canal:
                  </label>
                  <select
                    id="announcement-channel"
                    value={selectedDiscordChannel}
                    onChange={(e) => setSelectedDiscordChannel(e.target.value)}
                    className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 outline-none transition focus:border-orange-400"
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
                  className="flex items-center gap-2 rounded-lg bg-orange-500 px-4 py-2 text-xs font-semibold text-white shadow-xs transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-200"
                >
                  <Send size={14} />
                  Publicar anuncio en Discord
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Bandeja de mensajes listos para redacción (Selector de cola) */}
      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2.5">
              <h3 className="font-bold text-slate-900">
                Bandeja de mensajes en Redacción
              </h3>
              <span className="rounded-full border border-orange-200 bg-orange-50 px-3 py-0.5 text-xs font-bold text-orange-600">
                {workflowMessages.length} listos para copy
              </span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Interacciones de la comunidad analizadas por la IA con alta relevancia. Haz clic en cualquiera para cargarla en la mesa de trabajo.
            </p>
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

        {!workflowLoading && !workflowError && workflowMessages.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center">
            <p className="text-xs text-slate-500">
              No hay mensajes pendientes de redacción en este momento.
            </p>
          </div>
        )}

        {!workflowLoading && !workflowError && workflowMessages.length > 0 && (
          <div className="flex gap-3 overflow-x-auto pb-3 pt-1 scrollbar-thin">
            {workflowMessages.map((item) => {
              const isActive = selectedWorkflowId === item.interactionId

              return (
                <button
                  key={item.interactionId}
                  type="button"
                  onClick={() => {
                    setSelectedWorkflowId(item.interactionId)
                    prepareWorkflowContent(item)
                  }}
                  className={`min-w-[280px] max-w-[320px] shrink-0 rounded-xl border p-4 text-left transition ${
                    isActive
                      ? 'border-orange-500 bg-orange-50/70 shadow-sm ring-1 ring-orange-400'
                      : 'border-slate-200 bg-white hover:border-orange-300 hover:bg-slate-50/60'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-xs font-bold text-slate-900">
                      @{item.author}
                    </span>
                    <span className="shrink-0 rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-bold text-orange-700">
                      {item.relevance}% rel.
                    </span>
                  </div>

                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-slate-500">
                    <span className="font-medium text-indigo-600">#{item.channel}</span>
                    <span>•</span>
                    <span className="truncate text-slate-600">{item.topic}</span>
                  </div>

                  <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-600">
                    "{item.content}"
                  </p>

                  <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-[11px]">
                    <span
                      className={`font-semibold ${
                        isActive ? 'text-orange-600' : 'text-slate-400'
                      }`}
                    >
                      {isActive ? '● En mesa de trabajo' : 'Click para cargar'}
                    </span>
                    <span className="text-[10px] text-slate-400">ID #{item.interactionId}</span>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </section>

      {/* Mensaje original */}
      <section
        ref={originalMessageRef}
        className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
              <MessageCircle size={19} />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-slate-900">
                  Mensaje original de Discord
                </h3>

                <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                  Mesa de trabajo
                </span>
              </div>

              <p className="mt-1 text-xs text-slate-400">
                Insumo seleccionado para generación de contenido
              </p>
            </div>
          </div>

          <span className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-600">
            Discord
          </span>
        </div>

        <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="font-semibold text-slate-900">
                {selectedWorkflowMessage?.author ?? 'Sin mensaje seleccionado'}
              </p>

              <p className="mt-1 text-xs text-slate-400">
                Conversación seleccionada
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
                Sentimiento {selectedWorkflowMessage?.sentiment ?? 'Sin datos'}
              </span>

              <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-semibold text-orange-700">
                Relevancia {selectedWorkflowMessage?.relevance ?? 'Sin datos'}
              </span>
            </div>
          </div>

          <h4 className="mt-4 font-bold text-slate-900">
            {selectedWorkflowMessage?.topic ?? 'Selecciona una interacción'}
          </h4>

          <div className="mt-3 rounded-r-xl border-l-4 border-orange-500 bg-white/90 p-4 shadow-xs">
            <p className="text-sm italic leading-relaxed text-slate-700">
              "{selectedWorkflowMessage?.content ?? 'Selecciona una conversación de la bandeja para comenzar a redactar sus copys.'}"
            </p>
          </div>
        </div>
      </section>

      {/* Selector de formato */}
      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-50 text-orange-500">
              <FileText size={18} />
            </div>

            <div>
              <h3 className="font-bold text-slate-900">
                Contenido generado
              </h3>

              <p className="mt-1 text-sm text-slate-500">
                Revisa y adapta cada formato antes de enviarlo a
                aprobación
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label
              htmlFor="workspace-ai-provider"
              className="text-xs font-semibold text-slate-600"
            >
              Modelo IA:
            </label>
            <select
              id="workspace-ai-provider"
              value={workspaceAiProvider}
              disabled={Object.values(drafts).some((d) => d.regenerating)}
              onChange={(event) => setWorkspaceAiProvider(event.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 outline-none focus:border-orange-500 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
            >
              {AI_PROVIDERS.map((provider) => (
                <option key={provider} value={provider}>
                  {provider}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
          {formats.map((format) => {
            const Icon = format.icon
            const selected = activeFormat === format.id

            return (
              <button
                key={format.id}
                type="button"
                onClick={() => setActiveFormat(format.id)}
                className={`flex items-center gap-3 rounded-xl border p-4 text-left transition ${selected
                  ? 'border-orange-300 bg-orange-50'
                  : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
              >
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-lg ${selected
                    ? 'bg-orange-500 text-white'
                    : 'bg-slate-100 text-slate-600'
                    }`}
                >
                  <Icon size={19} />
                </div>

                <div>
                  <p className="font-semibold text-slate-900">
                    {format.name}
                  </p>

                  <p className="mt-0.5 text-xs text-slate-500">
                    {format.description}
                  </p>
                </div>
              </button>
            )
          })}
        </div>
      </section>

      {/* Tarjetas */}
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        {formats.map((format) => {
          const Icon = format.icon
          const draft = drafts[format.id]

          return (
            <section
              key={format.id}
              className={`flex flex-col rounded-2xl border bg-white shadow-sm transition ${activeFormat === format.id
                ? 'border-orange-300 ring-2 ring-orange-50'
                : 'border-slate-200'
                }`}
            >
              {/* Cabecera tarjeta */}
              <div className="border-b border-slate-100 p-5">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-700">
                      <Icon size={18} />
                    </div>

                    <div>
                      <h3 className="font-bold text-slate-900">
                        {format.name}
                      </h3>

                      <p className="text-xs text-slate-400">
                        {format.description}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${draft.submitted
                      ? 'bg-green-50 text-green-700'
                      : 'bg-amber-50 text-amber-700'
                      }`}
                  >
                    {draft.submitted
                      ? 'En aprobación'
                      : 'Borrador'}
                  </span>
                </div>
              </div>

              {/* Editor */}
              <div className="flex flex-1 flex-col p-5">
                <label
                  htmlFor={`content-${format.id}`}
                  className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  <Pencil size={14} />
                  Contenido editable
                </label>

                <textarea
                  id={`content-${format.id}`}
                  value={draft.content}
                  disabled={draft.submitted}
                  onFocus={() => setActiveFormat(format.id)}
                  onChange={(event) =>
                    updateContent(
                      format.id,
                      event.target.value,
                    )
                  }
                  className="mt-3 min-h-72 flex-1 resize-y rounded-xl border border-slate-200 p-4 text-sm leading-6 text-slate-700 outline-none transition focus:border-orange-400 focus:ring-2 focus:ring-orange-100 disabled:bg-slate-50 disabled:text-slate-500"
                />
                {format.id === 'x' && (
                  <p
                    className={`mt-2 text-right text-xs font-semibold ${
                      [...draft.content].length > 280
                        ? 'text-rose-600'
                        : 'text-slate-500'
                    }`}
                  >
                    {[...draft.content].length} / 280 caracteres
                  </p>
                )}
                {format.id === 'discord' && discordFiles.length > 0 && (
                  <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-slate-800">
                          Archivos adjuntos
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {discordFiles.length} archivo(s) del mensaje original
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          setShowDiscordFiles((current) => !current)
                        }
                        className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        {showDiscordFiles ? 'Ocultar archivos' : 'Ver archivos'}
                      </button>
                    </div>

                    {showDiscordFiles && (
                      <div className="mt-3 space-y-2">
                        {discordFiles.map((file) => (
                          <div
                            key={file.id}
                            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2"
                          >
                            <div className="min-w-0">
                              <p className="break-all text-xs font-semibold text-slate-700">
                                {file.filename}
                              </p>
                              <p className="mt-0.5 text-xs text-slate-400">
                                {file.content_type || 'Archivo'} · {formatDiscordFileSize(file.size)}
                              </p>
                            </div>

                            <a
                              href={file.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="rounded-lg border border-orange-200 px-3 py-2 text-xs font-semibold text-orange-600 transition hover:bg-orange-50"
                            >
                              Abrir / descargar
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
                    onClick={() => handleCopy(format.id)}
                    className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
                  >
                    {copiedFormat === format.id ? (
                      <CheckCircle size={15} />
                    ) : (
                      <Copy size={15} />
                    )}

                    {copiedFormat === format.id
                      ? 'Copiado'
                      : 'Copiar'}
                  </button>

                  <button
                    type="button"
                    disabled={draft.submitted || draft.submitting || draft.regenerating || Boolean(draft.savedId)}
                    onClick={() =>
                      handleRegenerate(format.id)
                    }
                    className="flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
                  >
                    <RotateCcw size={15} className={draft.regenerating ? 'animate-spin' : ''} />
                    {draft.regenerating ? 'Regenerando...' : 'Regenerar'}
                  </button>
                </div>

                {/* Guardar y registrar contenido */}
                <button
                  type="button"
                  onClick={() => handleSubmit(format.id)}
                  disabled={draft.submitted || draft.submitting || draft.regenerating || (format.id === 'x' && [...draft.content].length > 280)}
                  className={`mt-3 flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition ${draft.submitted
                    ? 'cursor-not-allowed bg-green-50 text-green-700'
                    : 'bg-orange-500 text-white hover:bg-orange-600'
                    }`}
                >
                  {draft.submitted ? (
                    <CheckCircle size={16} />
                  ) : (
                    <Send size={16} />
                  )}

                  {draft.submitted
                    ? 'Guardado en la plataforma'
                    : draft.submitting
                      ? 'Guardando...'
                      : draft.savedId
                        ? 'Reintentar guardado'
                        : 'Guardar y registrar contenido'}
                </button>

                {draft.savedId && (
                  <p className="mt-2 text-center text-xs font-medium text-green-700">
                    Contenido #{draft.savedId} registrado exitosamente. Listo para copiar y publicar.
                  </p>
                )}

                {draft.error && (
                  <p role="alert" className="mt-2 text-center text-xs text-red-600">
                    {draft.error}
                  </p>
                )}

                {format.id === 'discord' && (
                  <p className="mt-3 text-center text-xs leading-5 text-slate-400">
                    La publicación en Discord estará disponible
                    únicamente después de su aprobación. Este contenido
                    incluye {discordFiles.length} archivo(s) adjunto(s).
                  </p>
                )}

                {format.id !== 'discord' && (
                  <p className="mt-3 text-center text-xs leading-5 text-slate-400">
                    Una vez aprobado, el contenido podrá copiarse
                    para su publicación externa.
                  </p>
                )}
              </div>
            </section>
          )
        })}
      </div>

      {/* Quejas, reclamos y soporte crítico */}
      <section className="mt-6 rounded-2xl border border-rose-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 text-rose-600">
              <MessageCircle size={19} />
            </div>

            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-bold text-slate-900">
                  Panel de Quejas, Reclamos y Soporte Crítico
                </h3>

                <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-600">
                  IA + revisión humana
                </span>
              </div>

              <p className="mt-1 text-sm text-slate-500">
                Interacciones negativas de Discord que requieren revisión
                para determinar si necesitan una respuesta.
              </p>
            </div>
          </div>

          <span className="rounded-full bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-600">
            {complaintsLoading ? 'Cargando...' : `${complaints.length} posibles quejas`}
          </span>
        </div>

        {complaintsError && (
          <p role="alert" className="mt-4 text-sm text-red-600">
            No se pudieron cargar las interacciones: {complaintsError}
          </p>
        )}

        <div className="mt-5 max-h-[480px] overflow-y-auto pr-1.5 space-y-3">
          {!complaintsLoading && !complaintsError && complaints.length === 0 && (
            <p className="text-sm text-slate-500">
              No hay interacciones negativas para revisar.
            </p>
          )}

          {complaints.map((complaint) => (
            <div
              key={complaint.id}
              className="rounded-xl border border-rose-100 bg-rose-50/30 p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-rose-100 px-2.5 py-1 text-xs font-semibold text-rose-700">
                    Posible queja
                  </span>

                  <span className="text-xs text-slate-500">
                    {complaint.canal || 'Discord'} · {complaint.autor || 'Autor desconocido'}
                  </span>
                </div>

                <span className="text-xs font-medium text-orange-600">
                  Relevancia: {complaint.relevancia ?? 'Sin evaluar'}
                </span>
              </div>

              <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">
                {complaint.texto}
              </p>

              <div className="mt-4 flex justify-end">
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
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-indigo-700"
                >
                  Preparar respuesta
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

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
              <div className="flex items-center gap-2">
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
                      throw new Error('El servidor no devolvio una respuesta valida.')
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
                    `PUBLICAR RESPUESTA REAL EN DISCORD?\n\n` +
                    `Canal: #${destination.channel_name}\n` +
                    `ID del canal: ${destination.channel_id}\n` +
                    `Interaccion: ${interactionId}\n\n` +
                    `TEXTO EXACTO:\n${respuesta}\n\n` +
                    `Aceptar enviara este mensaje a Discord.`
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
                    setComplaintPublishError(
                      (error instanceof Error ? error.message : 'Error de publicacion.') +
                      ' Verifica Discord y Auditoria antes de volver a intentarlo.'
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

      {/* Flujo editorial directo */}
      <section className="mt-6 rounded-2xl border border-orange-100 bg-orange-50/50 p-5">
        <div className="flex items-start gap-3">
          <Sparkles
            size={18}
            className="mt-0.5 shrink-0 text-orange-500"
          />

          <div>
            <p className="text-sm font-semibold text-slate-800">
              Flujo editorial directo
            </p>

            <p className="mt-1 text-sm leading-6 text-slate-600">
              El contenido generado y personalizado aquí se guarda directamente en la base de datos de la plataforma. Puedes copiar los textos optimizados para LinkedIn y X para publicarlos en tus redes, mientras que las respuestas a quejas y soporte de Discord se envían en tiempo real con el bot oficial.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default ContentStudio
