'use client';

import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { DashboardContent } from 'src/layouts/dashboard';
import { useGetAnalytics } from 'src/actions/receipt';

import { CustomBreadcrumbs } from 'src/components/custom-breadcrumbs';

import { paths } from 'src/routes/paths';

import { fCurrency } from 'src/utils/format-number';

// ----------------------------------------------------------------------

export function VendorsView() {
  const { analytics, analyticsLoading } = useGetAnalytics();

  return (
    <DashboardContent maxWidth="xl">
      <CustomBreadcrumbs
        heading="Vendor Analytics"
        links={[
          { name: 'Dashboard', href: paths.dashboard.root },
          { name: 'Vendors' },
        ]}
        sx={{ mb: { xs: 3, md: 5 } }}
      />

      <Grid container spacing={3}>
        {analytics?.vendors.map((vendor, index) => (
          <Grid key={vendor.vendor} size={{ xs: 12, sm: 6, md: 4 }}>
            <Card sx={{ p: 3 }}>
              <Stack spacing={2}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Stack>
                    <Typography variant="h6">{vendor.vendor}</Typography>
                    <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                      {vendor.count} {vendor.count === 1 ? 'receipt' : 'receipts'}
                    </Typography>
                  </Stack>
                  <Typography variant="h4" sx={{ color: 'primary.main' }}>
                    #{index + 1}
                  </Typography>
                </Stack>
                <Typography variant="h4">{fCurrency(vendor.amount)}</Typography>
              </Stack>
            </Card>
          </Grid>
        ))}
      </Grid>
    </DashboardContent>
  );
}

