import { apiRequest } from './client'

export type ContentPlatform = 'linkedin' | 'x' | 'discord'

export interface CreateContentDraftRequest {
  interaccion_id?: number
  plataforma: ContentPlatform
  titulo: string
  contenido: string
  llamada_accion?: string | null
  hashtags?: string[]
  tono?: string
  tipo_contenido?: string
}

export interface ContentDraftResponse {
  id: number
  estado: string
  message: string
}

export interface RegenerateContentRequest {
  texto: string
  canal: string
  formato: ContentPlatform
  tono?: string
  proveedor?: string
}

export interface RegenerateContentResponse {
  formato: ContentPlatform
  titulo: string
  contenido: string
  llamada_accion: string
  hashtags: string[]
}

export async function regenerateContent(
  solicitud: RegenerateContentRequest,
): Promise<RegenerateContentResponse> {
  const data = (await apiRequest(
    '/api/v1/content-workflow/regenerate',
    {
      method: 'POST',
      body: JSON.stringify({
        ...solicitud,
        tono: solicitud.tono ?? 'profesional',
      }),
    },
  )) as RegenerateContentResponse

  if (
    !data ||
    data.formato !== solicitud.formato ||
    typeof data.contenido !== 'string' ||
    !data.contenido.trim()
  ) {
    throw new Error(
      'El Motor IA no devolvió un contenido válido para el formato solicitado.',
    )
  }

  if (solicitud.formato === 'x' && [...data.contenido].length > 280) {
    throw new Error(
      'El Motor IA generó un texto que supera los 280 caracteres de X.',
    )
  }

  return data
}


export async function createContentDraft(
  draft: CreateContentDraftRequest,
): Promise<ContentDraftResponse> {
  const response = (await apiRequest(
    '/api/v1/content-workflow/drafts',
    {
      method: 'POST',
      body: JSON.stringify(draft),
    },
  )) as ContentDraftResponse

  if (
    !Number.isInteger(response.id) ||
    response.id <= 0 ||
    response.estado !== 'pendiente_revision'
  ) {
    throw new Error(
      'El servidor no confirmó correctamente el guardado del borrador.',
    )
  }

  return response
}

export async function generateComplaintResponse(
  interaccionId: number,
  proveedor?: string,
): Promise<{ respuesta: string; proveedor_usado?: string }> {
  return (await apiRequest(
    '/api/v1/content-workflow/complaints/generate-response',
    {
      method: 'POST',
      body: JSON.stringify({
        interaccion_id: interaccionId,
        ...(proveedor ? { proveedor } : {}),
      }),
    },
  )) as { respuesta: string; proveedor_usado?: string }
}


export interface PublishComplaintResponseRequest {
  interaccion_id: number
  respuesta: string
  confirmado: true
}

export interface PublishComplaintResponseResult {
  estado: 'publicado'
  interaccion_id: number
  discord_message_id: string
  channel_id: string
}

export async function publishComplaintResponse(
  solicitud: PublishComplaintResponseRequest,
): Promise<PublishComplaintResponseResult> {
  if (!Number.isSafeInteger(solicitud.interaccion_id) || solicitud.interaccion_id <= 0) {
    throw new Error('La interacción seleccionada no es válida.')
  }

  const respuesta = solicitud.respuesta.trim()

  if (!respuesta || respuesta.length > 2000) {
    throw new Error('La respuesta debe contener entre 1 y 2000 caracteres.')
  }

  return (await apiRequest(
    '/api/v1/content-workflow/complaints/publish-response',
    {
      method: 'POST',
      body: JSON.stringify({
        interaccion_id: solicitud.interaccion_id,
        respuesta,
        confirmado: true,
      }),
    },
  )) as PublishComplaintResponseResult
}


export interface ComplaintPublishPreview {
  interaccion_id: number
  guild_id: string
  channel_id: string
  channel_name: string
  source_message_id: string
  author: string
  original_content: string
  ready: boolean
  detail?: string
}

export async function getComplaintPublishPreview(
  interaccionId: number,
): Promise<ComplaintPublishPreview> {
  if (!Number.isSafeInteger(interaccionId) || interaccionId <= 0) {
    throw new Error('La interacción seleccionada no es válida.')
  }

  const data = (await apiRequest(
    `/api/v1/content-workflow/complaints/${interaccionId}/publish-preview`,
    {
      method: 'GET',
    },
  )) as ComplaintPublishPreview

  if (!data || data.interaccion_id !== interaccionId) {
    throw new Error('No se pudo verificar el destino de Discord.')
  }

  if (
    data.ready &&
    (!data.channel_id || !data.channel_name || !data.source_message_id)
  ) {
    throw new Error('No se pudo verificar el destino de Discord.')
  }

  return data
}

