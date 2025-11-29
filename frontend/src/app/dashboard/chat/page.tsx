import type { Metadata } from 'next';

import { CONFIG } from 'src/global-config';

import { AIAuditorView } from 'src/sections/bookkeeping/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `AI Auditor | Dashboard - ${CONFIG.appName}` };

export default function Page() {
  return <AIAuditorView />;
}
