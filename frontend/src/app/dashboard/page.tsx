import type { Metadata } from 'next';

import { CONFIG } from 'src/global-config';

import { OverviewBookkeepingView } from 'src/sections/overview/bookkeeping/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `Dashboard - ${CONFIG.appName}` };

export default function Page() {
  return <OverviewBookkeepingView />;
}
