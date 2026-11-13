"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, CalendarDays, Check, LoaderCircle, Plus } from "lucide-react";
import { api, messageFrom } from "@/lib/api";
import { useToast } from "@/components/toast";

type Rule = { weekday: number; start_time: string; end_time: string; slot_minutes: number; buffer_minutes: number; is_active: boolean };
type Appointment = { id: string; starts_at: string; ends_at: string; status: string; source: string };

const DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

export default function ClientAgendaPage() {
  const params = useParams<{ id: string }>();
  const clientId = params?.id ?? "";
  const toast = useToast();
  const [rules, setRules] = useState<Rule[]>([]);
  const [timezone, setTimezone] = useState("America/Bogota");
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [slotMinutes, setSlotMinutes] = useState(60);
  const [buffer, setBuffer] = useState(0);
  const [activeDays, setActiveDays] = useState<number[]>([0, 1, 2, 3, 4]);
  const [openTime, setOpenTime] = useState("09:00");
  const [closeTime, setCloseTime] = useState("12:00");
  const [newStart, setNewStart] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const [availability, list] = await Promise.all([
        api<{ timezone: string; rules: Rule[] }>(`/clients/${clientId}/availability`),
        api<Appointment[]>(`/clients/${clientId}/appointments`),
      ]);
      setTimezone(availability.timezone || "America/Bogota");
      setRules(availability.rules || []);
      if (availability.rules?.length) {
        const rule = availability.rules[0];
        setSlotMinutes(rule.slot_minutes);
        setBuffer(rule.buffer_minutes);
        setOpenTime(rule.start_time.slice(0, 5));
        setCloseTime(rule.end_time.slice(0, 5));
        setActiveDays(availability.rules.map((item) => item.weekday));
      }
      setAppointments(list || []);
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setBusy(false);
    }
  }, [clientId, toast]);

  useEffect(() => {
    if (clientId) void load();
  }, [clientId, load]);

  async function saveHours() {
    setSaving(true);
    try {
      await api(`/clients/${clientId}/availability`, {
        method: "PUT",
        body: JSON.stringify({
          timezone,
          rules: activeDays.map((weekday) => ({
            weekday,
            start_time: `${openTime}:00`,
            end_time: `${closeTime}:00`,
            slot_minutes: slotMinutes,
            buffer_minutes: buffer,
            is_active: true,
          })),
        }),
      });
      toast.success("Horario guardado");
      void load();
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setSaving(false);
    }
  }

  async function book() {
    if (!newStart) return;
    setSaving(true);
    try {
      await api(`/clients/${clientId}/appointments`, {
        method: "POST",
        body: JSON.stringify({ starts_at: new Date(newStart).toISOString(), duration: slotMinutes, source: "panel" }),
      });
      toast.success("Cita agendada");
      setNewStart("");
      void load();
    } catch (err) {
      toast.error(messageFrom(err));
    } finally {
      setSaving(false);
    }
  }

  async function cancel(id: string) {
    try {
      await api(`/clients/${clientId}/appointments/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "cancelled", reason: "panel" }),
      });
      void load();
    } catch (err) {
      toast.error(messageFrom(err));
    }
  }

  const upcoming = useMemo(
    () => appointments.filter((item) => item.status === "scheduled" || item.status === "rescheduled"),
    [appointments],
  );

  return (
    <div className="page-form">
      <section style={{ display: "flex", gap: 20, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", padding: "18px 20px", border: "1px solid #e4e8ee", borderRadius: 14, background: "#fff" }}>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <span aria-hidden style={{ width: 44, height: 44, borderRadius: 12, display: "grid", placeItems: "center", background: "#e0f2fe", color: "#0369a1", flex: "none" }}>
            <CalendarDays size={22} />
          </span>
          <div>
            <small className="field-help" style={{ textTransform: "uppercase", letterSpacing: ".05em", fontSize: 11 }}>Agenda del cliente</small>
            <h1 style={{ margin: "2px 0 0", fontSize: 22 }}>Citas y disponibilidad</h1>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="pill ok">{upcoming.length} próximas</span>
          <Link className="button" href={`/clients/${clientId}`}><ArrowLeft size={15} /> Volver</Link>
        </div>
      </section>

      <section style={{ border: "1px solid #e4e8ee", borderRadius: 14, padding: "18px 20px", background: "#fff" }}>
        <strong style={{ display: "block", marginBottom: 4 }}>Horario de atención</strong>
        <p className="field-help" style={{ margin: "0 0 12px" }}>Se aplica a todos los días marcados. El agente solo ofrece huecos dentro de este horario.</p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
          {DAYS.map((day, index) => {
            const active = activeDays.includes(index);
            return (
              <button key={day} type="button" className={active ? "button primary" : "button"} onClick={() => setActiveDays(active ? activeDays.filter((d) => d !== index) : [...activeDays, index].sort())}>
                {day}
              </button>
            );
          })}
        </div>
        <div style={{ display: "grid", gap: 10, gridTemplateColumns: "repeat(auto-fit,minmax(150px,1fr))", maxWidth: 720 }}>
          <label className="field">Desde<input type="time" value={openTime} onChange={(e) => setOpenTime(e.target.value)} /></label>
          <label className="field">Hasta<input type="time" value={closeTime} onChange={(e) => setCloseTime(e.target.value)} /></label>
          <label className="field">Duración (min)<input type="number" min={15} step={15} value={slotMinutes} onChange={(e) => setSlotMinutes(Number(e.target.value))} /></label>
          <label className="field">Buffer (min)<input type="number" min={0} step={15} value={buffer} onChange={(e) => setBuffer(Number(e.target.value))} /></label>
          <label className="field">Zona horaria<input value={timezone} onChange={(e) => setTimezone(e.target.value)} /></label>
        </div>
        <button type="button" className="button primary" style={{ marginTop: 12 }} onClick={saveHours} disabled={saving || activeDays.length === 0}>
          {saving ? <LoaderCircle className="spin" size={15} /> : <Check size={15} />} Guardar horario
        </button>
      </section>

      <section style={{ border: "1px solid #e4e8ee", borderRadius: 14, padding: "18px 20px", background: "#fff" }}>
        <strong style={{ display: "block", marginBottom: 4 }}>Agendar una cita</strong>
        <p className="field-help" style={{ margin: "0 0 12px" }}>Se valida contra el horario: si el hueco está ocupado, se rechaza.</p>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <input type="datetime-local" value={newStart} onChange={(e) => setNewStart(e.target.value)} style={{ padding: "10px 12px", border: "1px solid #d7dde5", borderRadius: 10 }} />
          <button type="button" className="button primary" onClick={book} disabled={saving || !newStart}>
            <Plus size={15} /> Agendar
          </button>
        </div>
      </section>

      <section style={{ border: "1px solid #e4e8ee", borderRadius: 14, padding: "18px 20px", background: "#fff" }}>
        <strong style={{ display: "block", marginBottom: 10 }}>Próximas citas</strong>
        {busy ? (
          <span className="field-help"><LoaderCircle className="spin" size={15} /> Cargando…</span>
        ) : upcoming.length === 0 ? (
          <p className="field-help" style={{ margin: 0 }}>Sin citas agendadas.</p>
        ) : (
          <ul style={{ listStyle: "none", margin: 0, padding: 0, display: "grid", gap: 8 }}>
            {upcoming.map((item) => (
              <li key={item.id} style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", border: "1px solid #f1f5f9", borderRadius: 10, padding: "10px 12px" }}>
                <span>
                  <strong style={{ display: "block", fontSize: 14 }}>{new Date(item.starts_at).toLocaleString()}</strong>
                  <small className="field-help">Origen: {item.source}</small>
                </span>
                <button type="button" className="button" onClick={() => cancel(item.id)}>Cancelar</button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
