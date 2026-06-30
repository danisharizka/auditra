import axios from "axios";

export function formatApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 503) {
      const detail = error.response.data?.detail;
      if (typeof detail === "string") return detail;
    }
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail;
      return typeof detail === "string" ? detail : JSON.stringify(detail);
    }
    if (error.code === "ERR_NETWORK" || !error.response) {
      const isProd = import.meta.env.PROD;
      if (isProd) {
        return (
          "Backend tidak terhubung. Periksa VITE_API_URL di Vercel dan CORS_ORIGINS di Railway.\n" +
          "API: https://auditra-production.up.railway.app/api/health"
        );
      }
      return (
        "Backend tidak terhubung. Jalankan di terminal terpisah:\n" +
        "python -m uvicorn api.main:app --reload --port 8000"
      );
    }
    return `HTTP ${error.response.status}: ${error.message}`;
  }
  if (error instanceof Error) return error.message;
  return "Gagal memuat data dari API.";
}
