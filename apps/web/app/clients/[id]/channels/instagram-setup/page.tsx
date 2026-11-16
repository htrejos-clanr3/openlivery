"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { LoaderCircle } from "lucide-react";

/**
 * Retired: the single configuration screen replaced this wizard.
 * Kept as a redirect so old links and bookmarks do not break.
 */
export default function InstagramSetupRedirect() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const clientId = params?.id ?? "";

  useEffect(() => {
    if (clientId) router.replace(`/clients/${clientId}/channels/instagram-config`);
  }, [clientId, router]);

  return (
    <div className="page-loading">
      <LoaderCircle className="spin" /> Abriendo la configuración de Instagram…
    </div>
  );
}
