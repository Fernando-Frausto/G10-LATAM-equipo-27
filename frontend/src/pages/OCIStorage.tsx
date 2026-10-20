import {
    AlertTriangle,
    CheckCircle2,
    Cloud,
    CloudUpload,
    Copy,
    Download,
    Eye,
    EyeOff,
    FileJson,
    FileText,
    Filter,
    FolderOpen,
    Loader2,
    MapPin,
    RefreshCw,
    Server,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
    getOCIReports,
    getOCIStorageStatus,
    getWeeklyPeriod,
    startWeeklySync,
} from "../api/ociStorage";
import type {
    OCIReportItem,
    OCIStorageStatus,
    WeeklyPeriod,
} from "../api/ociStorage";

type FilterMode = "all" | "oci" | "local";

function computeDefaultIsoWeekLabel(): string {
    const now = new Date();
    const target = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
    const dayNr = (target.getUTCDay() + 6) % 7;
    target.setUTCDate(target.getUTCDate() - dayNr + 3);
    const firstThursday = target.valueOf();
    target.setUTCMonth(0, 1);
    if (target.getUTCDay() !== 4) {
        target.setUTCMonth(0, 1 + ((4 - target.getUTCDay() + 7) % 7));
    }
    const weekNumber = 1 + Math.ceil((firstThursday - target.valueOf()) / 604800000);
    const isoYear = target.getUTCFullYear();
    return `${isoYear}-semana-${String(weekNumber).padStart(2, "0")}`;
}

function formatBytes(bytes: number): string {
    if (!bytes || bytes <= 0) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
}

function formatDateTime(isoString?: string): string {
    if (!isoString) return "—";
    try {
        const dt = new Date(isoString);
        if (Number.isNaN(dt.getTime())) return isoString;
        return dt.toLocaleString("es-CO", {
            year: "numeric",
            month: "short",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        });
    } catch {
        return isoString;
    }
}

