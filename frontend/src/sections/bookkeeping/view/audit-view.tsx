'use client';

import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Typography from '@mui/material/Typography';

import { paths } from 'src/routes/paths';
import { RouterLink } from 'src/routes/components';

import { fDate } from 'src/utils/format-time';
import { fCurrency } from 'src/utils/format-number';

import { useGetAudit } from 'src/actions/receipt';
import { DashboardContent } from 'src/layouts/dashboard';

import { Label } from 'src/components/label';
import { CustomBreadcrumbs } from 'src/components/custom-breadcrumbs';

// ----------------------------------------------------------------------

export function AuditView() {
  const { audit } = useGetAudit();

  return (
    <DashboardContent maxWidth="xl">
      <CustomBreadcrumbs
        heading="Audit Findings"
        links={[
          { name: 'Dashboard', href: paths.dashboard.root },
          { name: 'Audit' },
        ]}
        sx={{ mb: { xs: 3, md: 5 } }}
      />

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ p: 3, bgcolor: 'warning.lighter' }}>
            <Typography variant="h4" color="warning.main">
              {audit?.summary.totalDuplicates || 0}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
              Duplicates
            </Typography>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ p: 3, bgcolor: 'error.lighter' }}>
            <Typography variant="h4" color="error.main">
              {audit?.summary.totalMismatches || 0}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
              Total Mismatches
            </Typography>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ p: 3, bgcolor: 'error.lighter' }}>
            <Typography variant="h4" color="error.main">
              {audit?.summary.totalMissingVAT || 0}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
              Missing VAT
            </Typography>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ p: 3, bgcolor: 'error.lighter' }}>
            <Typography variant="h4" color="error.main">
              {audit?.summary.totalSuspicious || 0}
            </Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', mt: 1 }}>
              Suspicious
            </Typography>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Duplicates */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Duplicates ({audit?.duplicates.length || 0})
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={2}>
              {audit?.duplicates.map((item, index) => (
                <Box key={`duplicate-${item.receiptId}-${index}`} sx={{ p: 2, borderRadius: 1, bgcolor: 'warning.lighter' }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Stack>
                      <Typography variant="subtitle2">{item.receiptNumber}</Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {item.vendor} • {fDate(item.date)}
                      </Typography>
                    </Stack>
                    <Button
                      component={RouterLink}
                      href={paths.dashboard.receipt.details(item.receiptId)}
                      size="small"
                    >
                      View
                    </Button>
                  </Stack>
                </Box>
              ))}
              {(!audit?.duplicates || audit.duplicates.length === 0) && (
                <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', py: 3 }}>
                  No duplicates found
                </Typography>
              )}
            </Stack>
          </Card>
        </Grid>

        {/* Mismatches */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Total Mismatches ({audit?.mismatches.length || 0})
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={2}>
              {audit?.mismatches.map((item, index) => (
                <Box key={`mismatch-${item.receiptId}-${index}`} sx={{ p: 2, borderRadius: 1, bgcolor: 'error.lighter' }}>
                  <Stack spacing={1}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Stack>
                        <Typography variant="subtitle2">{item.receiptNumber}</Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          {item.vendor} • {fDate(item.date)}
                        </Typography>
                      </Stack>
                      <Button
                        component={RouterLink}
                        href={paths.dashboard.receipt.details(item.receiptId)}
                        size="small"
                      >
                        View
                      </Button>
                    </Stack>
                    <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                      <Typography variant="caption">
                        Expected: {fCurrency(item.expectedTotal || 0)}
                      </Typography>
                      <Typography variant="caption">
                        Actual: {fCurrency(item.actualTotal || 0)}
                      </Typography>
                      <Typography variant="caption" color="error.main">
                        Diff: {fCurrency(item.difference || 0)}
                      </Typography>
                    </Stack>
                  </Stack>
                </Box>
              ))}
              {(!audit?.mismatches || audit.mismatches.length === 0) && (
                <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', py: 3 }}>
                  No mismatches found
                </Typography>
              )}
            </Stack>
          </Card>
        </Grid>

        {/* Missing VAT */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Missing VAT ({audit?.missingVAT.length || 0})
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={2}>
              {audit?.missingVAT.map((item, index) => (
                <Box key={`missing-vat-${item.receiptId}-${index}`} sx={{ p: 2, borderRadius: 1, bgcolor: 'error.lighter' }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Stack>
                      <Typography variant="subtitle2">{item.receiptNumber}</Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {item.vendor} • {fDate(item.date)} • {fCurrency(item.total)}
                      </Typography>
                    </Stack>
                    <Button
                      component={RouterLink}
                      href={paths.dashboard.receipt.details(item.receiptId)}
                      size="small"
                    >
                      View
                    </Button>
                  </Stack>
                </Box>
              ))}
              {(!audit?.missingVAT || audit.missingVAT.length === 0) && (
                <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', py: 3 }}>
                  No missing VAT found
                </Typography>
              )}
            </Stack>
          </Card>
        </Grid>

        {/* Suspicious */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Suspicious Receipts ({audit?.suspicious.length || 0})
            </Typography>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={2}>
              {audit?.suspicious.map((item, index) => (
                <Box key={`suspicious-${item.receiptId}-${index}`} sx={{ p: 2, borderRadius: 1, bgcolor: 'error.lighter' }}>
                  <Stack spacing={1}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Stack>
                        <Typography variant="subtitle2">{item.receiptNumber}</Typography>
                        <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                          {item.vendor} • {fDate(item.date)}
                        </Typography>
                      </Stack>
                      <Button
                        component={RouterLink}
                        href={paths.dashboard.receipt.details(item.receiptId)}
                        size="small"
                      >
                        View
                      </Button>
                    </Stack>
                    <Label variant="soft" color="error">
                      {item.category}
                    </Label>
                  </Stack>
                </Box>
              ))}
              {(!audit?.suspicious || audit.suspicious.length === 0) && (
                <Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', py: 3 }}>
                  No suspicious receipts found
                </Typography>
              )}
            </Stack>
          </Card>
        </Grid>
      </Grid>
    </DashboardContent>
  );
}

