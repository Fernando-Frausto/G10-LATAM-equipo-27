import { mockCommunityData } from '../data/mockCommunityData'

const API_BASE_URL = (
    import.meta.env.VITE_API_URL ||
    import.meta.env.VITE_MOTOR_API_URL ||
    'http://127.0.0.1:8002'
).replace(/\/$/, '')

export interface CommunityHighlight {
    id: number | string
    id_mensaje?: number
    is_published?: boolean
    published_platforms?: string[]
    type: string
    title: string
    message: string
    content?: string
    copy_final?: string | null
    author: string
    channel: string
    sentiment: number
    sentiment_score?: number
    relevance: number
    color: 'green' | 'blue' | 'purple' | string
}

export interface EmojiScorecard {
    emoji: string
    count: number
    value?: number
    sentiment: 'positive' | 'neutral' | 'negative' | string
    label: string
    description: string
    trend: string
}

export interface CommunityAnalyticsResponse {
    sentiment?: {
        distribution?: Array<{ name: string; value: number }>
        evolution?: Array<{ date: string; positive: number; neutral: number; negative: number }>
    }
    topics?: Array<{ topic: string; percentage: number }>
    hashtags?: Array<{
        id: number
        name: string
        mentions: number
        growth: number | null
    }>
    emojis?: EmojiScorecard[]
    brand_alignment_percentage?: number
    analizados?: number
}

export interface CommunityHighlightsSummary {
    detected: number
    high_relevance: number
    ready_for_content: number
}

export interface AudienceSegment {
    name: string
    members: number
    percentage: number
}

export interface CommunityAudience {
    total_members: number
    growth: number
    active_members: number
    participation_rate: number
    segments: AudienceSegment[]
    ai_segments?: Record<string, number>
}

export interface CommunityCalendarItem {
    id: number | string
    date: string
    day: string
    messages: number
    sentiment: number
    highlights: number
}

export interface CommunityReportItem {
    id: number | string
    name: string
    type: string
    format: string
    created_at: string
    status: string
    status_label: string
    total_mensajes?: number
    semana?: string
}

export interface CommunityLiveSummary {
    highlights: CommunityHighlight[]
    highlights_summary: CommunityHighlightsSummary
    audience: CommunityAudience
    calendar: CommunityCalendarItem[]
    reports: CommunityReportItem[]
    isLive: boolean
}

export async function getCommunityLiveSummary(): Promise<CommunityLiveSummary> {
    try {
        const resp = await fetch(`${API_BASE_URL}/api/v1/community/live-summary`)
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`)
        }
        const data = await resp.json()

        // 1. Normalizar highlights
        const rawHighlights = Array.isArray(data.highlights) && data.highlights.length > 0
            ? data.highlights
            : mockCommunityData.highlights

        const colors: ('green' | 'blue' | 'purple')[] = ['green', 'blue', 'purple']
        const highlights: CommunityHighlight[] = rawHighlights.map((h: any, idx: number) => {
            const rawSent = h.sentiment
            let sentScore = 80
            if (typeof h.sentiment_score === 'number') {
                sentScore = Math.round(h.sentiment_score * 100)
            } else if (typeof rawSent === 'number') {
                sentScore = rawSent
            } else if (typeof rawSent === 'string') {
                if (rawSent.toLowerCase().includes('pos')) sentScore = 92
                else if (rawSent.toLowerCase().includes('neg')) sentScore = 35
                else sentScore = 70
            }

            const msgText = h.copy_final && h.copy_final !== "Pendiente de redacción por Enoc..."
                ? h.copy_final
                : (h.content || h.message || h.texto_original || '')

            return {
                id: h.id || h.id_mensaje || idx + 1,
                id_mensaje: typeof h.id_mensaje === 'number' ? h.id_mensaje : (typeof h.id === 'number' ? h.id : undefined),
                is_published: Boolean(h.is_published),
                published_platforms: Array.isArray(h.published_platforms) ? h.published_platforms : [],
                type: h.type || (h.copy_final ? 'Historia curada' : 'Insight de comunidad'),
                title: h.title || h.titulo || `Destacado #${idx + 1}`,
                message: msgText,
                content: msgText,
                copy_final: h.copy_final || null,
                author: h.author || h.autor || 'Comunidad Discord',
                channel: h.channel || h.canal || '#general',
                sentiment: sentScore,
                sentiment_score: h.sentiment_score,
                relevance: typeof h.relevance === 'number' ? h.relevance : (h.relevancia ?? 85),
                color: h.color || colors[idx % colors.length],
            }
        })

        // 2. Normalizar highlights_summary
        const highlights_summary: CommunityHighlightsSummary = data.highlights_summary
            ? {
                detected: data.highlights_summary.detected ?? highlights.length,
                high_relevance: data.highlights_summary.high_relevance ?? 0,
                ready_for_content: data.highlights_summary.ready_for_content ?? 0,
            }
            : mockCommunityData.highlights_summary

        // 3. Normalizar audience
        let audience: CommunityAudience
        if (data.audience && typeof data.audience.total_members === 'number') {
            const segs: AudienceSegment[] = (data.audience.segments || []).map((s: any) => ({
                name: s.name || 'Segmento',
                members: s.members ?? s.count ?? 0,
                percentage: s.percentage ?? 0,
            }))
            audience = {
                total_members: data.audience.total_members,
                growth: data.audience.growth ?? mockCommunityData.audience.growth,
                active_members: data.audience.active_members ?? data.audience.total_members,
                participation_rate: data.audience.participation_rate ?? 68.6,
                segments: segs.length > 0 ? segs : mockCommunityData.audience.segments,
                ai_segments: data.audience.ai_segments,
            }
        } else {
            audience = mockCommunityData.audience
        }

        // 4. Normalizar calendar
        const calendar: CommunityCalendarItem[] = Array.isArray(data.calendar) && data.calendar.length > 0
            ? data.calendar.map((c: any, idx: number) => ({
                id: c.id || idx + 1,
                date: c.date || new Date().toISOString().slice(0, 10),
                day: c.day || 'Lun',
                messages: c.messages ?? 0,
                sentiment: c.sentiment ?? 75,
                highlights: c.highlights ?? 0,
            }))
            : mockCommunityData.calendar

        // 5. Normalizar reports
        const reports: CommunityReportItem[] = Array.isArray(data.reports) && data.reports.length > 0
            ? data.reports.map((r: any, idx: number) => ({
                id: r.id || idx + 1,
                name: r.name || r.title || `Reporte Semanal ${r.semana || r.id}`,
                type: r.type || 'Análisis semanal',
                format: r.format || 'JSON',
                created_at: r.created_at || new Date().toISOString(),
                status: r.status || 'ready',
                status_label: r.status_label || (r.status === 'ready' ? 'Completado' : 'Guardado local'),
                total_mensajes: r.total_mensajes,
                semana: r.semana,
            }))
            : mockCommunityData.reports

        return {
            highlights,
            highlights_summary,
            audience,
            calendar,
            reports,
            isLive: true,
        }
    } catch {
        return {
            highlights: mockCommunityData.highlights.map(h => ({ ...h, color: h.color || 'green' })),
            highlights_summary: mockCommunityData.highlights_summary,
            audience: mockCommunityData.audience,
            calendar: mockCommunityData.calendar,
            reports: mockCommunityData.reports,
            isLive: false,
        }
    }
}

