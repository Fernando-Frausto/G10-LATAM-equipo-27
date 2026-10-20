import { clearSession, getToken } from "./session";

const API_URL = (import.meta.env.VITE_API_URL || import.meta.env.VITE_MOTOR_API_URL || "http://127.0.0.1:8002").replace(/\/$/, "");

export async function apiRequest(
    endpoint: string,
    options: RequestInit = {}
) {
    const token = getToken();

    const headers = new Headers(options.headers);

    headers.set("Content-Type", "application/json");

    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers,
    });
    if (response.status === 401) {
        clearSession();

        if (window.location.pathname !== "/login") {
            window.location.replace("/login");
        }

        throw new Error("La sesión ha expirado");
    }

    if (!response.ok) {
        let message = "Error al comunicarse con el servidor";
        const status = response.status;
        let codigoError = "";

        try {
            const error = await response.json();
            message = error.detail || error.mensaje || error.message || message;
            codigoError = error.codigo_error || "";
        } catch {
            if (response.status === 429) {
                message = "Discord o Cloudflare ha limitado temporalmente la IP del servidor en la nube (Error 1015 / Rate Limit). Sincroniza desde tu entorno local o intenta en unos minutos.";
            }
        }

        const err = new Error(message) as Error & { status?: number; codigoError?: string };
        err.status = status;
        err.codigoError = codigoError;
        throw err;
    }

    return response.json();
}
