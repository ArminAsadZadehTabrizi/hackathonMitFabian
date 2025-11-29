import type { Metadata } from 'next';

import { CONFIG } from 'src/global-config';

import { ReceiptListView } from 'src/sections/receipt/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `Receipts | Dashboard - ${CONFIG.appName}` };

export default function Page() {
  return <ReceiptListView />;
}

