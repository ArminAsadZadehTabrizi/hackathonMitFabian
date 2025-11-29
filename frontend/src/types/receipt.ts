// ----------------------------------------------------------------------

export type IReceiptLineItem = {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number;
  total: number;
  vat: number;
};

export type IReceiptAuditFlags = {
  isDuplicate: boolean;
  hasTotalMismatch: boolean;
  missingVAT: boolean;
  suspiciousCategory: string | null;
};

export type IReceiptItem = {
  id: string;
  receiptNumber: string;
  vendor: string;
  vendorVAT: string | null;
  date: string;
  total: number;
  subtotal: number;
  vat: number | null;
  vatRate: number | null;
  paymentMethod: string;
  category: string;
  currency: string;
  lineItems: IReceiptLineItem[];
  imageUrl: string | null;
  status: 'verified' | 'duplicate' | 'flagged';
  tags: string[];
  notes: string | null;
  createdAt: string;
  updatedAt: string;
  auditFlags: IReceiptAuditFlags;
};

export type IReceiptTableFilters = {
  vendor: string;
  category: string;
  startDate: Date | null;
  endDate: Date | null;
  status: string;
};

export type IAnalyticsSummary = {
  summary: {
    totalSpending: number;
    totalReceipts: number;
    totalVAT: number;
    avgReceiptValue: number;
  };
  monthly: Array<{
    month: string;
    amount: number;
    count: number;
  }>;
  categories: Array<{
    category: string;
    amount: number;
    count: number;
  }>;
  vendors: Array<{
    vendor: string;
    amount: number;
    count: number;
  }>;
};

export type IAuditFinding = {
  receiptId: string;
  receiptNumber: string;
  vendor: string;
  date: string;
  total: number;
  reason?: string;
  issue?: string;
  category?: string;
  expectedTotal?: number;
  actualTotal?: number;
  difference?: number;
};

export type IAuditFindings = {
  duplicates: IAuditFinding[];
  mismatches: IAuditFinding[];
  missingVAT: IAuditFinding[];
  suspicious: IAuditFinding[];
  summary: {
    totalDuplicates: number;
    totalMismatches: number;
    totalMissingVAT: number;
    totalSuspicious: number;
  };
};

