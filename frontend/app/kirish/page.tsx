"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { setSession } from "@/lib/auth";

export default function Page() {
  return (
    <Suspense fallback={null}>
      <Login />
    </Suspense>
  );
}

function Login() {
  const router = useRouter();
  const params = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [demo, setDemo] = useState<{ username: string; password: string; role: string }[]>([]);

  useEffect(() => {
    api.demoAccounts().then(setDemo).catch(() => {});
  }, []);

  async function submit(u = username, p = password) {
    setBusy(true);
    setError("");
    try {
      const s = await api.login(u, p);
      setSession(s);
      const next = params.get("keyin");
      router.push(next || (s.role === "customs" ? "/bojxona" : s.role === "manufacturer" ? "/manufacturer" : "/inspektor"));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Xodimlar uchun kirish</h1>
        <p className="text-sm text-gray-600">
          Inspektor, bojxona va ishlab chiqaruvchi panellari uchun. Xaridorlarga kirish shart emas: qutini tekshirish anonim.
        </p>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="space-y-3 rounded-2xl border border-gray-200 bg-white p-5"
      >
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Login" autoCapitalize="none"
          className="w-full rounded-lg border border-gray-300 px-3 py-2" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Parol" type="password"
          className="w-full rounded-lg border border-gray-300 px-3 py-2" />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button disabled={busy} className="w-full rounded-lg bg-brand-500 py-2 font-medium text-white disabled:opacity-50">
          {busy ? "…" : "Kirish"}
        </button>
      </form>
      {demo.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm">
          <div className="mb-2 font-medium text-amber-900">Demo hisoblar (hakamlar uchun)</div>
          <ul className="space-y-1">
            {demo.map((d) => (
              <li key={d.username} className="flex items-center justify-between gap-2">
                <span>
                  {d.role}: <code>{d.username}</code> / <code>{d.password}</code>
                </span>
                <button onClick={() => submit(d.username, d.password)} className="rounded bg-white px-2 py-0.5 text-xs ring-1 ring-amber-300">
                  Kirish
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
