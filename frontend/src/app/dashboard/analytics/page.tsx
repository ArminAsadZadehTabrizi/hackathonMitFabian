import type { Metadata } from 'next';

import { CONFIG } from 'src/global-config';

import { BookkeepingAnalyticsView } from 'src/sections/bookkeeping/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `Analytics | Dashboard - ${CONFIG.appName}` };

export default function Page() {
  return <BookkeepingAnalyticsView />;
}
