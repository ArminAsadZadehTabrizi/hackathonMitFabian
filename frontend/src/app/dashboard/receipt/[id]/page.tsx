import type { Metadata } from 'next';

import { CONFIG } from 'src/global-config';

import { ReceiptDetailsView } from 'src/sections/receipt/view';

// ----------------------------------------------------------------------

export const metadata: Metadata = { title: `Receipt Details | Dashboard - ${CONFIG.appName}` };

type Props = {
  params: Promise<{ id: string }>;
};

export default async function Page({ params }: Props) {
  const { id } = await params;
  return <ReceiptDetailsView id={id} />;
}

