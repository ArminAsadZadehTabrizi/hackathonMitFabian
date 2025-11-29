'use client';

import type { NavSectionProps } from 'src/components/nav-section';

import { paths } from 'src/routes/paths';

import { CONFIG } from 'src/global-config';
import { useTranslate } from 'src/locales';

import { SvgColor } from 'src/components/svg-color';

// ----------------------------------------------------------------------

const icon = (name: string) => {
  const iconPath = `${CONFIG.assetsDir}/assets/icons/navbar/${name}.svg`;
  return <SvgColor src={iconPath} />;
};

const ICONS = {
  chat: icon('ic-chat'),
  file: icon('ic-file'),
  invoice: icon('ic-invoice'),
  product: icon('ic-product'),
  analytics: icon('ic-analytics'),
};

export function useNavData(): NavSectionProps['data'] {
  const { t } = useTranslate('common');

  return [
    /**
     * Bookkeeping - Auto-Bookkeeper Dashboard
     */
    {
      subheader: t('nav.bookkeeping'),
      items: [
        { title: t('nav.receipts'), path: paths.dashboard.receipt.root, icon: ICONS.invoice },
        { title: t('nav.analytics'), path: paths.dashboard.general.analytics, icon: ICONS.analytics },
        { title: t('nav.vendors'), path: paths.dashboard.vendors.root, icon: ICONS.product },
        { title: t('nav.audit'), path: paths.dashboard.audit.root, icon: ICONS.file },
        { title: t('nav.aiAuditor'), path: paths.dashboard.chat, icon: ICONS.chat },
      ],
    },
  ];
}

