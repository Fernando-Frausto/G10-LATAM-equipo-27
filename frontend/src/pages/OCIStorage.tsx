import {
    AlertTriangle,
    CheckCircle2,
    Cloud,
    Copy,
    Download,
    Eye,
    FileText,
    Loader2,
    RefreshCw,
    Upload,
    X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
    BarChart,
    Bar,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
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
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
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

    const [weekLabelInput, setWeekLabelInput] = useState<string>(computeDefaultIsoWeekLabel);
    const [isSyncing, setIsSyncing] = useState<boolean>(false);
    const [retryingWeek, setRetryingWeek] = useState<string | null>(null);
    const [statusFilter, setStatusFilter] = useState<FilterMode>("all");

    const [feedbackBanner, setFeedbackBanner] = useState<{
        type: "success" | "offline" | "error";
        message: string;
    } | null>(null);

    const [inspectionModalReport, setInspectionModalReport] = useState<OCIReportItem | null>(null);
    const [jsonModalReport, setJsonModalReport] = useState<OCIReportItem | null>(null);
    const [copiedJson, setCopiedJson] = useState<boolean>(false);

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

    const isServiceConnected =
        ociStatus?.status === "connected" || ociStatus?.status === "ready";
    const isOciOnline = Boolean(ociStatus?.oci_configured);
    const bucketName = ociStatus?.bucket || "communitylab-reports";
    const regionName = ociStatus?.region || "sa-santiago-1";
    const namespace = ((ociStatus as unknown) as { namespace?: string })?.namespace || "axk3lz9qpm2";

    const totalReportsBytes = useMemo(
        () => reports.reduce((acc, r) => acc + (r.tamano_bytes || 0), 0),
        [reports]
    );

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

    const chartData = useMemo(() => {
        if (!reports || reports.length === 0) {
            return [
                { label: "W40", semana: "2026-semana-40", mensajes: 74, isMax: false },
                { label: "W41", semana: "2026-semana-41", mensajes: 88, isMax: false },
                { label: "W42", semana: "2026-semana-42", mensajes: 94, isMax: true },
            ];
        }
        const list = [...reports].slice(0, 8).reverse();
        const maxVal = Math.max(...list.map((r) => r.resumen_metricas?.total_mensajes ?? 0), 1);
        return list.map((r) => {
            const count = r.resumen_metricas?.total_mensajes ?? 0;
            const match = r.semana.match(/(?:semana-|W)(\d+)$/i);
            const shortLabel = match ? `W${match[1]}` : r.semana;
            return {
                label: shortLabel,
                semana: r.semana,
                mensajes: count,
                isMax: count === maxVal && count > 0,
            };
        });
    }, [reports]);

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

    const handleCopyJson = async (reportContent: unknown) => {
        try {
            await navigator.clipboard.writeText(JSON.stringify(reportContent, null, 2));
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
                response.bucket || ociStatus?.bucket || "communitylab-reports";
            const rutaRes =
                response.ruta_oci ||
                `activos/${semanaRes}/paquete-distribucion.json`;
            const subidoOci = Boolean(response.subido_oci);

            if (subidoOci) {
                setFeedbackBanner({
                    type: "success",
                    message: `Reporte ${semanaRes}.json empaquetado y respaldado exitosamente en Oracle Cloud Infrastructure (${bucketRes}/${rutaRes}).`,
                });
            } else {
                setFeedbackBanner({
                    type: "offline",
                    message: `Modo Local / Offline: Sin conexión activa a OCI en este entorno. Reporte generado y respaldado en reportes/${semanaRes}.json.`,
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
                message: errMsg,
            });
        } finally {
            setIsSyncing(false);
            setRetryingWeek(null);
        }
    };

    const periodText = weeklyPeriod
        ? `${weeklyPeriod.iso_week_label || weeklyPeriod.week_label || weekLabelInput} · ${weeklyPeriod.start_date} – ${weeklyPeriod.end_date}`
        : "2026-W43 · 19 – 25 oct";

    const usagePercent = Math.max(2, Math.min(100, Math.round((totalReportsBytes / (10 * 1024 * 1024 * 1024)) * 100)));

    return (
        <section data-view="oci-storage" aria-labelledby="t-oci" className="space-y-6">
            {/* Cabecera idéntica a Cristian (.l-page-head) */}
            <div className="l-page-head">
                <div className="l-page-head__text">
                    <h1 className="t-page" id="t-oci">
                        Informes y Almacenamiento (OCI)
                    </h1>
                    <p>
                        Reportes semanales generados automáticamente y respaldados en Oracle Cloud Infrastructure.
                    </p>
                </div>
            </div>

            <div className="l-stack space-y-6">
                {/* Grid 2 Columnas idéntico a Cristian (.l-grid.l-grid--side-main) */}
                <div className="l-grid l-grid--side-main">
                    {/* Tarjeta Lateral Izquierda: OCI Object Storage con colores actuales (#080A27) */}
                    <article className="c-card c-card--brand bg-[#080A27] text-white">
                        <div className="l-between mb-5 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <span className="c-iconbox bg-orange-500/15 text-orange-400">
                                    <Cloud size={20} />
                                </span>
                                <h2 className="t-section font-bold !text-white" style={{ color: "#ffffff" }}>
                                    OCI Object Storage
                                </h2>
                            </div>

                            <span
                                className={`c-pill c-pill--dot ${
                                    isOciOnline ? "c-pill--success" : "c-pill--warning"
                                }`}
                                style={{
                                    backgroundColor: isOciOnline
                                        ? "rgba(16, 185, 129, 0.15)"
                                        : "rgba(245, 158, 11, 0.15)",
                                    color: isOciOnline ? "#6ee7b7" : "#fcd34d",
                                    border: "none",
                                }}
                            >
                                {!isServiceConnected
                                    ? "Verificando..."
                                    : isOciOnline
                                      ? "Conectado"
                                      : "Modo Local / Offline"}
                            </span>
                        </div>

                        <dl className="c-dl" style={{ color: "var(--slate-300, #cbd5e1)" }}>
                            <dt className="!text-slate-400" style={{ color: "#94a3b8" }}>Bucket</dt>
                            <dd className="font-mono !text-white" style={{ color: "#ffffff" }}>{bucketName}</dd>

                            <dt className="!text-slate-400" style={{ color: "#94a3b8" }}>Región</dt>
                            <dd className="font-mono !text-white" style={{ color: "#ffffff" }}>{regionName}</dd>

                            <dt className="!text-slate-400" style={{ color: "#94a3b8" }}>Namespace</dt>
                            <dd className="t-mono font-mono !text-white" style={{ color: "#ffffff" }}>{namespace}</dd>

                            <dt className="!text-slate-400" style={{ color: "#94a3b8" }}>Último sync</dt>
                            <dd className="!text-white" style={{ color: "#ffffff" }}>
                                {reports.length > 0
                                    ? formatDateTime(reports[0]?.generado_en)
                                    : "Hoy, 08:00"}
                            </dd>
                        </dl>

                        <div className="c-meter mt-5">
                            <div className="c-meter__row">
                                <span className="!text-slate-400" style={{ color: "#94a3b8" }}>Uso del bucket</span>
                                <b className="tabular-nums !text-white" style={{ color: "#ffffff" }}>
                                    {formatBytes(totalReportsBytes)} / 10 GB
                                </b>
                            </div>
                            <div className="c-progress mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                                <div
                                    className="c-progress__bar h-full bg-gradient-to-r from-orange-500 to-amber-400"
                                    style={{ width: `${usagePercent}%` }}
                                />
                            </div>
                        </div>
                    </article>

                    {/* Tarjeta Principal Derecha: Reporte Semanal y Distribución (OCI) */}
                    <article className="c-card c-card--lg flex flex-col justify-between">
                        <div className="c-card__header flex flex-wrap items-start justify-between gap-4">
                            <div>
                                <h2 className="t-card">📦 Reporte Semanal y Distribución (OCI)</h2>
                                <p className="c-card__desc">
                                    Período actual: <b>{periodText}</b>
                                </p>
                            </div>

                            {/* Acciones de Cabecera con Etiqueta de la Semana a la izquierda de Generar Reporte */}
                            <div className="l-cluster flex flex-wrap items-center gap-2">
                                <div className="flex items-center gap-1.5">
                                    <label
                                        htmlFor="week-label-input"
                                        className="text-xs font-semibold text-slate-500 whitespace-nowrap"
                                    >
                                        Etiqueta:
                                    </label>
                                    <input
                                        id="week-label-input"
                                        type="text"
                                        value={weekLabelInput}
                                        onChange={(e) => setWeekLabelInput(e.target.value)}
                                        placeholder="AAAA-semana-NN"
                                        title="Etiqueta de la semana en formato AAAA-semana-NN (ej. 2026-semana-42)"
                                        className={`rounded-lg border px-2.5 py-1 text-xs font-mono font-semibold outline-none transition w-36 ${
                                            isWeekLabelValid
                                                ? "border-slate-200 bg-white text-slate-800 focus:border-orange-500"
                                                : "border-red-400 bg-red-50 text-red-700 focus:border-red-500"
                                        }`}
                                    />
                                </div>

                                <button
                                    className="c-btn c-btn--secondary c-btn--sm"
                                    type="button"
                                    id="oci-generate"
                                    disabled={isSyncing || !isWeekLabelValid}
                                    onClick={() => executeWeeklySync(weekLabelInput)}
                                >
                                    {isSyncing ? (
                                        <Loader2 size={13} className="animate-spin" />
                                    ) : (
                                        <FileText size={13} />
                                    )}
                                    <span>{isSyncing ? "Generando..." : "Generar reporte"}</span>
                                </button>

                                <button
                                    className="c-btn c-btn--primary c-btn--sm"
                                    type="button"
                                    id="oci-sync"
                                    disabled={isSyncing || !isWeekLabelValid}
                                    onClick={() => executeWeeklySync(weekLabelInput)}
                                >
                                    {isSyncing ? (
                                        <Loader2 size={13} className="animate-spin" />
                                    ) : (
                                        <Upload size={13} />
                                    )}
                                    <span>Sincronizar con OCI</span>
                                </button>
                            </div>
                        </div>

                        {/* Gráfico de barras de mensajes por semana (idéntico al ch-oci-weeks de Cristian) */}
                        <div className="c-chart c-chart--sm mt-4 h-44 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                    data={chartData}
                                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                    <XAxis
                                        dataKey="label"
                                        tickLine={false}
                                        tick={{ fontSize: 11, fill: "#64748b" }}
                                    />
                                    <YAxis
                                        tickLine={false}
                                        tick={{ fontSize: 11, fill: "#64748b" }}
                                        allowDecimals={false}
                                    />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: "#0f172a",
                                            border: "none",
                                            borderRadius: "8px",
                                            color: "#ffffff",
                                            fontSize: "12px",
                                        }}
                                        itemStyle={{ color: "#ffffff" }}
                                        labelStyle={{ color: "#94a3b8", fontWeight: 600 }}
                                        formatter={(val) => [`${val} mensajes`, "Consolidado"]}
                                        labelFormatter={(lbl) => `Semana ${lbl}`}
                                    />
                                    <Bar dataKey="mensajes" radius={[4, 4, 0, 0]}>
                                        {chartData.map((entry, index) => (
                                            <Cell
                                                key={`cell-${index}`}
                                                fill={entry.isMax ? "#ff7400" : "#cbd5e1"}
                                            />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </article>
                </div>

                {/* Banner de feedback si ocurre alguna sincronización o error */}
                {feedbackBanner && (
                    <div
                        className={`flex items-start gap-3 rounded-xl border p-4 text-sm ${
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
                        <button
                            type="button"
                            onClick={() => setFeedbackBanner(null)}
                            className="text-xs font-semibold hover:underline"
                        >
                            Cerrar
                        </button>
                    </div>
                )}

                {/* Tarjeta de Tabla (.c-card.c-card--flush): Historial de Informes Semanales */}
                <article className="c-card c-card--flush">
                    <div className="c-card__section l-between flex flex-wrap items-center justify-between gap-3">
                        <div>
                            <h2 className="t-card">Historial de Informes Semanales</h2>
                            <p className="c-card__desc">JSON generado cada lunes a las 08:00 y respaldado en OCI.</p>
                        </div>

                        {/* Filtros de Estado */}
                        <div className="flex items-center gap-1.5 text-xs text-slate-500">
                            <button
                                type="button"
                                onClick={() => setStatusFilter("all")}
                                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                                    statusFilter === "all"
                                        ? "bg-slate-900 text-white"
                                        : "text-slate-600 hover:bg-slate-100"
                                }`}
                            >
                                Todos ({reports.length})
                            </button>
                            <button
                                type="button"
                                onClick={() => setStatusFilter("oci")}
                                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                                    statusFilter === "oci"
                                        ? "bg-emerald-600 text-white"
                                        : "text-slate-600 hover:bg-slate-100"
                                }`}
                            >
                                OCI ({ociSyncedCount})
                            </button>
                            <button
                                type="button"
                                onClick={() => setStatusFilter("local")}
                                className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                                    statusFilter === "local"
                                        ? "bg-amber-500 text-white"
                                        : "text-slate-600 hover:bg-slate-100"
                                }`}
                            >
                                Local ({localSavedCount})
                            </button>
                        </div>
                    </div>

                    <div className="c-table-wrap">
                        <table className="c-table c-table--compact" id="oci-table">
                            <thead>
                                <tr>
                                    <th>Semana</th>
                                    <th className="is-right">Mensajes</th>
                                    <th>Tamaño</th>
                                    <th>Generado</th>
                                    <th>Estado</th>
                                    <th className="is-right">Acciones</th>
                                </tr>
                            </thead>
                            <tbody>
                                {isLoadingReports ? (
                                    <tr>
                                        <td colSpan={6} className="py-8 text-center text-slate-400">
                                            <div className="inline-flex items-center gap-2">
                                                <Loader2 size={16} className="animate-spin text-orange-500" />
                                                Cargando historial de reportes...
                                            </div>
                                        </td>
                                    </tr>
                                ) : filteredReports.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="py-8 text-center text-slate-400">
                                            No hay informes semanales disponibles en este filtro.
                                        </td>
                                    </tr>
                                ) : (
                                    filteredReports.map((r) => {
                                        const isRowRetrying = retryingWeek === r.semana;
                                        return (
                                            <tr key={r.semana}>
                                                <td style={{ whiteSpace: "nowrap" }}>
                                                    <span className="is-strong t-mono font-mono">{r.semana}</span>
                                                </td>
                                                <td className="is-right tabular-nums font-semibold">
                                                    {(r.resumen_metricas?.total_mensajes ?? 0).toLocaleString()}
                                                </td>
                                                <td className="tabular-nums">
                                                    {formatBytes(r.tamano_bytes)}
                                                </td>
                                                <td style={{ whiteSpace: "nowrap" }} className="tabular-nums text-xs text-slate-500">
                                                    {formatDateTime(r.generado_en)}
                                                </td>
                                                <td>
                                                    <span
                                                        className={`c-pill c-pill--dot ${
                                                            r.subido_oci ? "c-pill--success" : "c-pill--warning"
                                                        }`}
                                                    >
                                                        {r.subido_oci ? "✓ Subido a OCI" : "💾 Respaldo Local"}
                                                    </span>
                                                </td>
                                                <td className="is-right">
                                                    <div
                                                        className="l-cluster"
                                                        style={{
                                                            justifyContent: "flex-end",
                                                            flexWrap: "nowrap",
                                                            display: "flex",
                                                            alignItems: "center",
                                                            gap: "0.375rem",
                                                        }}
                                                    >
                                                        {/* 1. Botón Ver JSON */}
                                                        <button
                                                            type="button"
                                                            className="c-btn c-btn--secondary c-btn--sm"
                                                            onClick={() => setJsonModalReport(r)}
                                                        >
                                                            <Eye size={13} />
                                                            <span>Ver JSON</span>
                                                        </button>

                                                        {/* 2. Botón NEGRO de Inspección del Reporte (Solicitud del Usuario) */}
                                                        <button
                                                            type="button"
                                                            className="c-btn c-btn--sm bg-slate-900 text-white hover:bg-slate-800 border-transparent shadow-xs"
                                                            onClick={() => setInspectionModalReport(r)}
                                                            title="Inspección del Reporte"
                                                        >
                                                            <FileText size={13} />
                                                            <span>Inspección</span>
                                                        </button>

                                                        {/* 3. Botón Descargar */}
                                                        <button
                                                            type="button"
                                                            className="c-btn c-btn--secondary c-btn--icon c-btn--sm"
                                                            title={`Descargar reporte_${r.semana}.json`}
                                                            aria-label={`Descargar reporte ${r.semana}`}
                                                            onClick={() => handleDownloadJson(r)}
                                                        >
                                                            <Download size={13} />
                                                        </button>

                                                        {/* 4. Botón Subir / Reintentar OCI */}
                                                        <button
                                                            type="button"
                                                            disabled={isRowRetrying || isSyncing}
                                                            className="c-btn c-btn--primary c-btn--sm"
                                                            onClick={() => executeWeeklySync(r.semana, true)}
                                                        >
                                                            <RefreshCw
                                                                size={13}
                                                                className={isRowRetrying ? "animate-spin" : ""}
                                                            />
                                                            <span>
                                                                {r.subido_oci ? "Reintentar OCI" : "Subir a OCI"}
                                                            </span>
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
                </article>
            </div>

            {/* MODAL 1: Inspección del Reporte (Ventana emergente activada con el botón NEGRO) */}
            {inspectionModalReport && (
                <div
                    className="c-modal is-open"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="inspection-modal-title"
                >
                    <div className="c-modal__dialog max-w-2xl">
                        <div className="c-modal__head">
                            <div className="flex items-center gap-2">
                                <FileText size={18} className="text-orange-500" />
                                <h2 className="t-card" id="inspection-modal-title">
                                    Inspección del Reporte: {inspectionModalReport.semana}
                                </h2>
                            </div>
                            <button
                                type="button"
                                className="c-btn c-btn--ghost c-btn--icon c-btn--sm"
                                onClick={() => setInspectionModalReport(null)}
                                aria-label="Cerrar modal"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        <div className="c-modal__body space-y-4">
                            {/* Estado y Ruta OCI */}
                            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-50 p-3 text-xs border border-slate-200/80">
                                <div className="flex items-center gap-2">
                                    <span
                                        className={`c-pill c-pill--dot ${
                                            inspectionModalReport.subido_oci
                                                ? "c-pill--success"
                                                : "c-pill--warning"
                                        }`}
                                    >
                                        {inspectionModalReport.subido_oci
                                            ? "✓ Subido a OCI"
                                            : "💾 Respaldo Local"}
                                    </span>
                                    <span className="font-mono text-slate-600">
                                        {inspectionModalReport.bucket}/{inspectionModalReport.ruta_oci}
                                    </span>
                                </div>
                                <span className="text-slate-400">
                                    Generado: {formatDateTime(inspectionModalReport.generado_en)}
                                </span>
                            </div>

                            {/* 3 Tarjetas de Métricas de la Inspección */}
                            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
                                {/* Consolidado */}
                                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                                    <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                                        Consolidado
                                    </p>
                                    <div className="mt-2.5 grid grid-cols-3 gap-1.5 text-center">
                                        <div className="rounded-lg bg-slate-50 p-1.5">
                                            <p className="text-[10px] text-slate-500">Total</p>
                                            <p className="text-base font-bold text-slate-900 tabular-nums">
                                                {inspectionModalReport.resumen_metricas?.total_mensajes ?? 0}
                                            </p>
                                        </div>
                                        <div className="rounded-lg bg-emerald-50 p-1.5">
                                            <p className="text-[10px] text-emerald-700">Aprobados</p>
                                            <p className="text-base font-bold text-emerald-600 tabular-nums">
                                                {inspectionModalReport.resumen_metricas?.total_aprobados ?? 0}
                                            </p>
                                        </div>
                                        <div className="rounded-lg bg-slate-50 p-1.5">
                                            <p className="text-[10px] text-slate-500">Descartados</p>
                                            <p className="text-base font-bold text-slate-600 tabular-nums">
                                                {inspectionModalReport.resumen_metricas?.total_descartados ?? 0}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Sentimientos y Segmentos */}
                                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                                    <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                                        Sentimientos y Segmentos
                                    </p>
                                    <div className="mt-2 flex flex-wrap gap-1">
                                        {Object.entries(
                                            inspectionModalReport.resumen_metricas?.sentimiento || {}
                                        ).map(([sent, count]) => (
                                            <span
                                                key={sent}
                                                className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700 tabular-nums"
                                            >
                                                {sent}: {count}
                                            </span>
                                        ))}
                                        {Object.entries(
                                            inspectionModalReport.resumen_metricas?.segmentos || {}
                                        ).map(([seg, count]) => (
                                            <span
                                                key={seg}
                                                className="rounded-md bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700 tabular-nums"
                                            >
                                                {seg}: {count}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                {/* Top Temas en Tendencia */}
                                <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-2xs">
                                    <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                                        Top Temas
                                    </p>
                                    <div className="mt-2 flex flex-wrap gap-1">
                                        {(inspectionModalReport.resumen_metricas?.temas_tendencia || []).length > 0 ? (
                                            inspectionModalReport.resumen_metricas?.temas_tendencia?.map((t) => (
                                                <span
                                                    key={t.tema}
                                                    className="rounded-md bg-orange-50 px-2 py-0.5 text-[11px] font-semibold text-orange-700 tabular-nums"
                                                >
                                                    {t.tema} ({t.menciones})
                                                </span>
                                            ))
                                        ) : (
                                            <span className="text-xs text-slate-400 italic">
                                                Sin temas registrados
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="c-modal__foot">
                            <button
                                type="button"
                                className="c-btn c-btn--secondary c-btn--sm"
                                onClick={() => handleDownloadJson(inspectionModalReport)}
                            >
                                <Download size={13} />
                                <span>Descargar .json</span>
                            </button>
                            <button
                                type="button"
                                className="c-btn c-btn--secondary c-btn--sm"
                                onClick={() => {
                                    const r = inspectionModalReport;
                                    setInspectionModalReport(null);
                                    setJsonModalReport(r);
                                }}
                            >
                                <Eye size={13} />
                                <span>Ver JSON completo</span>
                            </button>
                            <button
                                type="button"
                                className="c-btn c-btn--primary c-btn--sm"
                                onClick={() => setInspectionModalReport(null)}
                            >
                                Cerrar
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* MODAL 2: Ver JSON (.c-modal idéntico al de Cristian) */}
            {jsonModalReport && (
                <div
                    className="c-modal is-open"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="json-modal-title"
                >
                    <div className="c-modal__dialog max-w-3xl">
                        <div className="c-modal__head">
                            <h2 className="t-card" id="json-modal-title">
                                reporte_{jsonModalReport.semana}.json ({formatBytes(jsonModalReport.tamano_bytes)})
                            </h2>
                            <button
                                type="button"
                                className="c-btn c-btn--ghost c-btn--icon c-btn--sm"
                                onClick={() => setJsonModalReport(null)}
                                aria-label="Cerrar modal"
                            >
                                <X size={16} />
                            </button>
                        </div>

                        <div className="c-modal__body">
                            <pre className="c-code max-h-[60vh] overflow-auto text-xs">
                                {JSON.stringify(jsonModalReport.reporte, null, 2)}
                            </pre>
                        </div>

                        <div className="c-modal__foot">
                            <button
                                type="button"
                                className="c-btn c-btn--secondary c-btn--sm"
                                onClick={() => handleDownloadJson(jsonModalReport)}
                            >
                                <Download size={13} />
                                <span>Descargar</span>
                            </button>
                            <button
                                type="button"
                                className="c-btn c-btn--secondary c-btn--sm"
                                onClick={() => handleCopyJson(jsonModalReport.reporte)}
                            >
                                <Copy size={13} />
                                <span>{copiedJson ? "¡Copiado!" : "Copiar JSON"}</span>
                            </button>
                            <button
                                type="button"
                                className="c-btn c-btn--primary c-btn--sm"
                                onClick={() => setJsonModalReport(null)}
                            >
                                Cerrar
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </section>
    );
}

export default OCIStorage;
