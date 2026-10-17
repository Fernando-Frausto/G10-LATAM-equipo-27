import { apiRequest } from "./client";

export interface OCIStorageStatus {
    status: string;
    message: string;
    oci_configured?: boolean;
    mode?: "online" | "offline";
    bucket?: string;
    region?: string;
}

export interface WeeklyPeriod {
    semana_nombre?: string;
    week_label?: string;
    iso_week_label?: string;
    start_date: string;
    end_date: string;
    status: string;
}

export interface OCIReportSummaryMetrics {
    total_mensajes: number;
    total_aprobados: number;
    total_descartados: number;
    sentimiento: Record<string, number>;
    temas_tendencia: Array<{ tema: string; menciones: number }>;
    segmentos: Record<string, number>;
}

export interface OCIReportFull {
    metadata: {
        proyecto: string;
        semana: string;
        version_esquema: string;
        generado_en: string;
        oci_storage: {
            bucket: string;
            ruta: string;
            subido?: boolean;
        };
    };
    resumen_metricas: OCIReportSummaryMetrics;
    activos_copywriting: {
        aprobados: Record<string, unknown>[];
        descartados: Record<string, unknown>[];
    };
}

export interface OCIReportItem {
    semana: string;
    nombre_archivo: string;
    tamano_bytes: number;
    generado_en: string;
    bucket: string;
    ruta_oci: string;
    subido_oci: boolean;
    resumen_metricas: OCIReportSummaryMetrics;
    reporte: OCIReportFull;
}

export interface OCIReportsListResponse {
    reports: OCIReportItem[];
    total: number;
}

export interface WeeklySyncResponse {
    exito?: boolean;
    status: string;
    message: string;
    sync_id: string | number;
    semana?: string;
    subido_oci?: boolean;
    bucket?: string;
    ruta_oci?: string;
    resumen?: OCIReportSummaryMetrics;
    reporte?: OCIReportFull;
    start_date?: string;
    end_date?: string;
}

export async function getOCIStorageStatus(): Promise<OCIStorageStatus> {
    return apiRequest("/api/v1/oci-storage/status", {
        method: "GET",
    });
}

export async function getWeeklyPeriod(): Promise<WeeklyPeriod> {
    return apiRequest("/api/v1/oci-storage/weekly-period", {
        method: "GET",
    });
}

export async function startWeeklySync(semana?: string): Promise<WeeklySyncResponse> {
    return apiRequest("/api/v1/oci-storage/weekly-sync", {
        method: "POST",
        body: JSON.stringify(semana ? { semana } : {}),
    });
}

export async function getOCIReports(): Promise<OCIReportsListResponse> {
    return apiRequest("/api/v1/oci-storage/reports", {
        method: "GET",
    });
}