export default function RouteLoadingFallback() {
    return (
        <div
            role="status"
            aria-live="polite"
            className="flex min-h-[400px] w-full flex-col items-center justify-center p-8 transition-opacity duration-200"
        >
            <div className="relative flex items-center justify-center">
                {/* Anillo de pulso exterior con paleta CloudEdTech */}
                <div className="h-12 w-12 rounded-full border-2 border-slate-200 animate-pulse" />
                {/* Spinner activo con acento CloudEdTech */}
                <div className="absolute h-12 w-12 animate-spin rounded-full border-2 border-transparent border-t-[#FF7400] border-r-[#080A27]" />
                {/* Punto central institucional */}
                <div className="absolute h-3 w-3 rounded-full bg-[#080A27]" />
            </div>
            <p className="mt-4 text-xs font-semibold uppercase tracking-[0.15em] text-slate-500">
                Cargando sección...
            </p>
        </div>
    )
}
