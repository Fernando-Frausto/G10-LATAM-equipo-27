import { useEffect, useState } from 'react'
import {
  getChannelParticipation,
  type ChannelParticipationItem,
} from '../api/communityLive'

const CANONICAL_CHANNELS = [
  '#general',
  '#faq',
  '#pqrs',
  '#chat-egresados',
  '#oportunidades-laborales',
]

function ChannelParticipation() {
  const [channels, setChannels] = useState<ChannelParticipationItem[]>([
    { channel: '#general', name: 'general', count: 0, percentage: 0.0 },
    { channel: '#faq', name: 'faq', count: 0, percentage: 0.0 },
    { channel: '#pqrs', name: 'pqrs', count: 0, percentage: 0.0 },
    { channel: '#chat-egresados', name: 'chat-egresados', count: 0, percentage: 0.0 },
    { channel: '#oportunidades-laborales', name: 'oportunidades-laborales', count: 0, percentage: 0.0 },
  ])

  useEffect(() => {
    let isMounted = true

    getChannelParticipation()
      .then((data) => {
        if (!isMounted) return
        if (data && Array.isArray(data.channels) && data.channels.length > 0) {
          const channelsMap = new Map(
            data.channels.map((ch) => [ch.channel.toLowerCase(), ch])
          )
          const ordered = CANONICAL_CHANNELS.map((chName) => {
            return (
              channelsMap.get(chName.toLowerCase()) || {
                channel: chName,
                name: chName.replace(/^#/, ''),
                count: 0,
                percentage: 0.0,
              }
            )
          })
          setChannels(ordered)
        }
      })
      .catch(() => {
        // Fallback silencioso preserva los 6 canales en 0.0%
      })

    return () => {
      isMounted = false
    }
  }, [])

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5">
        <h3 className="flex items-center text-base font-bold text-slate-900">
          <span className="mr-1.5 font-bold text-orange-500">#</span>
          Participación por canal
        </h3>
        <p className="mt-0.5 text-xs text-slate-500">
          Distribución de mensajes registrados en los cinco canales de Discord
        </p>
      </div>

      <div className="space-y-4">
        {channels.map((item) => {
          const hasCount = item.count > 0 && item.percentage > 0
          const safePercentage = hasCount ? Math.min(item.percentage, 100) : 0

          return (
            <div key={item.channel} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">
                  {item.channel}
                </span>
                <span className="font-medium text-slate-500">
                  {item.percentage.toFixed(1)}% · {item.count}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-orange-500 transition-all duration-500 ease-out"
                  style={{ width: `${safePercentage}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ChannelParticipation
