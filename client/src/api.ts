import { supabase } from "./supabase";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

type Params = Record<string, string | number | boolean | null | undefined>;

type RequestOptions = {
    params?: Params;
    body?: unknown;
    headers?: HeadersInit;
};

function buildUrl(path: string, params?: Params) {
    const url = new URL(path, API);

    for (const [key, value] of Object.entries(params || {})) {
        if (value !== undefined && value !== null) {
            url.searchParams.set(key, String(value));
        }
    }

    return url.toString();
}

async function authHeaders(extraHeaders: HeadersInit = {}) {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;

    return {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...extraHeaders,
    };
}

async function request<T>(
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
    path: string,
    options: RequestOptions = {},
): Promise<T> {
    const res = await fetch(buildUrl(path, options.params), {
        method,
        headers: await authHeaders(options.headers),
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        const message = data?.detail || data?.message || text || res.statusText;
        throw new Error(message);
    }

    return data as T;
}

export const api = {
    get: <T>(path: string, params?: Params) => request<T>("GET", path, { params }),
    post: <T>(path: string, body?: unknown, params?: Params) =>
        request<T>("POST", path, { body, params }),
    put: <T>(path: string, body?: unknown, params?: Params) =>
        request<T>("PUT", path, { body, params }),
    patch: <T>(path: string, body?: unknown, params?: Params) =>
        request<T>("PATCH", path, { body, params }),
    delete: <T>(path: string, params?: Params) =>
        request<T>("DELETE", path, { params }),
};
