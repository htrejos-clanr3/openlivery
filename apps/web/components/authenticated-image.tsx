"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

type AuthenticatedImageProps = {
  src: string;
  alt?: string;
  className?: string;
  onReady?: () => void;
  onError?: () => void;
};

/** Fetches protected /api/* images with session cookies (plain img tags omit auth). */
export function AuthenticatedImage({ src, alt = "", className, onReady, onError }: AuthenticatedImageProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!src) return;
    let revoked: string | null = null;
    let cancelled = false;
    const url = src.startsWith("http") ? src : `${API_URL}${src}`;

    fetch(url, { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.blob();
      })
      .then((blob) => {
        if (cancelled) return;
        const objectUrl = URL.createObjectURL(blob);
        revoked = objectUrl;
        setBlobUrl(objectUrl);
        onReady?.();
      })
      .catch(() => {
        if (!cancelled) onError?.();
      });

    return () => {
      cancelled = true;
      if (revoked) URL.revokeObjectURL(revoked);
      setBlobUrl(null);
    };
  }, [src]);

  if (!blobUrl) return null;
  return <img src={blobUrl} alt={alt} className={className} />;
}