function OCIStorage() {
    const [weeklyPeriod, setWeeklyPeriod] = useState<WeeklyPeriod | null>(null);
    const [ociStatus, setOciStatus] = useState<OCIStorageStatus | null>(null);
    const [reports, setReports] = useState<OCIReportItem[]>([]);
    const [isLoadingReports, setIsLoadingReports] = useState<boolean>(true);
    const [selectedReport, setSelectedReport] = useState<OCIReportItem | null>(null);
    const [showJsonPreview, setShowJsonPreview] = useState<boolean>(false);
    const [copiedJson, setCopiedJson] = useState<boolean>(false);

    const [weekLabelInput, setWeekLabelInput] = useState<string>(computeDefaultIsoWeekLabel);
    const [isSyncing, setIsSyncing] = useState<boolean>(false);
    const [retryingWeek, setRetryingWeek] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<FilterMode>("all");

    const [feedbackBanner, setFeedbackBanner] = useState<{
        type: "success" | "offline" | "error";
        message: string;
    } | null>(null);

    const isWeekLabelValid = useMemo(
        () => /^\d{4}-semana-\d{2}$/.test(weekLabelInput.trim()),
        [weekLabelInput]
    );

    const loadReports = useCallback(async () => {
        setIsLoadingReports(true);
        try {
            const res = await getOCIReports();
            const list = res.reports || [];
            setReports(list);
            setSelectedReport((prev) => {
                if (prev) {
                    const updated = list.find((r) => r.semana === prev.semana);
                    return updated || prev;
                }
                return list[0] || null;
            });
        } catch (error) {
            console.error("Error cargando historial de reportes OCI:", error);
        } finally {
            setIsLoadingReports(false);
        }
    }, []);

    useEffect(() => {
        getOCIStorageStatus()
            .then((data) => {
                setOciStatus(data);
            })
            .catch((error) => {
                console.error("Error consultando OCI Storage:", error);
            });

        getWeeklyPeriod()
            .then((data) => {
                setWeeklyPeriod(data);
                const suggestedLabel = data.iso_week_label || data.semana_nombre || data.week_label;
                if (suggestedLabel && /^\d{4}-semana-\d{2}$/.test(suggestedLabel)) {
                    setWeekLabelInput(suggestedLabel);
                }
            })
            .catch((error) => {
                console.error("Error consultando el período semanal:", error);
            });

        loadReports();
    }, [loadReports]);

    const activeReport = selectedReport ?? reports[0] ?? null;

    const ociSyncedCount = useMemo(
        () => reports.filter((r) => r.subido_oci).length,
        [reports]
    );
    const localSavedCount = useMemo(
        () => reports.filter((r) => !r.subido_oci).length,
        [reports]
    );

    const filteredReports = useMemo(() => {
        if (statusFilter === "oci") {
            return reports.filter((r) => r.subido_oci);
        }
        if (statusFilter === "local") {
            return reports.filter((r) => !r.subido_oci);
        }
        return reports;
    }, [reports, statusFilter]);

    const handleDownloadJson = (item: OCIReportItem) => {
        const jsonString = JSON.stringify(item.reporte, null, 2);
        const blob = new Blob([jsonString], {
            type: "application/json;charset=utf-8",
        });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `${item.semana}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const handleCopyJson = async () => {
        if (!activeReport) return;
        try {
            await navigator.clipboard.writeText(
                JSON.stringify(activeReport.reporte, null, 2)
            );
            setCopiedJson(true);
            setTimeout(() => setCopiedJson(false), 2000);
        } catch (error) {
            console.error("No se pudo copiar el JSON:", error);
        }
    };

    const executeWeeklySync = async (targetWeek: string, isRowRetry = false) => {
        const cleanWeek = targetWeek.trim();
        if (!/^\d{4}-semana-\d{2}$/.test(cleanWeek)) {
            setFeedbackBanner({
                type: "error",
                message: "Formato inválido. Usa AAAA-semana-NN (ej. 2026-semana-42).",
            });
            return;
        }

        if (isRowRetry) {
            setRetryingWeek(cleanWeek);
        } else {
            setIsSyncing(true);
        }
        setFeedbackBanner(null);

        try {
            const response = await startWeeklySync(cleanWeek);
            const semanaRes = response.semana || cleanWeek;
            const bucketRes =
                response.bucket || ociStatus?.bucket || "communitylab-assets";
            const rutaRes =
                response.ruta_oci ||
                `activos/${semanaRes}/paquete-distribucion.json`;
            const subidoOci = Boolean(response.subido_oci);

            if (response.reporte) {
                const jsonLength = JSON.stringify(response.reporte, null, 2).length;
                const newItem: OCIReportItem = {
                    semana: semanaRes,
                    nombre_archivo: `${semanaRes}.json`,
                    tamano_bytes: jsonLength,
                    generado_en:
                        response.reporte.metadata?.generado_en ||
                        new Date().toISOString(),
                    bucket: bucketRes,
                    ruta_oci: rutaRes,
                    subido_oci: subidoOci,
                    resumen_metricas: response.reporte.resumen_metricas,
                    reporte: response.reporte,
                };
                setSelectedReport(newItem);
                setShowJsonPreview(true);
            }

            if (subidoOci) {
                setFeedbackBanner({
                    type: "success",
                    message: `🎉 Reporte ${semanaRes}.json empaquetado y subido exitosamente a Oracle Cloud (${bucketRes}/${rutaRes}).`,
                });
            } else {
                setFeedbackBanner({
                    type: "offline",
                    message: `⚠️ Modo Offline: Sin conexión activa a OCI en este entorno. Reporte generado y respaldado en reportes/${semanaRes}.json.`,
                });
            }

            await loadReports();
        } catch (error) {
            const errMsg =
                error instanceof Error
                    ? error.message
                    : "Error inesperado al generar el reporte semanal.";
            setFeedbackBanner({
                type: "error",
                message: `❌ ${errMsg}`,
            });
        } finally {
            setIsSyncing(false);
            setRetryingWeek(null);
        }
    };

    const isServiceConnected =
        ociStatus?.status === "connected" || ociStatus?.status === "ready";
    const isOciOnline = Boolean(ociStatus?.oci_configured);
    const bucketName = ociStatus?.bucket || "communitylab-assets";
    const regionName = ociStatus?.region || "mx-queretaro-1";

    return (
        <div>
            {/* Encabezado */}
            <div>
                <h2 className="text-2xl font-bold text-slate-900">
                    Informes y Almacenamiento (OCI)
                </h2>
                <p className="mt-1 text-slate-500">
                    Empaquetado de reportes semanales de comunidad, respaldo JSON y distribución hacia Oracle Cloud Infrastructure.
                </p>
            </div>

            {/* Cabecera de Estado OCI y 4 Contadores Reales (RF-01 / Spec 019 RF-08, RF-10) */}
            <div className="c-card--brand mt-8 overflow-hidden rounded-2xl bg-[#080A27] p-6 text-white shadow-sm">
                <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-start">
                    <div className="flex items-start gap-4">
                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-orange-500/15 text-orange-400">
                            <Cloud size={24} />
                        </div>

                        <div>
                            <div className="flex flex-wrap items-center gap-3">
                                <h3 className="text-lg font-bold">
                                    OCI Object Storage
                                </h3>

                                <span
                                    className={`c-live rounded-full px-3 py-1 text-xs font-semibold ${
                                        !isServiceConnected
                                            ? "bg-slate-500/20 text-slate-300"
                                            : isOciOnline
                                              ? "bg-emerald-500/15 text-emerald-300"
                                              : "bg-amber-500/15 text-amber-300"
                                    }`}
                                    role="status"
                                >
                                    <span className="c-live__dot" aria-hidden="true" />
                                    <span>
                                        {!isServiceConnected
                                            ? "Verificando..."
                                            : isOciOnline
                                              ? "Conectado a OCI (Modo Online)"
                                              : "Modo Respaldo Local / Offline"}
                                    </span>
                                </span>
                            </div>

                            <p className="mt-2 text-sm text-slate-300">
                                {ociStatus?.message ??
                                    "Consultando el estado del módulo OCI Object Storage..."}
                            </p>

                            <dl className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-slate-400">
                                <div className="inline-flex items-center gap-1.5">
                                    <MapPin size={15} className="text-orange-400" />
                                    <dt className="text-slate-400">Región:</dt>
                                    <dd className="font-mono font-semibold tabular-nums text-slate-200">
                                        {regionName}
                                    </dd>
                                </div>
                                <div className="inline-flex items-center gap-1.5">
                                    <FolderOpen size={15} className="text-orange-400" />
                                    <dt className="text-slate-400">Bucket:</dt>
                                    <dd className="font-mono font-semibold tabular-nums text-slate-200">
                                        {bucketName}
                                    </dd>
                                </div>
                                <div className="inline-flex items-center gap-1.5">
                                    <Server size={15} className="text-orange-400" />
                                    <dt className="text-slate-400">Modo:</dt>
                                    <dd className="font-mono font-semibold tabular-nums text-slate-200">
                                        {isOciOnline ? "Online (OCI)" : "Local / Offline"}
                                    </dd>
                                </div>
                            </dl>
                        </div>
                    </div>

                    <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                        <div className="flex items-center gap-2">
                            <Server size={16} className="text-orange-400" />
                            <span className="text-sm font-semibold">
                                Oracle Cloud Infrastructure
                            </span>
                        </div>
                        <p className="mt-1 font-mono text-xs tabular-nums text-slate-400">
                            {isOciOnline
                                ? `Sincronización directa activa en ${bucketName}`
                                : "Respaldo local garantizado en reportes/*.json"}
                        </p>
                    </div>
                </div>

                <div className="mt-6 grid grid-cols-2 gap-3 border-t border-white/10 pt-5 md:grid-cols-4">
                    <div className="rounded-xl bg-white/5 p-4">
                        <p className="text-xs text-slate-400">Reportes Semanales</p>
                        <p className="mt-1 text-xl font-bold tabular-nums">{reports.length}</p>
                    </div>

                    <div className="rounded-xl bg-white/5 p-4">
                        <p className="text-xs text-slate-400">Mensajes Consolidados</p>
                        <p className="mt-1 text-xl font-bold tabular-nums">
                            {activeReport?.resumen_metricas?.total_mensajes ?? 0}
                        </p>
                    </div>

                    <div className="rounded-xl bg-white/5 p-4">
                        <p className="text-xs text-slate-400">Activos Aprobados</p>
                        <p className="mt-1 text-xl font-bold tabular-nums text-emerald-300">
                            {activeReport?.resumen_metricas?.total_aprobados ?? 0}
                        </p>
                    </div>

                    <div className="rounded-xl bg-white/5 p-4">
                        <p className="text-xs text-slate-400">Estado Almacenamiento</p>
                        <p className="mt-1 text-base font-bold tabular-nums sm:text-lg">
                            {ociSyncedCount} en OCI · {localSavedCount} Local
                        </p>
                    </div>
                </div>
            </div>

            {/* Panel Principal: Reporte Semanal y Distribución OCI — Flujo de Tania (RF-03) */}
            <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
                    <div className="flex items-start gap-3">
                        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-orange-50 text-orange-500">
                            <CloudUpload size={20} />
                        </div>

                        <div>
                            <h3 className="font-bold text-slate-900">
                                📦 Reporte Semanal y Distribución (OCI)
                            </h3>
                            <p className="text-sm text-slate-500">
                                Empaqueta los mensajes analizados por IA, calcula métricas de sentimiento, temas y segmentos, guarda el JSON semanal y lo distribuye a Oracle Cloud.
                            </p>
                        </div>
                    </div>

                    <span className="w-fit rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                        {weeklyPeriod
                            ? `Período activo: ${weeklyPeriod.start_date} — ${weeklyPeriod.end_date}`
                            : "Listo para empaquetar"}
                    </span>
                </div>

                <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_auto] lg:items-start">
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                        <label
                            htmlFor="week-label-input"
                            className="block text-xs font-bold uppercase tracking-wide text-slate-600"
                        >
                            Etiqueta de la Semana (AAAA-semana-NN)
                        </label>
                        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center">
                            <input
                                id="week-label-input"
                                type="text"
                                value={weekLabelInput}
                                onChange={(e) => setWeekLabelInput(e.target.value)}
                                placeholder="Ej: 2026-semana-42"
                                className={`w-full rounded-xl border bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 outline-none transition sm:max-w-xs ${
                                    isWeekLabelValid
                                        ? "border-slate-300 focus:border-orange-500"
                                        : "border-red-400 focus:border-red-500"
                                }`}
                            />
                            <span className="text-xs text-slate-500">
                                Destino OCI:{" "}
                                <code className="rounded bg-slate-200/70 px-1.5 py-0.5 font-mono text-slate-700">
                                    {bucketName}/activos/{weekLabelInput.trim() || "AAAA-semana-NN"}/paquete-distribucion.json
                                </code>
                            </span>
                        </div>
                        {!isWeekLabelValid && (
                            <p className="mt-2 text-xs font-medium text-red-600">
                                El formato debe ser exactamente AAAA-semana-NN (por ejemplo: 2026-semana-42).
                            </p>
                        )}
                    </div>

                    <button
                        type="button"
                        disabled={isSyncing || !isWeekLabelValid}
                        onClick={() => executeWeeklySync(weekLabelInput)}
                        className="inline-flex min-h-[56px] items-center justify-center gap-2 rounded-xl bg-orange-500 px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-60 lg:min-w-64"
                    >
                        {isSyncing ? (
                            <>
                                <Loader2 size={18} className="animate-spin" />
                                Empaquetando y subiendo...
                            </>
                        ) : (
                            <>
                                <CloudUpload size={18} />
                                📦 Generar y Subir Reporte a OCI
                            </>
                        )}
                    </button>
                </div>

                {/* Banner de resultado de operación */}
                {feedbackBanner && (
                    <div
                        className={`mt-4 flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${
                            feedbackBanner.type === "success"
                                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                                : feedbackBanner.type === "offline"
                                  ? "border-amber-200 bg-amber-50 text-amber-800"
                                  : "border-red-200 bg-red-50 text-red-800"
                        }`}
                    >
                        {feedbackBanner.type === "success" ? (
                            <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600" />
                        ) : (
                            <AlertTriangle
                                size={18}
                                className={`mt-0.5 shrink-0 ${
                                    feedbackBanner.type === "offline"
                                        ? "text-amber-600"
                                        : "text-red-600"
                                }`}
                            />
                        )}
                        <div className="flex-1 font-medium">{feedbackBanner.message}</div>
                    </div>
                )}
            </div>

            {/* Visor Interactivo del Reporte Semanal y Descarga Directa (RF-04) */}
            {activeReport && (
                <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                    <div className="flex flex-col justify-between gap-4 border-b border-slate-100 pb-4 lg:flex-row lg:items-center">
                        <div className="flex items-start gap-3">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                                <FileJson size={20} />
                            </div>
                            <div>
                                <div className="flex flex-wrap items-center gap-2">
                                    <h3 className="font-bold text-slate-900">
                                        Inspección del Reporte: {activeReport.semana}
                                    </h3>
                                    <span
                                        className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                                            activeReport.subido_oci
                                                ? "bg-emerald-100 text-emerald-700"
                                                : "bg-amber-100 text-amber-700"
                                        }`}
                                    >
                                        {activeReport.subido_oci
                                            ? "✅ Subido a OCI"
                                            : "💾 Respaldo Local"}
                                    </span>
                                </div>
                                <p className="mt-0.5 text-xs text-slate-500">
                                    Generado: {formatDateTime(activeReport.generado_en)} · Ruta OCI:{" "}
                                    <code className="font-mono text-slate-700">
                                        {activeReport.bucket}/{activeReport.ruta_oci}
                                    </code>
                                </p>
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setShowJsonPreview((prev) => !prev)}
                                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
                            >
                                {showJsonPreview ? (
                                    <>
                                        <EyeOff size={15} />
                                        👁️ Ocultar JSON del Reporte Semanal ({activeReport.semana})
                                    </>
                                ) : (
                                    <>
                                        <Eye size={15} />
                                        👁️ Ver JSON del Reporte Semanal ({activeReport.semana})
                                    </>
                                )}
                            </button>

                            <button
                                type="button"
                                onClick={() => handleDownloadJson(activeReport)}
                                className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white transition hover:bg-slate-800"
                            >
                                <Download size={15} />
                                ⬇️ Descargar {activeReport.semana}.json
                            </button>
                        </div>
                    </div>

                    {/* Resumen de métricas del reporte seleccionado */}
                    <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
                        <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                Consolidado de Mensajes
                            </p>
                            <div className="mt-3 grid grid-cols-3 gap-2 text-center">
                                <div className="rounded-lg bg-white p-2.5 shadow-xs">
                                    <p className="text-[11px] text-slate-500">Total</p>
                                    <p className="text-lg font-bold text-slate-900">
                                        {activeReport.resumen_metricas?.total_mensajes ?? 0}
                                    </p>
                                </div>
                                <div className="rounded-lg bg-white p-2.5 shadow-xs">
                                    <p className="text-[11px] text-emerald-600">Aprobados</p>
                                    <p className="text-lg font-bold text-emerald-600">
                                        {activeReport.resumen_metricas?.total_aprobados ?? 0}
                                    </p>
                                </div>
                                <div className="rounded-lg bg-white p-2.5 shadow-xs">
                                    <p className="text-[11px] text-slate-500">Descartados</p>
                                    <p className="text-lg font-bold text-slate-600">
                                        {activeReport.resumen_metricas?.total_descartados ?? 0}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                Sentimientos y Segmentos
                            </p>
                            <div className="mt-3 flex flex-wrap gap-1.5">
                                {Object.entries(
                                    activeReport.resumen_metricas?.sentimiento || {}
                                ).map(([sent, count]) => (
                                    <span
                                        key={sent}
                                        className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 shadow-xs"
                                    >
                                        {sent}: {count}
                                    </span>
                                ))}
                                {Object.entries(
                                    activeReport.resumen_metricas?.segmentos || {}
                                ).map(([seg, count]) => (
                                    <span
                                        key={seg}
                                        className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700"
                                    >
                                        {seg}: {count}
                                    </span>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
                                Top Temas en Tendencia
                            </p>
                            <div className="mt-3 flex flex-wrap gap-1.5">
                                {(activeReport.resumen_metricas?.temas_tendencia || [])
                                    .length > 0 ? (
                                    activeReport.resumen_metricas.temas_tendencia.map(
                                        (t) => (
                                            <span
                                                key={t.tema}
                                                className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-semibold text-orange-700"
                                            >
                                                {t.tema} ({t.menciones})
                                            </span>
                                        )
                                    )
                                ) : (
                                    <span className="text-xs text-slate-400">
                                        Sin hashtags registrados en este corte
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Bloque JSON Desplegable */}
                    {showJsonPreview && (
                        <div className="mt-5 overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
                            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2.5 text-xs text-slate-300">
                                <span className="font-mono font-semibold">
                                    reportes/{activeReport.nombre_archivo} ({formatBytes(activeReport.tamano_bytes)})
                                </span>
                                <button
                                    type="button"
                                    onClick={handleCopyJson}
                                    className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1 text-xs font-medium text-slate-200 transition hover:bg-slate-700"
                                >
                                    <Copy size={13} />
                                    {copiedJson ? "¡Copiado!" : "Copiar JSON"}
                                </button>
                            </div>
                            <pre className="max-h-96 overflow-auto p-4 font-mono text-xs leading-relaxed text-emerald-300">
                                {JSON.stringify(activeReport.reporte, null, 2)}
                            </pre>
                        </div>
                    )}
                </div>
            )}

            {/* Tabla Conectada: Historial de Informes Semanales (RF-05) */}
            <div className="mt-6 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
                <div className="flex flex-col justify-between gap-4 border-b border-slate-200 p-6 lg:flex-row lg:items-center">
                    <div>
                        <h3 className="font-bold text-slate-900">
                            Historial de Informes Semanales
                        </h3>
                        <p className="mt-1 text-xs text-slate-500">
                            Reportes generados en el servidor local y sincronizados con el bucket de distribución en OCI.
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2">
                        <div className="mr-2 flex items-center gap-1 text-xs text-slate-500">
                            <Filter size={14} />
                            Filtrar por Estado:
                        </div>

                        <button
                            type="button"
                            onClick={() => setStatusFilter("all")}
                            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                                statusFilter === "all"
                                    ? "border border-slate-300 bg-slate-900 text-white shadow-xs"
                                    : "text-slate-600 hover:bg-slate-100"
                            }`}
                        >
                            Todos ({reports.length})
                        </button>

                        <button
                            type="button"
                            onClick={() => setStatusFilter("oci")}
                            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                                statusFilter === "oci"
                                    ? "border border-emerald-600 bg-emerald-600 text-white shadow-xs"
                                    : "text-slate-600 hover:bg-slate-100"
                            }`}
                        >
                            Subido a OCI ({ociSyncedCount})
                        </button>

                        <button
                            type="button"
                            onClick={() => setStatusFilter("local")}
                            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                                statusFilter === "local"
                                    ? "border border-amber-500 bg-amber-500 text-white shadow-xs"
                                    : "text-slate-600 hover:bg-slate-100"
                            }`}
                        >
                            Respaldo Local / Offline ({localSavedCount})
                        </button>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full min-w-[950px]">
                        <thead className="bg-slate-50">
                            <tr className="border-b border-slate-200 text-left text-[11px] font-bold uppercase tracking-wide text-slate-500">
                                <th className="px-6 py-4">Semana / Período</th>
                                <th className="px-6 py-4">Archivo JSON & Ruta OCI</th>
                                <th className="px-6 py-4">Métricas & Tamaño</th>
                                <th className="px-6 py-4">Estado de Distribución</th>
                                <th className="px-6 py-4 text-right">Acciones</th>
                            </tr>
                        </thead>

                        <tbody className="divide-y divide-slate-100">
                            {isLoadingReports ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-12 text-center">
                                        <div className="inline-flex items-center gap-2 text-sm text-slate-500">
                                            <Loader2 size={18} className="animate-spin text-orange-500" />
                                            Cargando historial de reportes semanales...
                                        </div>
                                    </td>
                                </tr>
                            ) : filteredReports.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="px-6 py-14 text-center">
                                        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100 text-slate-400">
                                            <FileText size={22} />
                                        </div>
                                        <p className="mt-4 text-sm font-semibold text-slate-700">
                                            No hay informes semanales en esta vista
                                        </p>
                                        <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-slate-400">
                                            Usa el botón &ldquo;📦 Generar y Subir Reporte a OCI&rdquo; en el panel superior para empaquetar los mensajes evaluados.
                                        </p>
                                    </td>
                                </tr>
                            ) : (
                                filteredReports.map((item) => {
                                    const isRowRetrying = retryingWeek === item.semana;
                                    const isSelected = activeReport?.semana === item.semana;
                                    return (
                                        <tr
                                            key={item.semana}
                                            className={`transition hover:bg-slate-50/80 ${
                                                isSelected ? "bg-orange-50/30" : ""
                                            }`}
                                        >
                                            <td className="px-6 py-4">
                                                <p className="text-sm font-bold text-slate-900">
                                                    {item.semana}
                                                </p>
                                                <p className="mt-0.5 text-xs text-slate-500">
                                                    {formatDateTime(item.generado_en)}
                                                </p>
                                            </td>

                                            <td className="px-6 py-4">
                                                <p className="font-mono text-xs font-semibold text-slate-800">
                                                    reportes/{item.nombre_archivo}
                                                </p>
                                                <p className="mt-0.5 font-mono text-[11px] text-slate-500">
                                                    {item.bucket}/{item.ruta_oci}
                                                </p>
                                            </td>

                                            <td className="px-6 py-4">
                                                <p className="text-xs font-semibold text-slate-800">
                                                    {item.resumen_metricas?.total_mensajes ?? 0} mensajes{" "}
                                                    <span className="font-normal text-slate-500">
                                                        ({item.resumen_metricas?.total_aprobados ?? 0} aprobados /{" "}
                                                        {item.resumen_metricas?.total_descartados ?? 0} descartados)
                                                    </span>
                                                </p>
                                                <p className="mt-0.5 text-xs text-slate-400">
                                                    Tamaño: {formatBytes(item.tamano_bytes)}
                                                </p>
                                            </td>

                                            <td className="px-6 py-4">
                                                <span
                                                    className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${
                                                        item.subido_oci
                                                            ? "bg-emerald-50 text-emerald-700"
                                                            : "bg-amber-50 text-amber-700"
                                                    }`}
                                                >
                                                    {item.subido_oci
                                                        ? "✅ Subido a OCI"
                                                        : "💾 Respaldo Local"}
                                                </span>
                                            </td>

                                            <td className="px-6 py-4 text-right">
                                                <div className="inline-flex flex-wrap items-center justify-end gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() => {
                                                            setSelectedReport(item);
                                                            setShowJsonPreview(true);
                                                        }}
                                                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
                                                    >
                                                        <Eye size={13} />
                                                        👁️ Ver JSON
                                                    </button>

                                                    <button
                                                        type="button"
                                                        onClick={() => handleDownloadJson(item)}
                                                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100"
                                                    >
                                                        <Download size={13} />
                                                        ⬇️ Descargar
                                                    </button>

                                                    <button
                                                        type="button"
                                                        disabled={isRowRetrying || isSyncing}
                                                        onClick={() =>
                                                            executeWeeklySync(item.semana, true)
                                                        }
                                                        className="inline-flex items-center gap-1 rounded-lg bg-orange-500 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-orange-600 disabled:opacity-50"
                                                    >
                                                        <RefreshCw
                                                            size={13}
                                                            className={
                                                                isRowRetrying ? "animate-spin" : ""
                                                            }
                                                        />
                                                        {item.subido_oci
                                                            ? "🔄 Reintentar OCI"
                                                            : "☁️ Subir a OCI"}
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}

export default OCIStorage;