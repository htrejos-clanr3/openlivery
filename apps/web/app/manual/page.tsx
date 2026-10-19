"use client";

import Link from "next/link";
import { BookOpen, CheckCircle2, ExternalLink, Printer } from "lucide-react";
import { useLanguage } from "@/lib/i18n";
import { manualGuide } from "@/lib/manual-guide";

export default function ManualPage() {
  const { lang } = useLanguage();
  const copy = manualGuide[lang];

  return (
    <div className="page-form">
      <section className="form-section">
        <div className="section-copy">
          <small>{copy.eyebrow}</small>
          <h1 style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <BookOpen size={22} /> {copy.title}
          </h1>
          <p>{copy.intro}</p>
        </div>
        <div className="form-fields">
          <button type="button" className="button" onClick={() => window.print()}>
            <Printer size={16} /> {copy.printLabel}
          </button>
        </div>
      </section>

      <section className="form-section">
        <div className="section-copy">
          <h2>{copy.whatTitle}</h2>
        </div>
        <div className="form-fields">
          <ul>
            {copy.what.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <nav aria-label={copy.stepsTitle}>
            <ol style={{ columns: 2, margin: 0, paddingLeft: 20 }}>
              {copy.steps.map((step, index) => (
                <li key={step.title}>
                  <a href={`#step-${index + 1}`}>{step.title}</a>
                </li>
              ))}
            </ol>
          </nav>
        </div>
      </section>

      <section className="form-section">
        <div className="section-copy">
          <h2>{copy.stepsTitle}</h2>
          <p>{copy.stepsIntro}</p>
        </div>
        <div className="form-fields">
          <ol style={{ margin: 0, paddingLeft: 22, display: "grid", gap: 18 }}>
            {copy.steps.map((step, index) => (
              <li key={step.title} id={`step-${index + 1}`}>
                <h3 style={{ margin: "0 0 6px" }}>{step.title}</h3>
                <ul style={{ margin: "0 0 8px", paddingLeft: 18 }}>
                  {step.body.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
                <p style={{ display: "flex", alignItems: "center", gap: 6, margin: "0 0 8px" }}>
                  <CheckCircle2 size={15} /> <strong>{copy.resultLabel}:</strong> {step.result}
                </p>
                <Link className="button" href={step.href}>
                  <ExternalLink size={14} /> {copy.openLabel}
                </Link>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="form-section">
        <div className="section-copy">
          <h2>{copy.integrationsTitle}</h2>
          <p>{copy.integrationsIntro}</p>
        </div>
        <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>{copy.colName}</th>
                <th>{copy.colWhat}</th>
                <th>{copy.colWhere}</th>
                <th>{copy.colNeeds}</th>
              </tr>
            </thead>
            <tbody>
              {copy.integrations.map((item) => (
                <tr key={item.name}>
                  <td>
                    <strong>{item.name}</strong>
                  </td>
                  <td>{item.what}</td>
                  <td>{item.where}</td>
                  <td>{item.needs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="form-section">
        <div className="section-copy">
          <h2>{copy.errorsTitle}</h2>
        </div>
        <div className="form-fields">
          <dl style={{ display: "grid", gap: 10, margin: 0 }}>
            {copy.errors.map((item) => (
              <div key={item.problem}>
                <dt>
                  <strong>{item.problem}</strong>
                </dt>
                <dd style={{ margin: "2px 0 0" }}>{item.fix}</dd>
              </div>
            ))}
          </dl>
          <p className="field-help">{copy.footer}</p>
        </div>
      </section>
    </div>
  );
}