export async function fetchCommunityExportData(): Promise<any> {
    try {
        const resp = await fetch(`${API_BASE_URL}/api/v1/export/community-data`)
        if (!resp.ok) {
            throw new Error(`HTTP ${resp.status}`)
        }
        return await resp.json()
    } catch {
        return mockCommunityData
    }
}

export interface EvaluateSingleMessageResponse {
    exito: boolean
    interaction_id: number
    proveedor: string
    relevancia: number
    sentimiento: string
    sentiment_score?: number
    tema: string
    razonamiento?: string
    estado: string
    etapa_flujo: string
    mensaje?: string
}

export async function evaluateSingleMessage(
    interactionId: number,
    proveedor?: string
): Promise<EvaluateSingleMessageResponse> {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/ai/evaluate-message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interaction_id: interactionId, proveedor }),
        })
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            throw new Error(errorData.detail || `Error al evaluar mensaje (${response.status})`)
        }
        return response.json()
    } catch (error: any) {
        if (error?.message?.includes('Failed to fetch') || error?.name === 'TypeError') {
            throw new Error(
                `No se pudo conectar con el servidor (${API_BASE_URL}). Asegúrate de acceder desde http://localhost:5173/messages y que el backend esté activo en la terminal.`
            )
        }
        throw error
    }
}

export interface ChannelParticipationItem {
    channel: string
    name: string
    count: number
    percentage: number
}

export interface ChannelParticipationResponse {
    channels: ChannelParticipationItem[]
    total_messages: number
}

const DEFAULT_CHANNEL_PARTICIPATION: ChannelParticipationResponse = {
    total_messages: 0,
    channels: [
        { channel: '#general', name: 'general', count: 0, percentage: 0.0 },
        { channel: '#faq', name: 'faq', count: 0, percentage: 0.0 },
        { channel: '#pqrs', name: 'pqrs', count: 0, percentage: 0.0 },
        { channel: '#chat-egresados', name: 'chat-egresados', count: 0, percentage: 0.0 },
        { channel: '#oportunidades-laborales', name: 'oportunidades-laborales', count: 0, percentage: 0.0 },
    ],
}

export async function getChannelParticipation(): Promise<ChannelParticipationResponse> {
    try {
        const response = await fetch(`${API_BASE_URL}/api/community/channel-participation`)
        if (!response.ok) {
            return DEFAULT_CHANNEL_PARTICIPATION
        }
        const data = await response.json()
        if (!data || !Array.isArray(data.channels)) {
            return DEFAULT_CHANNEL_PARTICIPATION
        }
        return {
            total_messages: typeof data.total_messages === 'number' ? data.total_messages : 0,
            channels: data.channels.map((ch: any) => ({
                channel: ch.channel || '',
                name: ch.name || '',
                count: typeof ch.count === 'number' ? ch.count : 0,
                percentage: typeof ch.percentage === 'number' ? ch.percentage : 0.0,
            })),
        }
    } catch {
        return DEFAULT_CHANNEL_PARTICIPATION
    }
}


