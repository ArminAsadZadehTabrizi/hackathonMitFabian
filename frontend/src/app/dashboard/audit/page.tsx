import type { Metadata } from 'next';

import { CONFIG } from 'src/global-config';

import { AuditView } from 'src/sections/bookkeeping/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `Audit | Dashboard - ${CONFIG.appName}` };

export default function Page() {
  return <AuditView />;
}

