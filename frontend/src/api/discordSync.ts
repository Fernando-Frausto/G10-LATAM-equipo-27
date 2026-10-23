import { apiRequest } from './client'

export interface DiscordSyncParams {
  limite_por_canal?: number
  asincrono?: boolean
}

export interface DiscordSyncResponse {
  exito: boolean
  total_recibidas: number
  guardadas_nuevas: number
  repetidas_omitidas: number
  vacias_omitidas: number
  periodo_referencia: string
  mensaje: string
  detail?: string
  asincrono?: boolean
  en_segundo_plano?: boolean
}

export interface DiscordRecoverMessagePayload {
  canal_id: string
  message_id: string
  autor: string
  texto: string
  fecha: string
  canal?: string
}

export type DiscordRecoverItem = DiscordRecoverMessagePayload

export interface DiscordRecoverPayload {
  mensajes: DiscordRecoverMessagePayload[]
}

export interface DiscordRecoverResponse {
  exito: boolean
  guardados_nuevos: number
  repetidos_omitidos: number
  mensaje: string
}

/**
 * Sincroniza mensajes recientes de Discord hacia Supabase y la base local SQLite.
 */
export async function syncDiscord(
  paramsOrLimit?: number | DiscordSyncParams,
  options?: { signal?: AbortSignal },
): Promise<DiscordSyncResponse> {
  const limite =
    typeof paramsOrLimit === 'number'
      ? paramsOrLimit
      : paramsOrLimit?.limite_por_canal

  const asincrono =
    typeof paramsOrLimit === 'object' && paramsOrLimit?.asincrono !== undefined
      ? paramsOrLimit.asincrono
      : true

  const body = JSON.stringify({
    ...(limite !== undefined ? { limite_por_canal: limite } : {}),
    asincrono,
  })

  return (await apiRequest('/api/v1/discord/sync', {
    method: 'POST',
    body,
    signal: options?.signal,
  })) as DiscordSyncResponse
}

/**
 * Recupera selectivamente mensajes históricos inspeccionados de Discord y los inserta como pendientes.
 */
export async function recoverDiscordMessages(
  mensajesOrPayload: DiscordRecoverMessagePayload[] | DiscordRecoverPayload,
): Promise<DiscordRecoverResponse> {
  const payload: DiscordRecoverPayload = Array.isArray(mensajesOrPayload)
    ? { mensajes: mensajesOrPayload }
    : mensajesOrPayload

  return (await apiRequest('/api/v1/discord/recover', {
    method: 'POST',
    body: JSON.stringify(payload),
  })) as DiscordRecoverResponse
}
