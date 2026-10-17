import { useEffect, useState } from 'react'
import { Search, X, RefreshCcw, Inbox } from 'lucide-react'
import type { DiscordPublishingChannel } from '../api/motorDiscordPublishing'
import {
  getDiscordRecoveryPreview,
  type DiscordRecoveryMessage,
  type DiscordRecoveryResponse,
} from '../api/discordRecovery'
import {
  recoverDiscordMessages,
  type DiscordRecoverMessagePayload,
} from '../api/discordSync'

type Props = {
  open: boolean
  onClose: () => void
  channels: DiscordPublishingChannel[]
  onRecovered?: () => void
}

export default function RecoverDiscordMessagesModal({
  open,
  onClose,
  channels,
  onRecovered,
}: Props) {
  const [search, setSearch] = useState('')
  const [channel, setChannel] = useState('')
  const [period, setPeriod] = useState('7')
  const [onlyPending, setOnlyPending] = useState(true)
  const [page, setPage] = useState(1)
  const [result, setResult] = useState<DiscordRecoveryResponse | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [isRecovering, setIsRecovering] = useState(false)
  const [recoveryNotice, setRecoveryNotice] = useState<{
    type: 'success' | 'error'
    message: string
  } | null>(null)

  useEffect(() => {
    if (!open) return

    let cancelled = false
    setLoading(true)
    setError('')

    const delay = window.setTimeout(() => {
      getDiscordRecoveryPreview({
        canal_id: channel,
        buscar: search,
        dias: Number(period),
        solo_pendientes: onlyPending,
        pagina: page,
      })
        .then((data) => {
          if (!cancelled) setResult(data)
        })
        .catch((err: unknown) => {
          if (!cancelled) {
            setResult(null)
            setError(
              err instanceof Error ? err.message : 'No se pudo consultar Discord',
            )
          }
        })
        .finally(() => {
          if (!cancelled) setLoading(false)
        })
    }, 350)

    return () => {
      cancelled = true
      window.clearTimeout(delay)
    }
  }, [open, search, channel, period, onlyPending, page, refresh])

  function handleClose() {
    setSelected([])
    setRecoveryNotice(null)
    onClose()
  }

  function changeFilters(action: () => void) {
    action()
    setPage(1)
    setSelected([])
    setRecoveryNotice(null)
  }

  function toggleMessage(item: DiscordRecoveryMessage) {
    if (item.recuperado || isRecovering) return
    const key = `${item.channel_id}:${item.message_id}`
    setSelected((previous) =>
      previous.includes(key)
        ? previous.filter((value) => value !== key)
        : [...previous, key],
    )
  }

  async function handleRecoverSelected() {
    if (selected.length === 0 || isRecovering) return

    const selectedMessages = (result?.mensajes ?? []).filter((item) =>
      selected.includes(`${item.channel_id}:${item.message_id}`),
    )

    if (selectedMessages.length === 0) return

    const payload: DiscordRecoverMessagePayload[] = selectedMessages.map((msg) => ({
      canal_id: msg.channel_id,
      message_id: msg.message_id,
      autor: msg.autor,
      texto: msg.texto,
      fecha: msg.fecha,
      canal: msg.canal,
    }))

    setIsRecovering(true)
    setRecoveryNotice(null)

    try {
      const response = await recoverDiscordMessages(payload)

      setResult((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          mensajes: prev.mensajes.map((item) => {
            const key = `${item.channel_id}:${item.message_id}`
            if (selected.includes(key)) {
              return { ...item, recuperado: true }
            }
            return item
          }),
        }
      })

      setSelected([])
      setRecoveryNotice({
        type: 'success',
        message:
          response.mensaje ||
          `Se recuperaron ${response.guardados_nuevos} mensajes exitosamente.`,
      })
      onRecovered?.()
    } catch (err: unknown) {
      setRecoveryNotice({
        type: 'error',
        message:
          err instanceof Error
            ? err.message
            : 'No fue posible recuperar los mensajes de Discord.',
      })
    } finally {
      setIsRecovering(false)
    }
  }

  const messages = result?.mensajes ?? []
  const totalPages = result
    ? Math.max(1, Math.ceil(result.total / result.tamano_pagina))
    : 1

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4"
      role="presentation"
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="recover-discord-title"
        className="flex max-h-[90vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-slate-200 p-5">
          <div>
            <h2 id="recover-discord-title" className="text-xl font-bold text-slate-900">
              Recuperar mensajes de Discord
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Filtra y selecciona los mensajes que deseas incorporar.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Cerrar ventana"
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"
          >
            <X size={20} />
          </button>
        </header>

        <div className="space-y-4 overflow-y-auto p-5">
          <div className="relative">
            <Search size={17} className="absolute left-3 top-3 text-slate-400" />
            <input
              value={search}
              onChange={(event) =>
                changeFilters(() => setSearch(event.target.value))
              }
              placeholder="Buscar por texto, autor o palabra clave..."
              className="w-full rounded-xl border border-slate-200 py-2.5 pl-10 pr-3 text-sm"
            />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="space-y-1 text-xs font-semibold text-slate-600">
              Canal de Discord
              <select
                value={channel}
                onChange={(event) =>
                  changeFilters(() => setChannel(event.target.value))
                }
                className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-sm"
              >
                <option value="">Todos los canales</option>
                {channels.map((item) => (
                  <option key={item.id} value={item.id}>
                    #{item.nombre}
                  </option>
                ))}
              </select>
            </label>

            <label className="space-y-1 text-xs font-semibold text-slate-600">
              Período
              <select
                value={period}
                onChange={(event) =>
                  changeFilters(() => setPeriod(event.target.value))
                }
                className="w-full rounded-xl border border-slate-200 bg-white p-2.5 text-sm"
              >
                <option value="1">Últimas 24 horas</option>
                <option value="7">Últimos 7 días</option>
                <option value="30">Últimos 30 días</option>
                <option value="all" disabled>
                  Todo el historial (próximamente)
                </option>
              </select>
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={onlyPending}
              onChange={(event) =>
                changeFilters(() => setOnlyPending(event.target.checked))
              }
              className="h-4 w-4 rounded"
            />
            Mostrar solo mensajes no recuperados
          </label>

          {recoveryNotice && (
            <div
              role="alert"
              className={`flex items-center justify-between rounded-xl p-3.5 text-sm ${
                recoveryNotice.type === 'success'
                  ? 'border border-emerald-200 bg-emerald-50 text-emerald-900'
                  : 'border border-red-200 bg-red-50 text-red-900'
              }`}
            >
              <span>{recoveryNotice.message}</span>
              <button
                type="button"
                onClick={() => setRecoveryNotice(null)}
                className="ml-3 text-xs font-semibold underline hover:opacity-80"
              >
                Cerrar
              </button>
            </div>
          )}

          {loading ? (
            <div className="rounded-xl bg-slate-50 p-6 text-center text-sm text-slate-600">
              Consultando mensajes reales de Discord...
            </div>
          ) : error ? (
            <div role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">
              {error}
              <button
                type="button"
                onClick={() => setRefresh((value) => value + 1)}
                className="ml-3 font-semibold underline"
              >
                Reintentar
              </button>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex min-h-40 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
              <Inbox size={30} className="mb-3 text-slate-400" />
              <p className="font-semibold text-slate-700">
                No se encontraron mensajes con estos filtros
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {messages.map((item) => {
                const key = `${item.channel_id}:${item.message_id}`
                return (
                  <label
                    key={key}
                    className={`flex cursor-pointer gap-3 rounded-xl border border-slate-200 p-3 hover:bg-slate-50 ${
                      item.recuperado ? 'bg-slate-50/70 opacity-80 cursor-default' : ''
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selected.includes(key)}
                      disabled={item.recuperado || isRecovering}
                      onChange={() => toggleMessage(item)}
                      className="mt-1 h-4 w-4"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        <strong className="text-slate-800">{item.autor}</strong>
                        <span>#{item.canal}</span>
                        <span>{new Date(item.fecha).toLocaleString('es-CO')}</span>
                        {item.recuperado && (
                          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                            Ya recuperado
                          </span>
                        )}
                      </div>
                      <p className="mt-1 whitespace-pre-wrap break-words text-sm text-slate-700">
                        {item.texto}
                      </p>
                    </div>
                  </label>
                )
              })}
            </div>
          )}

          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>
              {result ? `${result.total} coincidencias en el historial inspeccionado` : ''}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={loading || page <= 1}
                onClick={() => {
                  setPage((value) => value - 1)
                  setSelected([])
                }}
                className="rounded-lg border px-3 py-1 disabled:opacity-40"
              >
                Anterior
              </button>
              <span>{page} / {totalPages}</span>
              <button
                type="button"
                disabled={loading || page >= totalPages}
                onClick={() => {
                  setPage((value) => value + 1)
                  setSelected([])
                }}
                className="rounded-lg border px-3 py-1 disabled:opacity-40"
              >
                Siguiente
              </button>
            </div>
          </div>
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 p-5">
          <span className="text-xs text-slate-500">
            {selected.length} mensajes seleccionados
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={isRecovering}
              className="rounded-xl border border-slate-200 px-4 py-2 text-sm font-semibold hover:bg-slate-50 disabled:opacity-50"
            >
              Cancelar
            </button>
            <button
              type="button"
              disabled={selected.length === 0 || isRecovering}
              onClick={handleRecoverSelected}
              className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <RefreshCcw size={15} className={isRecovering ? 'animate-spin' : ''} />
              {isRecovering ? 'Recuperando...' : 'Recuperar seleccionados'}
            </button>
          </div>
        </footer>
      </section>
    </div>
  )
}
