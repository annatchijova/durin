// Mirrors the JSON shapes produced by Durin's Python engine
// (supplier_report.py, source_workflow.py, authorization.py,
// paypal_payouts.py, api_server.py). Kept intentionally loose on fields the
// UI does not read, rather than re-deriving the whole schema here.

export type CheckResult = {
  key: string;
  status: "pass" | "fail" | "alert";
  detail: string;
};

export type Row = {
  invoiceId: string;
  supplier: string;
  invoiceNumber: string;
  recipient: string;
  amount: string;
  currency: string;
  operationState: string;
  reasons: string[];
  checks: CheckResult[];
  status: "READY_FOR_REVIEW" | "EXCLUDED";
  dueDate?: string;
  typoSuggestion?: { recipient: string; distance: number };
  historyAverage?: string;
  priceChangePercent?: string;
  operationIds?: string[];
  recognizedAmount?: string;
};

export type FieldProvenance = {
  value: string;
  provenance: {
    source: string;
    sourceHash: string;
    sourceId: string;
    fieldName: string;
    evidenceExcerpt: string;
    extractionMethod: string;
    extractorVersion: string;
    validationStatus: "SUPPORTED" | "UNSUPPORTED_EVIDENCE";
    requiresReview: boolean;
  };
};

export type ExtractedInvoice = {
  invoiceId: string;
  supplier: string;
  invoiceNumber: string;
  recipient: string;
  amount: string;
  currency: string;
  dueDate?: string;
  concept?: string;
  requiresReview: boolean;
  provenance: Record<string, FieldProvenance>;
};

export type Contradiction = {
  type: "CROSS_SOURCE_FIELD_MISMATCH";
  supplier: string;
  invoiceNumber: string;
  field: string;
  observedValues: { value: string; sources: { invoiceId: string; sourceId: string; sourceHash: string; evidenceExcerpt: string }[] }[];
  requiresReview: boolean;
};

export type SourceManifestEntry = {
  sourceId: string;
  source: string;
  sourceHash: string;
  validationStatus: "EXTRACTED" | "MISSING_EXTRACTION" | "EXTRACTION_REJECTED";
  requiresReview: string;
  rejectionReason?: string;
};

export type Report = {
  schemaVersion: number;
  reportId: string;
  flow: "PAYABLE";
  observedAt: string;
  policy: Record<string, unknown>;
  sourceManifest: SourceManifestEntry[];
  rows: Row[];
  metrics: {
    invoiceCount: number;
    readyCount: number;
    excludedCount: number;
    reasonCounts: Record<string, number>;
    operationStateCounts: Record<string, number>;
    readyAmountsByCurrency: Record<string, string>;
  };
  execution: string;
  humanApprovalRequired: boolean;
  extraction: {
    extractorVersion: string;
    sourceCount: number;
    extractedCount: number;
    missingExtractionCount: number;
    rejectedExtractionCount: number;
    requiresReviewCount: number;
  };
  contradictions: Contradiction[];
  extractedInvoices: ExtractedInvoice[];
};

export type Proposal = {
  schemaVersion: number;
  proposalId: string;
  flow: "PAYABLE";
  items: Row[];
  currency: string;
  totalAmount: string;
  policyVersion: string;
  evidenceRefs: string[];
  createdAt: string;
  expiresAt: string;
  status: "PENDING_APPROVAL" | "APPROVED";
  execution: string;
};

export type Authorization = {
  authorizationId: string;
  proposalId: string;
  proposalDigest: string;
  approverId: string;
  approvedAt: string;
  expiresAt: string;
  status: "APPROVED";
  execution: string;
  authorizationProof: string;
};

export type NormalizedPayout = {
  payoutBatchId: string;
  providerBatchStatus: string;
  reconciliationStatus: string;
  items: { payoutItemId: string; transactionId: string; providerStatus: string; reconciliationStatus: string; error: unknown }[];
  settlementEvidence: string;
};

export type CaseStage = "EXTRACTED" | "PROPOSED" | "APPROVED" | "SUBMITTED" | "SUBMISSION_UNCERTAIN" | "RECONCILED";

export type Case = {
  reportId: string;
  createdAt: string;
  stage: CaseStage;
  report: Report;
  extractionErrors: { sourceId: string; source: string; error: string }[];
  proposal: Proposal | null;
  proposalDigest: string | null;
  authorization: Authorization | null;
  payoutRequest: Record<string, unknown> | null;
  payoutResponse: Record<string, unknown> | null;
  payoutError?: { status: number | null; body: unknown };
  normalizedPayout?: NormalizedPayout;
  reconciledRows?: Row[];
};

export type CaseSummary = {
  reportId: string;
  createdAt: string;
  stage: CaseStage;
  metrics: Report["metrics"];
  contradictionCount: number;
};
