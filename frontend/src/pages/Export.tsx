import { useState } from "react";
import { Download, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";
import { fetchCommunityExportData } from "../api/communityLive";

function Export() {
    const [isExporting, setIsExporting] = useState<boolean>(false);
    const [exportStatus, setExportStatus] = useState<{ type: "success" | "fallback"; message: string } | null>(null);

    const handleExportJSON = async () => {
        if (isExporting) return;
        setIsExporting(true);
        setExportStatus(null);

        try {
            const data = await fetchCommunityExportData();
            const isLive = "interactions" in data || "export_date" in data;
            const json = JSON.stringify(data, null, 2);
            const blob = new Blob([json], { type: "application/json" });
            const url = URL.createObjectURL(blob);

            const link = document.createElement("a");
            link.href = url;
            link.download = `cloudedtech-community-data-${new Date().toISOString().slice(0, 10)}.json`;

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            URL.revokeObjectURL(url);

            setExportStatus({
                type: isLive ? "success" : "fallback",
                message: isLive
                    ? "Exportación generada exitosamente con datos en vivo desde Supabase y Motor IA."
                    : "Exportación completada usando datos locales de respaldo (modo offline/demo).",
            });
        } catch (error) {
            console.error("Error al exportar datos:", error);
            setExportStatus({
                type: "fallback",
                message: "No fue posible conectar con el servidor. Se recomienda reintentar con el motor activo.",
            });
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <div>
            {/* Encabezado */}
            <div>
                <h2 className="text-2xl font-bold text-slate-900">
                    Export
                </h2>

                <p className="mt-1 text-slate-500">
                    Exporta análisis y datos de tu comunidad.
                </p>
            </div>

            {/* Contenido */}
            <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-50 text-orange-500">
                        <Download size={20} />
                    </div>

                    <div>
                        <h3 className="font-bold text-slate-900">
                            Exportar información
                        </h3>

                        <p className="text-sm text-slate-500">
                            Genera reportes y exporta los resultados de tus análisis.
                        </p>
                    </div>
                </div>

                {exportStatus && (
                    <div
                        role="alert"
                        className={`mt-6 flex items-center gap-2 rounded-xl border p-4 text-xs font-semibold ${
                            exportStatus.type === "success"
                                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                                : "border-amber-200 bg-amber-50 text-amber-800"
                        }`}
                    >
                        {exportStatus.type === "success" ? (
                            <CheckCircle2 size={16} className="shrink-0 text-emerald-600" />
                        ) : (
                            <AlertCircle size={16} className="shrink-0 text-amber-600" />
                        )}
                        <span>{exportStatus.message}</span>
                    </div>
                )}

                <div className="mt-6 rounded-xl bg-slate-50 p-6">
                    <div className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-5 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                            <h4 className="font-semibold text-slate-900">
                                Datos de la comunidad
                            </h4>

                            <p className="mt-1 text-sm text-slate-500">
                                Exporta los datos actuales de CloudEdTech y KPIs en formato JSON.
                            </p>
                        </div>

                        <button
                            type="button"
                            disabled={isExporting}
                            onClick={handleExportJSON}
                            className="flex items-center justify-center gap-2 rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:opacity-60 disabled:cursor-not-allowed"
                        >
                            {isExporting ? (
                                <RefreshCw size={17} className="animate-spin" />
                            ) : (
                                <Download size={17} />
                            )}
                            {isExporting ? "Exportando..." : "Exportar JSON"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Export;