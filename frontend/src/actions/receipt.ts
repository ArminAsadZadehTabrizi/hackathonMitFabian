import type { SWRConfiguration } from 'swr';
import type { IReceiptItem, IAnalyticsSummary, IAuditFindings } from 'src/types/receipt';

import useSWR from 'swr';
import { useMemo } from 'react';

import axiosInstance, { fetcher, endpoints } from 'src/lib/axios';

// ----------------------------------------------------------------------

const swrOptions: SWRConfiguration = {
  revalidateIfStale: false,
  revalidateOnFocus: false,
  revalidateOnReconnect: false,
};

// ----------------------------------------------------------------------

type ReceiptsData = {
  receipts: IReceiptItem[];
};

export function useGetReceipts(filters?: {
  vendor?: string;
  category?: string;
  startDate?: string;
  endDate?: string;
}) {
  const params = new URLSearchParams();
  if (filters?.vendor) params.append('vendor', filters.vendor);
  if (filters?.category) params.append('category', filters.category);
  if (filters?.startDate) params.append('startDate', filters.startDate);
  if (filters?.endDate) params.append('endDate', filters.endDate);

  const url = params.toString() ? `${endpoints.receipts}?${params.toString()}` : endpoints.receipts;

  const { data, isLoading, error, isValidating, mutate } = useSWR<ReceiptsData>(url, fetcher, {
    ...swrOptions,
  });

  const memoizedValue = useMemo(
    () => ({
      receipts: data?.receipts || [],
      receiptsLoading: isLoading,
      receiptsError: error,
      receiptsValidating: isValidating,
      receiptsEmpty: !isLoading && !isValidating && !data?.receipts.length,
      refreshReceipts: mutate,
    }),
    [data?.receipts, error, isLoading, isValidating, mutate]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

type ReceiptData = {
  receipt: IReceiptItem;
};

export function useGetReceipt(receiptId: string) {
  const url = receiptId ? `${endpoints.receipts}?receiptId=${receiptId}` : '';

  const { data, isLoading, error, isValidating } = useSWR<ReceiptData>(url, fetcher, {
    ...swrOptions,
  });

  const memoizedValue = useMemo(
    () => ({
      receipt: data?.receipt,
      receiptLoading: isLoading,
      receiptError: error,
      receiptValidating: isValidating,
    }),
    [data?.receipt, error, isLoading, isValidating]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

type AnalyticsData = IAnalyticsSummary;

export function useGetAnalytics() {
  const url = endpoints.analytics.summary;

  const { data, isLoading, error, isValidating } = useSWR<AnalyticsData>(url, fetcher, {
    ...swrOptions,
  });

  const memoizedValue = useMemo(
    () => ({
      analytics: data,
      analyticsLoading: isLoading,
      analyticsError: error,
      analyticsValidating: isValidating,
    }),
    [data, error, isLoading, isValidating]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

type AuditData = IAuditFindings;

export function useGetAudit() {
  const url = endpoints.audit;

  const { data, isLoading, error, isValidating } = useSWR<AuditData>(url, fetcher, {
    ...swrOptions,
  });

  const memoizedValue = useMemo(
    () => ({
      audit: data,
      auditLoading: isLoading,
      auditError: error,
      auditValidating: isValidating,
    }),
    [data, error, isLoading, isValidating]
  );

  return memoizedValue;
}

// ----------------------------------------------------------------------

type ChatQueryData = {
  answer: string;
  receipts: IReceiptItem[];
  receiptIds: string[];
  totalAmount: number;
  count: number;
};

export function useChatQuery() {
  const queryChat = async (query: string): Promise<ChatQueryData> => {
    const response = await axiosInstance.post<ChatQueryData>(endpoints.chatQuery, { query });
    return response.data;
  };

  return { queryChat };
}

