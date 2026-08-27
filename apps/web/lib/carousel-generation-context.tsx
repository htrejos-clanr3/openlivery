"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useT } from "@/lib/i18n";

export type CarouselGenerationJob = {
  carouselId: string;
  clientId: string;
  title: string;
  startedAt: number;
  abort: () => void;
};

type CarouselGenerationContextValue = {
  jobs: CarouselGenerationJob[];
  activeCount: number;
  register: (job: CarouselGenerationJob) => void;
  unregister: (carouselId: string) => void;
  abortAll: () => void;
};

const CarouselGenerationContext = createContext<CarouselGenerationContextValue | null>(null);

export function CarouselGenerationProvider({ children }: { children: ReactNode }) {
  const t = useT();
  const [jobs, setJobs] = useState<CarouselGenerationJob[]>([]);

  const register = useCallback((job: CarouselGenerationJob) => {
    setJobs((prev) => [...prev.filter((item) => item.carouselId !== job.carouselId), job]);
  }, []);

  const unregister = useCallback((carouselId: string) => {
    setJobs((prev) => prev.filter((item) => item.carouselId !== carouselId));
  }, []);

  const abortAll = useCallback(() => {
    setJobs((prev) => {
      prev.forEach((job) => job.abort());
      return [];
    });
  }, []);

  useEffect(() => {
    if (!jobs.length) return;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = t("carousels.generation.leaveWarning");
      jobs.forEach((job) => job.abort());
    };
    const onPageHide = () => jobs.forEach((job) => job.abort());
    window.addEventListener("beforeunload", onBeforeUnload);
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      window.removeEventListener("pagehide", onPageHide);
    };
  }, [jobs, t]);

  const value = useMemo(
    () => ({ jobs, activeCount: jobs.length, register, unregister, abortAll }),
    [jobs, register, unregister, abortAll],
  );

  return <CarouselGenerationContext.Provider value={value}>{children}</CarouselGenerationContext.Provider>;
}

export function useCarouselGeneration() {
  const ctx = useContext(CarouselGenerationContext);
  if (!ctx) throw new Error("useCarouselGeneration requires CarouselGenerationProvider");
  return ctx;
}
