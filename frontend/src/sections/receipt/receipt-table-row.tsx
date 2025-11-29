import type { GridCellParams } from '@mui/x-data-grid';

import { useState } from 'react';

import Box from '@mui/material/Box';
import Link from '@mui/material/Link';
import Avatar from '@mui/material/Avatar';
import ListItemText from '@mui/material/ListItemText';

import { RouterLink } from 'src/routes/components';

import { fCurrency } from 'src/utils/format-number';
import { fDate, fTime } from 'src/utils/format-time';

import { Label } from 'src/components/label';
import { Iconify } from 'src/components/iconify';

// ----------------------------------------------------------------------

type ParamsProps = {
  params: GridCellParams;
};

export function RenderCellTotal({ params }: ParamsProps) {
  return fCurrency(params.row.total);
}

export function RenderCellStatus({ params }: ParamsProps) {
  const { status } = params.row;
  
  const color =
    status === 'verified' ? 'success' :
    status === 'duplicate' ? 'warning' :
    'error';

  return (
    <Label variant="soft" color={color}>
      {status}
    </Label>
  );
}

export function RenderCellDate({ params }: ParamsProps) {
  return (
    <Box sx={{ gap: 0.5, display: 'flex', flexDirection: 'column' }}>
      <span>{fDate(params.row.date)}</span>
      <Box component="span" sx={{ typography: 'caption', color: 'text.secondary' }}>
        {fTime(params.row.date)}
      </Box>
    </Box>
  );
}

export function RenderCellReceipt({ params, href }: ParamsProps & { href: string }) {
  return (
    <Box
      sx={{
        py: 2,
        gap: 2,
        width: 1,
        display: 'flex',
        alignItems: 'center',
      }}
    >
      {params.row.imageUrl && (
        <Avatar
          alt={params.row.vendor}
          src={params.row.imageUrl}
          variant="rounded"
          sx={{ width: 64, height: 64 }}
        />
      )}

      <ListItemText
        primary={
          <Link component={RouterLink} href={href} color="inherit">
            {params.row.receiptNumber}
          </Link>
        }
        secondary={params.row.vendor}
        slotProps={{
          primary: { noWrap: true, sx: { typography: 'subtitle2' } },
          secondary: { sx: { color: 'text.disabled' } },
        }}
      />
    </Box>
  );
}

export function RenderCellCategory({ params }: ParamsProps) {
  return (
    <Label variant="soft" color="default">
      {params.row.category}
    </Label>
  );
}

export function RenderCellVAT({ params }: ParamsProps) {
  const { vat, vatRate } = params.row;
  
  if (!vat) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'error.main' }}>
        <Iconify icon="solar:danger-triangle-bold" width={16} />
        <span>Missing</span>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
      <span>{fCurrency(vat)}</span>
      <Box component="span" sx={{ typography: 'caption', color: 'text.secondary' }}>
        {vatRate}%
      </Box>
    </Box>
  );
}

export function RenderCellAuditFlags({ params }: ParamsProps) {
  const { auditFlags, lineItems, total, vat } = params.row;
  const [mismatchExpanded, setMismatchExpanded] = useState(false);
  const flags = [];

  // Calculate expected total for mismatch
  const calculateExpectedTotal = () => {
    const subtotal = lineItems.reduce((sum: number, item: any) => sum + item.total, 0);
    const vatAmount = vat || 0;
    return subtotal + vatAmount;
  };

  if (auditFlags.isDuplicate) flags.push('Duplicate');
  if (auditFlags.hasTotalMismatch) {
    const expectedTotal = calculateExpectedTotal();
    const difference = total - expectedTotal;
    flags.push({
      type: 'Mismatch',
      expectedTotal,
      actualTotal: total,
      difference,
    });
  }
  if (auditFlags.missingVAT) flags.push('No VAT');
  if (auditFlags.suspiciousCategory) flags.push('Suspicious');

  if (flags.length === 0) return <span>-</span>;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
      {flags.map((flag, index) => {
        if (typeof flag === 'string') {
          return (
            <Label key={index} variant="soft" color="error" sx={{ fontSize: '0.75rem' }}>
              {flag}
            </Label>
          );
        }
        // Mismatch with expandable details
        return (
          <Box key={index} sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
            <Box
              component="button"
              onClick={(e) => {
                e.stopPropagation();
                setMismatchExpanded(!mismatchExpanded);
              }}
              sx={{
                border: 'none',
                background: 'none',
                padding: 0,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                '&:hover': {
                  opacity: 0.8,
                },
              }}
            >
              <Label variant="soft" color="error" sx={{ fontSize: '0.75rem' }}>
                Mismatch
              </Label>
              <Iconify
                icon={mismatchExpanded ? 'solar:alt-arrow-up-bold' : 'solar:alt-arrow-down-bold'}
                width={14}
                sx={{ color: 'error.main' }}
              />
            </Box>
            {mismatchExpanded && (
              <Box sx={{ pl: 1, fontSize: '0.7rem', color: 'error.main', mt: 0.5 }}>
                <Box>Expected: {fCurrency(flag.expectedTotal)}</Box>
                <Box>Actual: {fCurrency(flag.actualTotal)}</Box>
                <Box sx={{ fontWeight: 600 }}>
                  Diff: {fCurrency(Math.abs(flag.difference))} {flag.difference > 0 ? '↑' : '↓'}
                </Box>
              </Box>
            )}
          </Box>
        );
      })}
    </Box>
  );
}

