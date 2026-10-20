import {
    BarChart3,
    CloudUpload,
    Home,
    LogOut,
    MessageSquare,
    WandSparkles,
    X,
} from 'lucide-react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState, type ReactNode } from 'react'
import { clearSession, getUser } from '../api/session'

interface SidebarItemProps {
    to: string
    icon: ReactNode
    label: string
    badge?: number | null
    onNavigate?: () => void
}

interface SidebarProps {
    isOpen?: boolean
    onClose?: () => void
}

interface SidebarMessagesApiResponse {
    total?: number
    messages?: Array<{
        message?: {
            interaction_id?: number
        }
        analysis?: {
            workflow_stage?: string
            relevance?: number
            curation_status?: string
            is_published?: boolean
        }
    }>
}

/**
 * Isotipo vectorial oficial de CloudEdTech diseñado por Cristian
 * (variante para fondo oscuro #080A27 y variante para fondo claro #0F172A).
 */
export function CloudEdTechBrandLogo({
    variant = 'dark',
    className = 'h-full w-full object-contain',
}: {
    variant?: 'dark' | 'light'
    className?: string
}) {
    if (variant === 'light') {
        /* Basado en assets/logo-dark.svg para encabezados móviles claros */
        return (
            <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 140 100"
                fill="none"
                className={className}
                role="img"
                aria-label="CloudEdTech"
            >
                <circle cx="28" cy="62" r="14" fill="#0F172A" />
                <circle cx="28" cy="62" r="6" fill="#FFFFFF" />
                <path
                    d="M 38 56 C 46 44 58 36 72 36 C 78 36 84 39 88 44 L 66 66 C 62 70 56 73 50 73 C 40 73 32 68 28 62"
                    fill="#0F172A"
                />
                <circle cx="72" cy="34" r="18" fill="#0F172A" />
                <circle cx="72" cy="34" r="8" fill="#FFFFFF" />
                <path
                    d="M 72 34 L 102 34 C 114 34 124 44 124 56 C 124 68 114 78 102 78 L 62 78 C 58 78 54 75 54 71 C 54 67 58 64 62 64 L 102 64 C 106 64 110 60 110 56 C 110 52 106 48 102 48 L 84 48 Z"
                    fill="#FF7400"
                />
                <circle cx="102" cy="56" r="6" fill="#0F172A" />
                <polygon
                    points="102,12 118,28 110,28 110,40 94,40 94,28 86,28"
                    fill="#FF7400"
                />
            </svg>
        )
    }

    /* Basado en assets/logo.svg para sidebar oscuro y login */
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 140 100"
            fill="none"
            className={className}
            role="img"
            aria-label="CloudEdTech"
        >
            <rect width="140" height="100" rx="18" fill="#080A27" />
            <circle cx="28" cy="62" r="14" fill="#FFFFFF" />
            <circle cx="28" cy="62" r="6" fill="#080A27" />
            <path
                d="M 38 56 C 46 44 58 36 72 36 C 78 36 84 39 88 44 L 66 66 C 62 70 56 73 50 73 C 40 73 32 68 28 62"
                fill="#FFFFFF"
            />
            <circle cx="72" cy="34" r="18" fill="#FFFFFF" />
            <circle cx="72" cy="34" r="8" fill="#080A27" />
            <path
                d="M 72 34 L 102 34 C 114 34 124 44 124 56 C 124 68 114 78 102 78 L 62 78 C 58 78 54 75 54 71 C 54 67 58 64 62 64 L 102 64 C 106 64 110 60 110 56 C 110 52 106 48 102 48 L 84 48 Z"
                fill="#FF7400"
            />
            <circle cx="102" cy="56" r="6" fill="#FFFFFF" />
            <polygon
                points="102,12 118,28 110,28 110,40 94,40 94,28 86,28"
                fill="#FF7400"
            />
        </svg>
    )
}

function SidebarItem({
    to,
    icon,
    label,
    badge,
    onNavigate,
}: SidebarItemProps) {
    const hasValidBadge =
        typeof badge === 'number' && Number.isFinite(badge) && badge >= 0

    return (
        <NavLink
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
                `flex w-full items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition ${
                    isActive
                        ? 'bg-[#FF7400] text-white shadow-sm'
                        : 'text-slate-300 hover:bg-slate-800/90 hover:text-white'
                }`
            }
        >
            {({ isActive }) => (
                <>
                    <span className="shrink-0">
                        {icon}
                    </span>

                    <span className="min-w-0 flex-1 truncate">
                        {label}
                    </span>

                    {hasValidBadge && (
                        <span
                            className={`ml-auto shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold tabular-nums ${
                                isActive
                                    ? 'bg-white/20 text-white'
                                    : 'bg-slate-800 text-orange-300'
                            }`}
                        >
                            {badge.toLocaleString('es-CL')}
                        </span>
                    )}
                </>
            )}
        </NavLink>
    )
}

