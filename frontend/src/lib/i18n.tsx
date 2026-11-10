"use client";

import { createContext, useContext, useState, useEffect, type ReactNode } from "react";

export type Lang = "en" | "es";

const dict = {
  en: {
    "nav.tagline": "what the AI read, what the engine verified, what you authorized",
    "nav.cases": "Cases",

    "landing.badge": "PayPal Hackathon · AI + real PayPal",
    "landing.title1": "Evidence, verified.",
    "landing.title2": "Authorization, yours.",
    "landing.subtitle": "Durin shows what the AI read in your invoices, what the deterministic engine verified against your real PayPal activity, and what you actually authorized — as one clear journey per payment, exceptions never mixed in with what's reconciled.",
    "landing.cta": "Enter Durin",
    "landing.ctaSecondary": "How it works",
    "landing.feature1.title": "What the AI read",
    "landing.feature1.desc": "Every extracted field is grounded in the exact excerpt from your source. No citation, no acceptance.",
    "landing.feature2.title": "What the engine verified",
    "landing.feature2.desc": "Deterministic checks catch contradictions, duplicates, and policy violations before anything reaches a proposal.",
    "landing.feature3.title": "What you authorized",
    "landing.feature3.desc": "No payment leaves Durin without your explicit, signed approval. PayPal stays the source of truth.",
    "landing.chat.eyebrow": "Ask about any payment",
    "landing.chat.title": "\"Did we pay them six months ago?\"",
    "landing.chat.desc": "Stop scrolling hundreds of transactions by hand. Ask in plain language and Durin searches your real PayPal history — the model proposes what to search for, never the answer itself.",

    "hero.step1Label": "Evidence received",
    "hero.step1Sub": "source hashed, cited",
    "hero.step2Label": "AI extraction",
    "hero.step2Sub": "every field, grounded",
    "hero.step3Label": "Contradiction check",
    "hero.step3Sub": "deterministic, not guessed",
    "hero.step4Label": "PayPal result",
    "hero.step4Sub": "real sandbox payout",
    "hero.sealedCase": "live case",
    "hero.live": "live",

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

    "summary.title": "Decision summary",
    "summary.stage": "Stage",
    "summary.of": "of",
    "summary.amount.proposal": "Sealed proposal total",
    "summary.amount.ready": "Ready to propose",
    "summary.amount.none": "Nothing is ready to pay",
    "summary.supplier": "Supplier",
    "summary.suppliers": "suppliers",
    "summary.invoices": "Invoices",
    "summary.included": "included",
    "summary.excluded": "excluded",
    "summary.contradictions": "Contradictions",
    "summary.extractionFailures": "Sources that failed extraction",
    "summary.uncited": "Invoices needing source review",
    "summary.digest": "Proposal digest",
    "summary.paypal": "PayPal batch",
    "summary.submissionError": "Not confirmed by PayPal",
    "summary.next": "Next step",
    "summary.doneBy": "Owner:",
    "summary.note": "Read-only view of the stored case. Every action happens in the journey, next to its evidence.",

    "next.PREPARE_PROPOSAL": "Prepare proposal",
    "next.REVIEW_EXCEPTIONS": "Review exceptions",
    "next.REVIEW_EXTRACTION": "Review extraction",
    "next.REVIEW_AND_APPROVE": "Review and approve",
    "next.SUBMIT_TO_PAYPAL": "Submit to PayPal",
    "next.RESOLVE_SUBMISSION": "Check PayPal submission",
    "next.REFRESH_PAYPAL": "Refresh PayPal status",
    "next.NONE": "No action pending",

    "actors.legend": "Who does what",
    "actor.source": "Sources arrive",
    "actor.ai": "AI reads",
    "actor.engine": "Engine verifies",
    "actor.human": "You authorize",
    "actor.paypal": "PayPal executes",
    "actorChip.source": "Source",
    "actorChip.ai": "AI",
    "actorChip.engine": "Engine",
    "actorChip.human": "You",
    "actorChip.paypal": "PayPal",

    "journey.stepsHeading": "Evidence journey",
    "journey.step6.uncertain": "PayPal did not confirm this submission, so its outcome is unknown. Sending again reuses the same batch ID.",
    "journey.step6.httpStatus": "HTTP status",
    "journey.step6.noStatus": "no response",

    "evidence.excerptLabel": "Source excerpt:",
    "evidence.statusLabel": "Citation:",

    "view.all": "All cases",
    "view.needsReview": "Needs review",
    "view.awaitingApproval": "Awaiting approval",
    "view.submitted": "Sent to PayPal",
    "view.uncertain": "Submission uncertain",
    "view.reconciled": "Reconciled",
    "dashboard.viewsLabel": "Views",
    "dashboard.queueHeading": "Work queue",
    "filter.stage": "Stage",
    "filter.stageAny": "Any stage",
    "filter.date": "Created",
    "filter.date.any": "Any time",
    "filter.date.24h": "Last 24 hours",
    "filter.date.7d": "Last 7 days",
    "filter.date.30d": "Last 30 days",
    "filter.clear": "Clear filters",
    "filter.showing": "Showing",
    "filter.of": "of",
    "filter.cases": "case(s)",
    "filter.noMatch": "No cases match these filters.",

    "caseCard.suppliers": "suppliers",
    "caseCard.readyTotal": "Ready total",
    "caseCard.next": "Next:",

    "runForm.label": "Source folder",
    "approve.label": "Approver identity",

    "chat.inputLabel": "Your question",
    "chat.examples": "Try asking",
    "chat.example1": "Did we pay Acme six months ago?",
    "chat.example2": "Find payments near USD 450.",
    "chat.example3": "Show transactions for supplier@example.com.",
    "chat.scope": "Search only. This chat cannot approve, submit, refund, or change a case.",

    "activity.title": "Activity record",
    "activity.subtitle": "Built from the case's stored records, in lifecycle order. The summaries are not the evidence; open the raw record to check each one.",
    "activity.raw": "Raw record",
    "activity.noTime": "time not recorded",
    "activity.intake": "Sources received",
    "activity.extraction": "Extraction finished",
    "activity.verification": "Deterministic checks run",
    "activity.proposal": "Proposal sealed",
    "activity.authorization": "Payment authorized",
    "activity.submitFailed": "Submission not confirmed by PayPal",
    "activity.submitted": "Batch accepted by PayPal",
    "activity.providerState": "Latest PayPal state",
    "activity.reconciled": "Rows reconciled against PayPal",
    "activity.extracted": "extracted",
    "activity.rejected": "rejected",
    "activity.items": "item(s)",

    "offline.title": "Backend not reachable",
    "offline.desc": "This preview isn't connected to a live Durin backend yet, so there's no case data to show here. The landing page works on its own; cases and the chat need api_server.py running and reachable.",

    "chat.title": "Ask about a payment",
    "chat.subtitle": "Search real PayPal transaction history in natural language.",
    "chat.placeholder": "e.g. \"Did we pay Acme around $450 a few months ago?\"",
    "chat.send": "Ask",
    "chat.sending": "Searching…",
    "chat.empty": "Ask about a client or supplier payment — I'll search your real PayPal history, not guess.",
    "chat.scanned": "scanned",
    "chat.transactions": "transaction(s)",
    "chat.over": "over",
    "chat.months": "month(s)",
    "chat.open": "Open chat",
    "chat.close": "Close chat",
  },
  es: {
    "nav.tagline": "lo que la IA leyó, lo que el motor verificó, lo que vos autorizaste",
    "nav.cases": "Casos",

    "landing.badge": "PayPal Hackathon · IA + PayPal real",
    "landing.title1": "Evidencia, verificada.",
    "landing.title2": "Autorización, tuya.",
    "landing.subtitle": "Durin muestra lo que la IA leyó en tus facturas, lo que el motor determinístico verificó contra tu actividad real de PayPal, y lo que vos realmente autorizaste — un recorrido claro por cada pago, sin mezclar excepciones con lo conciliado.",
    "landing.cta": "Entrar a Durin",
    "landing.ctaSecondary": "Cómo funciona",
    "landing.feature1.title": "Lo que la IA leyó",
    "landing.feature1.desc": "Cada campo extraído está fundado en la cita exacta de tu fuente. Sin cita, no se acepta.",
    "landing.feature2.title": "Lo que el motor verificó",
    "landing.feature2.desc": "Chequeos determinísticos atrapan contradicciones, duplicados y violaciones de política antes de que algo llegue a una propuesta.",
    "landing.feature3.title": "Lo que vos autorizaste",
    "landing.feature3.desc": "Ningún pago sale de Durin sin tu aprobación explícita y firmada. PayPal sigue siendo la fuente de verdad.",
    "landing.chat.eyebrow": "Preguntá por cualquier pago",
    "landing.chat.title": "\"¿Le pagamos hace seis meses?\"",
    "landing.chat.desc": "Dejá de buscar a mano entre cientos de transacciones. Preguntá en lenguaje natural y Durin busca en tu historial real de PayPal — el modelo propone qué buscar, nunca la respuesta en sí.",

    "hero.step1Label": "Evidencia recibida",
    "hero.step1Sub": "fuente hasheada y citada",
    "hero.step2Label": "Extracción con IA",
    "hero.step2Sub": "cada campo, fundado",
    "hero.step3Label": "Chequeo de contradicciones",
    "hero.step3Sub": "determinístico, no adivinado",
    "hero.step4Label": "Resultado en PayPal",
    "hero.step4Sub": "payout real de sandbox",
    "hero.sealedCase": "caso en vivo",
    "hero.live": "en vivo",

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

    "summary.title": "Resumen de decisión",
    "summary.stage": "Etapa",
    "summary.of": "de",
    "summary.amount.proposal": "Total de la propuesta sellada",
    "summary.amount.ready": "Listo para proponer",
    "summary.amount.none": "No hay nada listo para pagar",
    "summary.supplier": "Proveedor",
    "summary.suppliers": "proveedores",
    "summary.invoices": "Facturas",
    "summary.included": "incluidas",
    "summary.excluded": "excluidas",
    "summary.contradictions": "Contradicciones",
    "summary.extractionFailures": "Fuentes que fallaron en la extracción",
    "summary.uncited": "Facturas que requieren revisar la fuente",
    "summary.digest": "Digest de la propuesta",
    "summary.paypal": "Batch de PayPal",
    "summary.submissionError": "Sin confirmación de PayPal",
    "summary.next": "Próximo paso",
    "summary.doneBy": "Responsable:",
    "summary.note": "Vista de solo lectura del caso guardado. Toda acción ocurre en el recorrido, junto a su evidencia.",

    "next.PREPARE_PROPOSAL": "Preparar propuesta",
    "next.REVIEW_EXCEPTIONS": "Revisar excepciones",
    "next.REVIEW_EXTRACTION": "Revisar extracción",
    "next.REVIEW_AND_APPROVE": "Revisar y aprobar",
    "next.SUBMIT_TO_PAYPAL": "Enviar a PayPal",
    "next.RESOLVE_SUBMISSION": "Verificar el envío a PayPal",
    "next.REFRESH_PAYPAL": "Refrescar estado en PayPal",
    "next.NONE": "Sin acciones pendientes",

    "actors.legend": "Quién hace qué",
    "actor.source": "Llegan las fuentes",
    "actor.ai": "La IA lee",
    "actor.engine": "El motor verifica",
    "actor.human": "Vos autorizás",
    "actor.paypal": "PayPal ejecuta",
    "actorChip.source": "Fuente",
    "actorChip.ai": "IA",
    "actorChip.engine": "Motor",
    "actorChip.human": "Vos",
    "actorChip.paypal": "PayPal",

    "journey.stepsHeading": "Recorrido de evidencia",
    "journey.step6.uncertain": "PayPal no confirmó este envío, así que su resultado es desconocido. Enviar de nuevo reutiliza el mismo ID de batch.",
    "journey.step6.httpStatus": "Estado HTTP",
    "journey.step6.noStatus": "sin respuesta",

    "evidence.excerptLabel": "Cita de la fuente:",
    "evidence.statusLabel": "Cita:",

    "view.all": "Todos los casos",
    "view.needsReview": "Requiere revisión",
    "view.awaitingApproval": "Esperando aprobación",
    "view.submitted": "Enviado a PayPal",
    "view.uncertain": "Envío incierto",
    "view.reconciled": "Conciliado",
    "dashboard.viewsLabel": "Vistas",
    "dashboard.queueHeading": "Cola de trabajo",
    "filter.stage": "Etapa",
    "filter.stageAny": "Cualquier etapa",
    "filter.date": "Creado",
    "filter.date.any": "Cualquier fecha",
    "filter.date.24h": "Últimas 24 horas",
    "filter.date.7d": "Últimos 7 días",
    "filter.date.30d": "Últimos 30 días",
    "filter.clear": "Limpiar filtros",
    "filter.showing": "Mostrando",
    "filter.of": "de",
    "filter.cases": "caso(s)",
    "filter.noMatch": "Ningún caso coincide con estos filtros.",

    "caseCard.suppliers": "proveedores",
    "caseCard.readyTotal": "Total listo",
    "caseCard.next": "Sigue:",

    "runForm.label": "Carpeta de fuentes",
    "approve.label": "Identidad de quien aprueba",

    "chat.inputLabel": "Tu pregunta",
    "chat.examples": "Probá preguntar",
    "chat.example1": "¿Le pagamos a Acme hace seis meses?",
    "chat.example2": "Buscá pagos cercanos a USD 450.",
    "chat.example3": "Mostrá las transacciones de supplier@example.com.",
    "chat.scope": "Solo búsqueda. Este chat no puede aprobar, enviar, reembolsar ni modificar un caso.",

    "activity.title": "Registro de actividad",
    "activity.subtitle": "Armado a partir de los registros guardados del caso, en orden de ciclo de vida. Los resúmenes no son la evidencia; abrí el registro crudo para verificar cada uno.",
    "activity.raw": "Registro crudo",
    "activity.noTime": "hora no registrada",
    "activity.intake": "Fuentes recibidas",
    "activity.extraction": "Extracción terminada",
    "activity.verification": "Chequeos determinísticos ejecutados",
    "activity.proposal": "Propuesta sellada",
    "activity.authorization": "Pago autorizado",
    "activity.submitFailed": "Envío sin confirmación de PayPal",
    "activity.submitted": "Batch aceptado por PayPal",
    "activity.providerState": "Último estado en PayPal",
    "activity.reconciled": "Filas conciliadas contra PayPal",
    "activity.extracted": "extraída(s)",
    "activity.rejected": "rechazada(s)",
    "activity.items": "ítem(s)",

    "offline.title": "No se puede conectar al backend",
    "offline.desc": "Este preview todavía no está conectado a un backend de Durin en vivo, así que no hay datos de casos para mostrar acá. La landing funciona sola; los casos y el chat necesitan api_server.py corriendo y accesible.",

    "chat.title": "Preguntá por un pago",
    "chat.subtitle": "Buscá en el historial real de PayPal en lenguaje natural.",
    "chat.placeholder": "ej. \"¿Le pagamos a Acme unos 450 hace unos meses?\"",
    "chat.send": "Preguntar",
    "chat.sending": "Buscando…",
    "chat.empty": "Preguntá por un pago a un cliente o proveedor — busco en tu historial real de PayPal, no adivino.",
    "chat.scanned": "revisadas",
    "chat.transactions": "transacción(es)",
    "chat.over": "en",
    "chat.months": "mes(es)",
    "chat.open": "Abrir chat",
    "chat.close": "Cerrar chat",
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

  // Keep the document language in step with the toggle, so assistive tech
  // pronounces Spanish copy as Spanish (layout.tsx can only ship "en").
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

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