export interface PublishedComplaintIdsResponse {
  interaction_ids: number[]
}

export async function getPublishedComplaintIds(): Promise<number[]> {
  const data = (await apiRequest(
    '/api/v1/content-workflow/complaints/published-responses',
    { method: 'GET' },
  )) as PublishedComplaintIdsResponse

  if (
    !data ||
    !Array.isArray(data.interaction_ids) ||
    !data.interaction_ids.every(
      (id) => Number.isSafeInteger(id) && id > 0,
    )
  ) {
    throw new Error(
      'El servidor devolvió una lista de publicaciones no válida.',
    )
  }

  return data.interaction_ids
}

export interface AnnouncementWebhookStatus {
  configured: boolean
  channel_hint: string
  max_characters_recommended: number
  max_characters_limit: number
  warning: string | null
  channels?: Array<{ id: string; name: string }>
}

export interface AnnouncementGenerateResponse {
  anuncio_generado: string
  caracteres: number
  borrador_original: string
  modelo_usado: string
}

export interface AnnouncementPublishResponse {
  estado: string
  id_contenido: number | null
  fecha_publicacion: string
  caracteres: number
  canal_destino?: string
  mensaje?: string
}

export async function getAnnouncementWebhookStatus(): Promise<AnnouncementWebhookStatus> {
  return (await apiRequest('/api/v1/content-workflow/announcements/status', {
    method: 'GET',
  })) as AnnouncementWebhookStatus
}

export async function generateAnnouncement(
  borrador: string,
  proveedor?: string,
): Promise<AnnouncementGenerateResponse> {
  return (await apiRequest('/api/v1/content-workflow/announcements/generate', {
    method: 'POST',
    body: JSON.stringify({ borrador, proveedor }),
  })) as AnnouncementGenerateResponse
}

export async function publishAnnouncement(
  contenido: string,
  confirmado: boolean = true,
  channel_id?: string,
): Promise<AnnouncementPublishResponse> {
  return (await apiRequest('/api/v1/content-workflow/announcements/publish', {
    method: 'POST',
    body: JSON.stringify({ contenido, confirmado, channel_id }),
  })) as AnnouncementPublishResponse
}


// ==============================================================================
// Spec 015: Integración del Pipeline Mototradis MVP de Enoc (Frontend API Client)
// ==============================================================================

export type AIProviderOption =
  | 'auto'
  | 'Google Gemini'
  | 'Groq'
  | 'Google Gemma 4'
  | 'Groq (Llama 3.3)'
  | 'Google Gemini Flash Lite'
  | string

export interface MototradisModelosUtilizados {
  orquestador: string
  linkedin: string
  x: string
  discord: string
  pqrs?: string
  masivo?: string
  [key: string]: string | undefined
}

export interface MototradisChannelDraft {
  titulo?: string
  texto_copy?: string
  copy_tono?: string
  newsletter?: { destaque?: string; resumen?: string; [key: string]: any }
  faq?: { sugerencia?: string; respuesta?: string; [key: string]: any }
  canal_seleccionado?: string
  [key: string]: any
}

export interface MototradisBorradoresUI {
  linkedin?: string | MototradisChannelDraft
  x?: string | MototradisChannelDraft
  discord?: string | MototradisChannelDraft
  [key: string]: any
}

export interface MototradisCheckpointState {
  thread_id?: string
  id_mensaje: number
  interaccion_id?: number
  has_checkpoint: boolean
  estado_pipeline: string
  estado_revision?: string
  rutas_activas?: string[]
  borradores_ui: MototradisBorradoresUI
  intentos_generacion?: number
  modelos_utilizados: MototradisModelosUtilizados
  resultados_canales?: Record<string, any>
  updated_at?: string | null
  copys_generados?: Record<string, any>
  aviso_fallback?: string | null
  fallbacks_usados?: string[]
  is_published?: boolean
  plataformas_publicadas?: string[]
}

export type MototradisCheckpointResponse = MototradisCheckpointState
export type MototradisExecuteResponse = MototradisCheckpointState

