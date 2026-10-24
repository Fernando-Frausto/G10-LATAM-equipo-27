import { Component, type ErrorInfo, type ReactNode } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface Props {
    children: ReactNode
    fallback?: ReactNode
}

interface State {
    hasError: boolean
    error: Error | null
}

export class LazyRouteErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
    }

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error }
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('LazyRouteErrorBoundary capturó un fallo al cargar la ruta:', error, errorInfo)
    }

    private handleRetry = () => {
        // Forzar recarga de ventana para reintentar la descarga de chunks dinámicos tras corte de red
        window.location.reload()
    }

    public render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback
            }

            return (
                <div
                    role="alert"
                    className="my-8 mx-auto max-w-lg rounded-2xl border border-slate-200 bg-white p-6 shadow-sm text-center sm:p-8"
                >
                    <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-50 text-[#FF7400]">
                        <AlertCircle className="h-7 w-7" />
                    </div>

                    <h2 className="mt-4 text-lg font-bold text-[#080A27]">
                        Error al cargar la sección
                    </h2>

                    <p className="mt-2 text-sm text-slate-600 leading-relaxed">
                        Se produjo un inconveniente de red al descargar los componentes de esta vista.
                        Esto suele ocurrir ante cortes breves de conexión o actualizaciones de la plataforma.
                    </p>

                    <div className="mt-6 flex justify-center">
                        <button
                            type="button"
                            onClick={this.handleRetry}
                            className="inline-flex items-center gap-2 rounded-xl bg-[#080A27] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-[#FF7400] focus:outline-none focus:ring-2 focus:ring-[#FF7400] focus:ring-offset-2 active:scale-95 cursor-pointer"
                        >
                            <RefreshCw className="h-4 w-4" />
                            Reintentar carga
                        </button>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}

export default LazyRouteErrorBoundary
