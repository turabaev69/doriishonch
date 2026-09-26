"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getSession, Session, setSession } from "@/lib/auth";

export function NavUser() {
  const [s, setS] = useState<Session | null>(null);
  useEffect(() => {
    const update = () => setS(getSession());
    update();
    window.addEventListener("doriishonch-auth", update);
    return () => window.removeEventListener("doriishonch-auth", update);
  }, []);
  if (!s)
    return (
      <Link href="/kirish" className="whitespace-nowrap text-gray-500 hover:text-brand-700">
        Xodimlar
      </Link>
    );
  return (
    <button onClick={() => setSession(null)} className="whitespace-nowrap text-gray-500 hover:text-red-700" title="Chiqish">
      {s.username} ✕
    </button>
  );
}
