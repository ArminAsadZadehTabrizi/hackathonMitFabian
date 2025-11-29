import type { Metadata } from 'next';

import { CONFIG } from 'src/global-config';

import { VendorsView } from 'src/sections/bookkeeping/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `Vendors | Dashboard - ${CONFIG.appName}` };

export default function Page() {
  return <VendorsView />;
}