export interface MototradisHitlDecisionResponse {
  exito: boolean
  decision: string
  estado_revision?: string
  estado_pipeline?: string
  checkpoint_limpiado?: boolean
  id_mensaje: number
  resultados_canales?: Record<
    string,
    { ok: boolean; detalle: string; estado_canal?: string; [key: string]: any }
  >
}

export type MototradisHitlResponse = MototradisHitlDecisionResponse

export interface MototradisMassResult {
  status: string
  modelo_ia: string
  procesados: number
  publicados_directo: number
  descartados: number
  limite?: number
}

export type MototradisRunMassResponse = MototradisMassResult

export async function getMototradisCheckpoint(
  idMensaje: number,
): Promise<MototradisCheckpointState> {
  return (await apiRequest(
    `/api/v1/content-workflow/checkpoint/${idMensaje}`,
    {
      method: 'GET',
    },
  )) as MototradisCheckpointState
}

export async function executeMototradisPipeline(
  idMensaje: number,
  proveedor?: AIProviderOption,
): Promise<MototradisCheckpointState> {
  return (await apiRequest('/api/v1/content-workflow/execute-pipeline', {
    method: 'POST',
    body: JSON.stringify({
      id_mensaje: idMensaje,
      interaccion_id: idMensaje,
      proveedor,
    }),
  })) as MototradisCheckpointState
}

export async function generateMototradisChannelCopy(
  idMensaje: number,
  canal: 'linkedin' | 'x' | 'discord',
  proveedor?: AIProviderOption,
): Promise<{
  id_mensaje: number
  canal: string
  contenido: any
  borrador: any
  borradores_ui: MototradisBorradoresUI
  modelo_utilizado: string
  fallback_usado?: boolean
  aviso_fallback?: string | null
}> {
  return (await apiRequest('/api/v1/content-workflow/generate-channel', {
    method: 'POST',
    body: JSON.stringify({
      id_mensaje: idMensaje,
      interaccion_id: idMensaje,
      canal,
      proveedor,
    }),
  })) as {
    id_mensaje: number
    canal: string
    contenido: any
    borrador: any
    borradores_ui: MototradisBorradoresUI
    modelo_utilizado: string
  }
}

export const generateMototradisChannel = generateMototradisChannelCopy

export async function publishMototradisChannel(
  idMensaje: number,
  canal: 'linkedin' | 'x' | 'discord',
  texto: string,
  canalSeleccionado?: string,
  titulo?: string,
): Promise<{ canal: string; ok: boolean; detalle: string; estado_canal: string }> {
  return (await apiRequest('/api/v1/content-workflow/publish-channel', {
    method: 'POST',
    body: JSON.stringify({
      id_mensaje: idMensaje,
      interaccion_id: idMensaje,
      canal,
      texto_copy: texto,
      titulo: titulo ?? '',
      canal_seleccionado: canalSeleccionado,
    }),
  })) as { canal: string; ok: boolean; detalle: string; estado_canal: string }
}

export async function submitMototradisHitlDecision(
  idMensaje: number,
  aprobado: boolean,
  copysEditados?: Partial<Record<'linkedin' | 'x' | 'discord', any>>,
  motivoRechazo?: string,
): Promise<MototradisHitlDecisionResponse> {
  return (await apiRequest('/api/v1/content-workflow/hitl-decision', {
    method: 'POST',
    body: JSON.stringify({
      id_mensaje: idMensaje,
      interaccion_id: idMensaje,
      decision: aprobado ? 'aprobar' : 'desaprobar',
      aprobado,
      copys_editados: copysEditados,
      motivo_rechazo: motivoRechazo,
    }),
  })) as MototradisHitlDecisionResponse
}

export async function runMototradisMassProcess(
  limite: number = 10,
): Promise<MototradisMassResult> {
  return (await apiRequest('/api/v1/content-workflow/run-mass', {
    method: 'POST',
    body: JSON.stringify({ limite }),
  })) as MototradisMassResult
}

export async function getMototradisMassQueueStatus(): Promise<{
  total_en_cola: number
  criterio?: string
}> {
  return (await apiRequest('/api/v1/content-workflow/mass-queue-status', {
    method: 'GET',
  })) as { total_en_cola: number; criterio?: string }
}


export const runMototradisMassGemma = runMototradisMassProcess

