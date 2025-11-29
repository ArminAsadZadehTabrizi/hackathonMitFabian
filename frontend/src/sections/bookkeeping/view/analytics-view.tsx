'use client';

import { useMemo } from 'react';

import Grid from '@mui/material/Grid';
import Card from '@mui/material/Card';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { paths } from 'src/routes/paths';

import { fNumber, fCurrency } from 'src/utils/format-number';

import { useGetAnalytics } from 'src/actions/receipt';
import { DashboardContent } from 'src/layouts/dashboard';

import { Iconify } from 'src/components/iconify';
import { Chart, useChart } from 'src/components/chart';
import { CustomBreadcrumbs } from 'src/components/custom-breadcrumbs';

// ----------------------------------------------------------------------

export function BookkeepingAnalyticsView() {
  const { analytics } = useGetAnalytics();

  const categoryChart = useMemo(() => {
    if (!analytics?.categories) return null;

    return {
      series: analytics.categories.slice(0, 10).map((cat) => ({
        label: cat.category,
        value: cat.amount,
      })),
      categories: analytics.categories.slice(0, 10).map((cat) => cat.category),
    };
  }, [analytics]);

  const monthlyChart = useMemo(() => {
    if (!analytics?.monthly) return null;

    return {
      categories: analytics.monthly.map((m) => m.month),
      series: [
        {
          name: 'Spending',
          data: analytics.monthly.map((m) => m.amount),
        },
      ],
    };
  }, [analytics]);

  const categoryChartOptions = useChart({
    chart: { type: 'donut' },
    labels: categoryChart?.categories || [],
    tooltip: {
      y: {
        formatter: (value: number) => fCurrency(value),
        title: { formatter: () => '' },
      },
    },
    plotOptions: {
      pie: {
        donut: {
          size: '70%',
          labels: {
            show: true,
            total: {
              label: 'Total',
              formatter: () => fCurrency(analytics?.summary.totalSpending || 0),
            },
          },
        },
      },
    },
  });

  const monthlyChartOptions = useChart({
    chart: { type: 'area' },
    xaxis: { categories: monthlyChart?.categories || [] },
    tooltip: {
      y: {
        formatter: (value: number) => fCurrency(value),
      },
    },
    fill: {
      type: 'gradient',
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.7,
        opacityTo: 0.9,
      },
    },
  });

  return (
    <DashboardContent maxWidth="xl">
      <CustomBreadcrumbs
        heading="Analytics"
        links={[
          { name: 'Dashboard', href: paths.dashboard.root },
          { name: 'Analytics' },
        ]}
        sx={{ mb: { xs: 3, md: 5 } }}
      />

      <Grid container spacing={3}>
        {/* Summary Cards */}
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ p: 3 }}>
            <Stack spacing={0.5}>
              <Typography variant="h4">{fCurrency(analytics?.summary.totalSpending || 0)}</Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Total Spending
              </Typography>
            </Stack>
            <Iconify icon="solar:wallet-bold" width={32} sx={{ mt: 2, color: 'primary.main' }} />
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ p: 3 }}>
            <Stack spacing={0.5}>
              <Typography variant="h4">{fNumber(analytics?.summary.totalReceipts || 0)}</Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Total Receipts
              </Typography>
            </Stack>
            <Iconify icon="solar:receipt-bold" width={32} sx={{ mt: 2, color: 'info.main' }} />
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ p: 3 }}>
            <Stack spacing={0.5}>
              <Typography variant="h4">{fCurrency(analytics?.summary.totalVAT || 0)}</Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Total VAT
              </Typography>
            </Stack>
            <Iconify icon="solar:document-text-bold" width={32} sx={{ mt: 2, color: 'warning.main' }} />
          </Card>
        </Grid>

        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card sx={{ p: 3 }}>
            <Stack spacing={0.5}>
              <Typography variant="h4">
                {fCurrency(analytics?.summary.avgReceiptValue || 0)}
              </Typography>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                Avg Receipt Value
              </Typography>
            </Stack>
            <Iconify icon="solar:chart-2-bold" width={32} sx={{ mt: 2, color: 'success.main' }} />
          </Card>
        </Grid>

        {/* Monthly Spending Chart */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 3 }}>
              Monthly Spending
            </Typography>
            {monthlyChart && (
              <Chart
                type="area"
                series={monthlyChart.series}
                options={monthlyChartOptions}
                height={320}
                slotProps={{ loading: { p: 2.5 } }}
              />
            )}
          </Card>
        </Grid>

        {/* Category Distribution */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 3 }}>
              Spending by Category
            </Typography>
            {categoryChart && (
              <Chart
                type="donut"
                series={categoryChart.series.map((s) => s.value)}
                options={categoryChartOptions}
                height={320}
                slotProps={{ loading: { p: 2.5 } }}
              />
            )}
          </Card>
        </Grid>

        {/* Top Categories Table */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 3 }}>
              Top Categories
            </Typography>
            <Stack spacing={2}>
              {analytics?.categories.slice(0, 5).map((cat, index) => (
                <Stack
                  key={cat.category}
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                  sx={{ p: 2, borderRadius: 1, bgcolor: 'background.neutral' }}
                >
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography variant="h6" sx={{ minWidth: 24 }}>
                      {index + 1}
                    </Typography>
                    <Stack>
                      <Typography variant="subtitle2">{cat.category}</Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {cat.count} receipts
                      </Typography>
                    </Stack>
                  </Stack>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    {fCurrency(cat.amount)}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Card>
        </Grid>

        {/* Top Vendors */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 3 }}>
              Top Vendors
            </Typography>
            <Stack spacing={2}>
              {analytics?.vendors.slice(0, 5).map((vendor, index) => (
                <Stack
                  key={vendor.vendor}
                  direction="row"
                  justifyContent="space-between"
                  alignItems="center"
                  sx={{ p: 2, borderRadius: 1, bgcolor: 'background.neutral' }}
                >
                  <Stack direction="row" spacing={2} alignItems="center">
                    <Typography variant="h6" sx={{ minWidth: 24 }}>
                      {index + 1}
                    </Typography>
                    <Stack>
                      <Typography variant="subtitle2">{vendor.vendor}</Typography>
                      <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {vendor.count} receipts
                      </Typography>
                    </Stack>
                  </Stack>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    {fCurrency(vendor.amount)}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Card>
        </Grid>
      </Grid>
    </DashboardContent>
  );
}

