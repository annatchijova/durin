"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

export type Lang = "en" | "es";

const dict = {
  en: {
    "nav.tagline": "what the AI read, what the engine verified, what you authorized",
    "nav.cases": "Cases",

    "dashboard.title": "Cases",
    "dashboard.subtitle": "Each case is a batch of invoices walking the same path: evidence, extraction, contradictions, proposal, approval, PayPal.",
    "dashboard.empty": "No cases yet. Run extraction above to start one.",

    "runForm.title": "Process a batch of invoices",
    "runForm.hint": "Leave empty to use DURIN_SOURCE_DIR, or point to a folder with authorized invoices/emails.",
    "runForm.placeholder": "/path/to/sources (optional)",
    "runForm.submit": "Run extraction",
    "runForm.submitting": "Running…",

    "stage.EXTRACTED": "Extracted",
    "stage.PROPOSED": "Proposal ready",
    "stage.APPROVED": "Approved",
    "stage.SUBMITTED": "Sent to PayPal",
    "stage.SUBMISSION_UNCERTAIN": "Submission uncertain",
    "stage.RECONCILED": "Reconciled",

    "caseCard.ready": "ready",
    "caseCard.excluded": "excluded",
    "caseCard.contradictions": "contradictions",
    "caseCard.viewJourney": "View journey",

    "journey.title": "Invoice journey",
    "journey.sources": "source(s)",
    "journey.step1.title": "Evidence received",
    "journey.step2.title": "Data extracted by the AI",
    "journey.step2.meta": "extracted, rejected",
    "journey.step2.rejectedNote": "source(s) failed extraction and never reached this view.",
    "journey.step3.title": "Contradictions across sources",
    "journey.step3.found": "found",
    "journey.step4.title": "Payment proposal prepared",
    "journey.step4.items": "item(s) · total",
    "journey.step4.digest": "digest",
    "journey.step4.none": "No invoice is ready to be proposed yet.",
    "journey.step4.action": "Prepare proposal",
    "journey.step4.pending": "Preparing…",
    "journey.step5.title": "Human approval",
    "journey.step5.authorizedBy": "Authorized by",
    "journey.step5.on": "on",
    "journey.step5.waiting": "Waiting for a proposal before it can be approved.",
    "journey.step6.title": "Result at PayPal",
    "journey.step6.batch": "batch",
    "journey.step6.action": "Send to PayPal",
    "journey.step6.pending": "Sending…",
    "journey.step6.refresh": "Refresh status at PayPal",
    "journey.step6.waiting": "Waiting for authorization to run the payment.",

    "identity.supplierConflict": "This invoice number appears with more than one supplier across sources.",
    "identity.factsConflict": "This supplier and invoice number have different amounts or currencies between rows.",
    "identity.excludedNote": "excluded, see detail below.",

    "exceptions.title": "Exceptions — not reconciled",
    "exceptions.subtitle": "These rows never enter a proposal until a human reviews them. Nothing here was decided by default.",

    "evidence.cited": "Cited",
    "evidence.uncited": "Uncited",

    "field.supplier": "Supplier",
    "field.invoiceNumber": "Invoice #",
    "field.recipient": "Recipient (PayPal)",
    "field.amount": "Amount",
    "field.currency": "Currency",
    "field.dueDate": "Due date",
    "field.concept": "Concept",

    "check.unique": "No duplicates in batch",
    "check.recipient": "Recipient approved",
    "check.limit": "Within payment limit",
    "check.price": "Consistent with history",
    "check.due_date": "Due date",
    "check.invoice_facts": "Invoice data consistent across sources",
    "check.supplier_identity": "Supplier identity consistent",

    "contradiction.none": "No contradictions across sources for this obligation.",
    "contradiction.mismatch": "does not match across sources",
    "contradiction.field.recipient": "Recipient (PayPal)",
    "contradiction.field.dueDate": "Due date",
    "contradiction.field.concept": "Concept",
    "contradiction.source": "source",

    "approve.description": "You are about to authorize a payment of",
    "approve.note": "This action is signed with your identity and cannot be undone without explicit recovery.",
    "approve.placeholder": "your-email@merchant.com",
    "approve.submit": "Authorize payment",
    "approve.required": "Enter who is authorizing this payment",

    "state.ready": "Reconciled",
    "state.exception": "Exception",
    "state.review": "Needs review",
    "state.pending": "Pending",

    "action.genericError": "Something failed",
  },
  es: {
    "nav.tagline": "lo que la IA leyó, lo que el motor verificó, lo que vos autorizaste",
    "nav.cases": "Casos",

    "dashboard.title": "Casos",
    "dashboard.subtitle": "Cada caso es un lote de facturas recorriendo el mismo camino: evidencia, extracción, contradicciones, propuesta, aprobación, PayPal.",
    "dashboard.empty": "Todavía no hay casos. Corré la extracción arriba para empezar uno.",

    "runForm.title": "Procesar un lote de facturas",
    "runForm.hint": "Dejá vacío para usar DURIN_SOURCE_DIR, o indicá una carpeta con facturas/emails autorizados.",
    "runForm.placeholder": "/ruta/a/fuentes (opcional)",
    "runForm.submit": "Correr extracción",
    "runForm.submitting": "Corriendo…",

    "stage.EXTRACTED": "Extraído",
    "stage.PROPOSED": "Propuesta lista",
    "stage.APPROVED": "Aprobado",
    "stage.SUBMITTED": "Enviado a PayPal",
    "stage.SUBMISSION_UNCERTAIN": "Envío incierto",
    "stage.RECONCILED": "Conciliado",

    "caseCard.ready": "listas",
    "caseCard.excluded": "excluidas",
    "caseCard.contradictions": "contradicciones",
    "caseCard.viewJourney": "Ver recorrido",

    "journey.title": "Recorrido de la factura",
    "journey.sources": "fuente(s)",
    "journey.step1.title": "Evidencia recibida",
    "journey.step2.title": "Datos extraídos por la IA",
    "journey.step2.meta": "extraída(s), rechazada(s)",
    "journey.step2.rejectedNote": "fuente(s) fallaron en la extracción y no llegaron a esta vista.",
    "journey.step3.title": "Contradicciones entre fuentes",
    "journey.step3.found": "encontrada(s)",
    "journey.step4.title": "Propuesta de pago preparada",
    "journey.step4.items": "ítem(s) · total",
    "journey.step4.digest": "digest",
    "journey.step4.none": "Ninguna factura está lista para proponerse todavía.",
    "journey.step4.action": "Preparar propuesta",
    "journey.step4.pending": "Preparando…",
    "journey.step5.title": "Aprobación humana",
    "journey.step5.authorizedBy": "Autorizado por",
    "journey.step5.on": "el",
    "journey.step5.waiting": "Esperando una propuesta para poder autorizar.",
    "journey.step6.title": "Resultado en PayPal",
    "journey.step6.batch": "batch",
    "journey.step6.action": "Enviar a PayPal",
    "journey.step6.pending": "Enviando…",
    "journey.step6.refresh": "Refrescar estado en PayPal",
    "journey.step6.waiting": "Esperando autorización para ejecutar el pago.",

    "identity.supplierConflict": "Este número de factura aparece con más de un proveedor entre las fuentes.",
    "identity.factsConflict": "Este proveedor y número de factura tienen montos o monedas distintas entre filas.",
    "identity.excludedNote": "excluida, ver detalle abajo.",

    "exceptions.title": "Excepciones — no conciliadas",
    "exceptions.subtitle": "Estas filas no entran a ninguna propuesta hasta que alguien las revise. Nada acá se decidió por omisión.",

    "evidence.cited": "Citado",
    "evidence.uncited": "Sin cita",

    "field.supplier": "Proveedor",
    "field.invoiceNumber": "N° de factura",
    "field.recipient": "Destinatario (PayPal)",
    "field.amount": "Monto",
    "field.currency": "Moneda",
    "field.dueDate": "Vencimiento",
    "field.concept": "Concepto",

    "check.unique": "Sin duplicados en el lote",
    "check.recipient": "Destinatario aprobado",
    "check.limit": "Dentro del límite de pago",
    "check.price": "Consistente con el historial",
    "check.due_date": "Vencimiento",
    "check.invoice_facts": "Datos de factura consistentes entre fuentes",
    "check.supplier_identity": "Identidad del proveedor consistente",

    "contradiction.none": "Sin contradicciones entre fuentes para esta obligación.",
    "contradiction.mismatch": "no coincide entre fuentes",
    "contradiction.field.recipient": "Destinatario (PayPal)",
    "contradiction.field.dueDate": "Vencimiento",
    "contradiction.field.concept": "Concepto",
    "contradiction.source": "fuente",

    "approve.description": "Vas a autorizar el pago de",
    "approve.note": "Esta acción queda firmada con tu identidad y no se puede deshacer sin un recovery explícito.",
    "approve.placeholder": "tu-email@merchant.com",
    "approve.submit": "Autorizar pago",
    "approve.required": "Ingresá quién autoriza este pago",

    "state.ready": "Conciliado",
    "state.exception": "Excepción",
    "state.review": "Requiere revisión",
    "state.pending": "Pendiente",

    "action.genericError": "Algo falló",
  },
} as const;

type Dict = typeof dict.en;
export type Key = keyof Dict;

interface I18nContextType {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: Key) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const stored = localStorage.getItem("durin-lang") as Lang | null;
    if (stored === "en" || stored === "es") setLangState(stored);
  }, []);

  const setLang = (newLang: Lang) => {
    setLangState(newLang);
    localStorage.setItem("durin-lang", newLang);
  };

  const t = (key: Key): string => dict[lang][key] ?? dict.en[key] ?? key;

  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