function Sidebar({
    isOpen = false,
    onClose,
}: SidebarProps) {
    const navigate = useNavigate()
    const location = useLocation()
    const user = getUser()

    const [ingestionCount, setIngestionCount] = useState<number | null>(null)
    const [readyForCopyCount, setReadyForCopyCount] = useState<number | null>(null)

    useEffect(() => {
        const controller = new AbortController()

        const loadSidebarCounts = async () => {
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

                if (!response.ok) return

                const data: SidebarMessagesApiResponse = await response.json()
                if (controller.signal.aborted) return

                const totalMessages =
                    typeof data.total === 'number' && Number.isFinite(data.total)
                        ? data.total
                        : Array.isArray(data.messages)
                        ? data.messages.length
                        : null

                const readyCount = Array.isArray(data.messages)
                    ? data.messages.filter((item) => {
                          const analysis = item?.analysis
                          if (!analysis) return false
                          const workflow_stage = analysis.workflow_stage
                          const relevance = Number(analysis.relevance ?? 0)
                          const curation_status = analysis.curation_status
                          const is_published = Boolean(analysis.is_published)
                          return (
                              (workflow_stage === 'en_redaccion' ||
                                  workflow_stage === 'en_analisis') &&
                              relevance >= 70 &&
                              curation_status !== 'discarded' &&
                              !is_published
                          )
                      }).length
                    : null

                setIngestionCount(totalMessages)
                setReadyForCopyCount(readyCount)
            } catch {
                /* Degradación limpia y silenciosa sin romper la navegación */
            }
        }

        void loadSidebarCounts()

        return () => controller.abort()
    }, [location.pathname])

    const roleLabels: Record<string, string> = {
        admin: 'Administrador',
        community_manager: 'Community Manager',
        reviewer: 'Revisor',
    }

    const roleLabel = user?.role
        ? roleLabels[user.role] ?? user.role
        : 'Sin rol'

    const handleLogout = () => {
        clearSession()
        onClose?.()
        navigate('/login', { replace: true })
    }

    const handleNavigate = () => {
        onClose?.()
    }

    return (
        <>
            {/* Fondo oscuro para móvil */}
            <div
                aria-hidden="true"
                onClick={onClose}
                className={`fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-[1px] transition-opacity duration-300 lg:hidden ${
                    isOpen
                        ? 'pointer-events-auto opacity-100'
                        : 'pointer-events-none opacity-0'
                }`}
            />

            {/* Sidebar */}
            <aside
                className={`fixed inset-y-0 left-0 z-50 flex h-dvh w-64 flex-col overflow-hidden bg-slate-950 text-white shadow-xl transition-transform duration-300 ease-in-out lg:z-40 lg:translate-x-0 lg:shadow-none ${
                    isOpen
                        ? 'translate-x-0'
                        : '-translate-x-full'
                }`}
            >
                {/* Identidad CloudEdTech */}
                <div className="flex h-20 shrink-0 items-center border-b border-slate-800 px-5">
                    <div className="mr-2.5 flex h-12 w-14 shrink-0 items-center justify-center">
                        <CloudEdTechBrandLogo variant="dark" />
                    </div>

                    <div className="min-w-0 flex-1">
                        <h1 className="text-lg font-bold leading-none tracking-tight">
                            <span className="text-white">
                                Cloud
                            </span>
                            <span className="text-[#FF7400]">
                                Ed
                            </span>
                            <span className="text-white">
                                Tech
                            </span>
                        </h1>

                        <p className="mt-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                            {'EDUCATION & TECHNOLOGY'}
                        </p>
                    </div>

                    {/* Cerrar menú en móvil */}
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Cerrar menú"
                        className="ml-2 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-white lg:hidden"
                    >
                        <X size={19} />
                    </button>
                </div>

                {/* Navegación con scroll independiente */}
                <nav className="min-h-0 flex-1 overflow-y-auto px-4 py-5">
                    <div className="mb-3 flex items-center justify-between px-3">
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                            Principal
                        </p>
                        <span className="c-live text-emerald-400">
                            <span className="c-live__dot" />
                            <span>En vivo</span>
                        </span>
                    </div>

                    <div className="space-y-2">
                        <SidebarItem
                            to="/dashboard"
                            icon={<Home size={18} />}
                            label="Dashboard"
                            onNavigate={handleNavigate}
                        />

                        <SidebarItem
                            to="/messages"
                            icon={<MessageSquare size={18} />}
                            label="Ingesta de mensajes"
                            badge={ingestionCount}
                            onNavigate={handleNavigate}
                        />

                        <SidebarItem
                            to="/analytics"
                            icon={<BarChart3 size={18} />}
                            label="Análisis"
                            onNavigate={handleNavigate}
                        />

                        <SidebarItem
                            to="/content"
                            icon={<WandSparkles size={18} />}
                            label="Redacción de contenidos"
                            badge={readyForCopyCount}
                            onNavigate={handleNavigate}
                        />

                        <SidebarItem
                            to="/oci-storage"
                            icon={<CloudUpload size={18} />}
                            label="Informes y Almacenamiento"
                            onNavigate={handleNavigate}
                        />
                    </div>
                </nav>

                {/* Zona inferior siempre visible */}
                <div className="shrink-0 border-t border-slate-800 bg-slate-950">
                    <div className="px-4 pt-3">
                        <button
                            type="button"
                            onClick={handleLogout}
                            className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-slate-300 transition-colors hover:bg-slate-800 hover:text-orange-400"
                        >
                            <LogOut className="h-4 w-4 shrink-0" />
                            <span>Cerrar sesión</span>
                        </button>
                    </div>

                    {/* Usuario */}
                    <div className="p-4 pt-2">
                        <div className="flex items-center gap-3 rounded-lg p-2">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#FF7400] text-sm font-semibold text-white">
                                {user
                                    ? `${user.first_name?.charAt(0) ?? ''}${user.last_name?.charAt(0) ?? ''}`.toUpperCase()
                                    : 'U'}
                            </div>

                            <div className="min-w-0">
                                <p className="truncate text-sm font-medium text-white">
                                    {user
                                        ? `${user.first_name} ${user.last_name}`
                                        : 'Usuario'}
                                </p>

                                <p className="truncate text-xs text-slate-400">
                                    {roleLabel}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </aside>
        </>
    )
}

export default Sidebar